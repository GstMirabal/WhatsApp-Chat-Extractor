"""Enumerate every conversation in the chat list, and reopen one by identity.

Measured before written (`docs/sprints/007-backend-extractor/CHAT_LIST_PROBE_NOTES.md`).
Three probe runs on 2026-08-31 established:

* The pane **virtualizes**: 899 conversations were seen while the DOM never held
  more than 70 rows at once. A single ``query_selector_all`` would return 70 of
  899 and report success, which is why enumeration is a sweep that merges by
  identity — the same shape ``history.harvest_history`` uses one panel over.
* A chat's **position is stable** across a full sweep (0 of 69 changed), and no
  two conversations share a title (0 collisions in 7 100 row observations), so
  the digest identifies a conversation within a run.
* Across runs it does **not**: two sweeps 2.5 hours apart shared 898 of 899
  digests. The digest follows the title, so a renamed conversation becomes a new
  identity. That is a limit of the export contract, not of this module.

Position is therefore used only as a **hint** for where to look, and the digest
is what decides whether the right conversation was opened. Every open is verified
against the digest before anything is exported: H-001 shipped a wrong-chat export
because a click was trusted without checking what it opened.

Privacy: titles are read to hash them and to hand to ``writers.build_export``,
which hashes and drops them. This module stores no title.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypedDict

from whatsapp_chat_extractor.writers import pseudonymous_chat_id

if TYPE_CHECKING:  # pragma: no cover - typing only
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)

# The scrollable chat-list pane and its rows. Measured, not assumed: the probe
# reported `span[title]` as the working title selector — the two
# `cell-frame-title` candidates matched nothing in this WhatsApp Web build.
CHAT_PANE_SELECTOR = "#pane-side"
CHAT_ROW_SELECTOR = '[data-testid="cell-frame-container"]'
TITLE_SELECTORS = (
    'span[data-testid="cell-frame-title"] span[title]',
    'span[data-testid="cell-frame-title"]',
    "span[title]",
)

# Guarantees termination of a sweep. Run 3 finished a 899-chat list in 103
# passes; 400 leaves room for an account several times larger.
DEFAULT_MAX_PASSES = 400
DEFAULT_SETTLE_MS = 1_200
# Consecutive passes revealing nothing new that end a sweep — but only once the
# pane foot is reached. Before that, a quiet pass means the sweep is inside the
# render buffer, which is not the same statement (probe run 1 confounded them).
QUIET_PASSES_TO_STOP = 3
BOTTOM_TOLERANCE_PX = 1
# How many scroll-and-look attempts a single conversation gets before it is
# reported missing. The hint is usually exact; three covers a list that shifted.
DEFAULT_SEEK_ATTEMPTS = 3


class ChatRef(TypedDict):
    """One enumerated conversation: what it is, and where it was seen.

    `index` is the position of first discovery during a top-to-bottom sweep,
    which is list order. It is a **hint** for seeking, never the identity —
    `chat_id` is.
    """

    chat_id: str
    index: int


def row_title(row: object) -> str:
    """The conversation title of one chat-list row, or an empty string.

    The title is a person's name. It is returned so the caller can hash it and
    is never logged or stored.

    Args:
        row: A chat-list row element handle.

    Returns:
        str: The title as rendered, or ``""`` when no candidate matched.
    """
    for selector in TITLE_SELECTORS:
        node = row.query_selector(selector)  # type: ignore[attr-defined]
        if node is None:
            continue
        text = (node.get_attribute("title") or node.inner_text() or "").strip()
        if text:
            return text
    return ""


def row_digests(page: Page) -> tuple[list[str], int]:
    """Pseudonymous digests of every chat-list row currently in the DOM.

    Args:
        page: WhatsApp Web page showing the chat list.

    Returns:
        tuple[list[str], int]: Digests in list order, and how many rows carried
            no readable title. An unreadable row gets no digest rather than a
            fabricated one.
    """
    digests: list[str] = []
    untitled = 0
    for row in page.query_selector_all(CHAT_ROW_SELECTOR):
        title = row_title(row)
        if not title:
            untitled += 1
            continue
        digests.append(pseudonymous_chat_id(title))
    return digests, untitled


def pane_metrics(page: Page) -> dict[str, int]:
    """Scroll geometry of the chat pane, or zeroes when it cannot be read.

    Args:
        page: WhatsApp Web page showing the chat list.

    Returns:
        dict[str, int]: ``scroll_top``, ``scroll_height`` and ``client_height``.
    """
    metrics = page.evaluate(
        """(selector) => {
            const pane = document.querySelector(selector);
            if (!pane) return null;
            return {
                scroll_top: Math.round(pane.scrollTop),
                scroll_height: Math.round(pane.scrollHeight),
                client_height: Math.round(pane.clientHeight),
            };
        }""",
        CHAT_PANE_SELECTOR,
    )
    return metrics or {"scroll_top": 0, "scroll_height": 0, "client_height": 0}


def at_pane_bottom(metrics: dict[str, int]) -> bool:
    """Whether the pane has been scrolled to its foot.

    Args:
        metrics: A reading from :func:`pane_metrics`.

    Returns:
        bool: True when no scrollable distance remains. A pane reporting a zero
            ``scroll_height`` is **not** at the bottom: that is an unreadable
            pane, and calling it finished is how a wrong selector produces a
            confident answer about a list it never found.
    """
    if metrics["scroll_height"] <= 0:
        return False
    remaining = (
        metrics["scroll_height"] - metrics["scroll_top"] - metrics["client_height"]
    )
    return remaining <= BOTTOM_TOLERANCE_PX


def scroll_pane_to(page: Page, top: int, *, settle_ms: int) -> None:
    """Put the chat pane at ``top`` and wait for it to render.

    Args:
        page: WhatsApp Web page showing the chat list.
        top: Target ``scrollTop`` in pixels; clamped by the browser.
        settle_ms: Wait for newly requested rows to render.
    """
    page.evaluate(
        """([selector, top]) => {
            const pane = document.querySelector(selector);
            if (pane) pane.scrollTop = top;
        }""",
        [CHAT_PANE_SELECTOR, max(0, top)],
    )
    page.wait_for_timeout(settle_ms)


def seek_scroll_top(index: int, *, total: int, metrics: dict[str, int]) -> int:
    """Where to scroll so the conversation at ``index`` is likely rendered.

    Centres the target in the viewport rather than putting it at the edge, so a
    list that shifted by a few rows still renders it.

    Args:
        index: Position of the conversation in list order.
        total: How many conversations the sweep found.
        metrics: A reading from :func:`pane_metrics`.

    Returns:
        int: A non-negative ``scrollTop``. Zero when the geometry is unusable,
            which lands at the head — a defined position rather than a guess.
    """
    if total <= 0 or metrics["scroll_height"] <= 0:
        return 0
    row_height = metrics["scroll_height"] / total
    centred = index * row_height - metrics["client_height"] / 2
    return max(0, int(centred))


def sweep_chat_list(
    page: Page,
    *,
    max_passes: int = DEFAULT_MAX_PASSES,
    settle_ms: int = DEFAULT_SETTLE_MS,
) -> list[ChatRef]:
    """Every conversation in the list, in list order, discovered once each.

    Args:
        page: WhatsApp Web page showing the chat list.
        max_passes: Hard cap on scroll passes; guarantees termination.
        settle_ms: Wait after each scroll.

    Returns:
        list[ChatRef]: One entry per distinct conversation, in the order it was
            first seen. Fewer than the account holds if the cap was reached
            before the pane foot — the caller checks with
            :func:`sweep_reached_bottom`.
    """
    seen: set[str] = set()
    refs: list[ChatRef] = []
    quiet = 0
    for _ in range(max_passes):
        digests, untitled = row_digests(page)
        if untitled:
            logger.warning("%s chat-list rows had no readable title", untitled)
        added = [digest for digest in digests if digest not in seen]
        for digest in added:
            seen.add(digest)
            refs.append({"chat_id": digest, "index": len(refs)})
        quiet = quiet + 1 if not added else 0
        metrics = pane_metrics(page)
        if at_pane_bottom(metrics) and quiet >= QUIET_PASSES_TO_STOP:
            break
        scroll_pane_to(
            page,
            metrics["scroll_top"] + metrics["client_height"],
            settle_ms=settle_ms,
        )
    logger.info("Enumerated %s conversations", len(refs))
    return refs


def sweep_reached_bottom(page: Page) -> bool:
    """Whether the pane is currently at its foot.

    Args:
        page: WhatsApp Web page showing the chat list.

    Returns:
        bool: True when the sweep can be said to have seen the whole list.
    """
    return at_pane_bottom(pane_metrics(page))


def open_chat_by_digest(
    page: Page,
    ref: ChatRef,
    *,
    total: int,
    settle_ms: int = DEFAULT_SETTLE_MS,
    attempts: int = DEFAULT_SEEK_ATTEMPTS,
) -> str:
    """Open the conversation ``ref`` identifies and return its verified title.

    The index only decides where to look. What decides whether the right
    conversation was opened is the digest of the title actually on screen: a
    click is not evidence that anything opened, and H-001 shipped precisely that
    assumption.

    Args:
        page: WhatsApp Web page showing the chat list.
        ref: The conversation to open.
        total: How many conversations the sweep found, for the scroll estimate.
        settle_ms: Wait after scrolling and after clicking.
        attempts: Scroll-and-look tries before reporting it missing.

    Returns:
        str: The opened conversation's title, verified to hash to
            ``ref["chat_id"]``.

    Raises:
        LookupError: The conversation was not found in the list.
        RuntimeError: A row was clicked but the conversation that opened is not
            the one asked for. Fails closed rather than exporting the wrong chat.
    """
    from whatsapp_chat_extractor.export_one import read_open_chat_title

    for attempt in range(attempts):
        target = seek_scroll_top(
            ref["index"] + attempt, total=total, metrics=pane_metrics(page)
        )
        scroll_pane_to(page, target, settle_ms=settle_ms)
        match = find_row(page.query_selector_all(CHAT_ROW_SELECTOR), ref["chat_id"])
        if match is None:
            continue
        match.click(timeout=5_000)
        page.wait_for_timeout(settle_ms)
        return _verified_title(read_open_chat_title(page), ref["chat_id"])
    raise LookupError(f"{ref['chat_id']} was not found in the chat list")


def find_row(rows: list[object], chat_id: str) -> object | None:
    """The row among ``rows`` whose title hashes to ``chat_id``.

    Args:
        rows: Chat-list row element handles currently in the DOM.
        chat_id: The digest to match.

    Returns:
        object | None: The matching row, or None when this window holds none.
            A row with no readable title never matches — it has no identity to
            compare, and matching it would be guessing.
    """
    for row in rows:
        title = row_title(row)
        if title and pseudonymous_chat_id(title) == chat_id:
            return row
    return None


def _verified_title(title: str, chat_id: str) -> str:
    """The opened conversation's title, or a refusal.

    Args:
        title: Title read from the open conversation.
        chat_id: The digest the caller asked for.

    Returns:
        str: ``title`` when it hashes to ``chat_id``.

    Raises:
        RuntimeError: The wrong conversation is open, or its title is
            unreadable. An unattributable conversation is not exportable.
    """
    if not title:
        raise RuntimeError(f"Opened a conversation with no readable title for {chat_id}")
    if pseudonymous_chat_id(title) != chat_id:
        raise RuntimeError(
            f"Opened the wrong conversation: asked for {chat_id}, "
            f"got {pseudonymous_chat_id(title)}"
        )
    return title
