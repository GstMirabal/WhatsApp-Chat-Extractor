"""Probe whether WhatsApp Web renders a start-of-conversation marker.

Sprint 006 W1. An export reports ``complete: true`` only when
``export_one.CHAT_START_SELECTORS`` matches something, and no run has ever
produced it. Two explanations are open, and this probe decides between them
instead of assuming one:

    H1  The marker exists in some chats and no uncapped run has ever met one.
        Then ``complete: true`` is reachable and only needs to be executed.
    H2  The marker is absent from this operator's chats. Then the current
        completeness criterion is unusable in practice and must be replaced.

``KI-004-A`` is why this is a probe and not a patch: three successive theories
about message direction were reasoned rather than measured, and all three were
wrong and all three shipped. Nothing here infers WhatsApp's structure.

Privacy. ``ADR-0003`` keeps message content and real names out of every stored
artifact. This probe records structural attributes only, from a fixed
allowlist, and never reads ``innerText``. ``data-pre-plain-text`` is excluded
from that allowlist on purpose: it carries the sender's name. Chats are
identified by the same pseudonymous digest the exporter writes, so the output
file names no one.

The operator must be present: this drives a real logged-in session against real
conversations, so it is not runnable unattended. Give it at least five distinct
chats, one of them deliberately short — a short conversation is where a start
marker has the best chance of being on screen at all.

invoked_by: docs/sprints/006-backend-extractor/IMPLEMENTATION_PLAN.md (W1),
    run by hand by the operator; not part of any unattended routine.

Example:
    .venv/bin/python scripts/probe_chat_start.py -q ana -q "grupo obra" \
        -q pedro -q clinica -q "chat corto"
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from whatsapp_chat_extractor.export_one import (
    CHAT_START_SELECTORS,
    MESSAGE_PANEL_SELECTORS,
    MESSAGE_ROW_SELECTORS,
    SEARCH_RESULT_SELECTORS,
    at_chat_start,
    scroll_one_pass,
)
from whatsapp_chat_extractor.history import (
    DEFAULT_LOAD_WAIT_MS,
    DEFAULT_STALL_THRESHOLD,
    STOP_CHAT_START,
    STOP_MAX_PASSES,
    STOP_STALLED,
)
from whatsapp_chat_extractor.session import (
    DEFAULT_PROFILE_DIR,
    WA_WEB_URL,
    launch_context,
    open_whatsapp,
    wait_until_ready,
)
from whatsapp_chat_extractor.writers import pseudonymous_chat_id

if TYPE_CHECKING:  # pragma: no cover - typing only
    from playwright.sync_api import Page

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("wa-probe")

DEFAULT_OUT_DIR = Path("data/probes")
# The plan's threshold: below five chats the answer to H1/H2 is anecdote.
DEFAULT_MIN_CHATS = 5
# A probe is not the uncapped run. It exists to see the top of short chats and
# to report honestly when a long one was not exhausted.
DEFAULT_MAX_PASSES = 400
# Chrome nodes at the top of the panel. Twelve covers the encryption notice,
# the date divider and the first bubble's wrapper with room to spare.
TOP_NODE_LIMIT = 12
EXIT_BELOW_MINIMUM = 3
# Descendants of the first search hit to record. The hit's own node may not be
# the clickable one, and this is what shows which descendant is.
RESULT_TREE_LIMIT = 14
# Ordered attempts at opening a search hit, most specific first.
#
# `export_one._open_first_result` clicks `.first` of the earliest selector with
# any match, and run 1 measured why that fails here: `role="listitem"` matches
# nothing (0), so it falls through to `#pane-side div[role="row"]` (59) — a
# wrapper that accepts a click and does nothing. The operator then opens the
# chat by hand and the run looks like it worked.
#
# The probe therefore tries several and records which one actually opened the
# chat, rather than assuming. Nothing is fixed in the exporter on this evidence
# alone: these counts came from a page with a chat already open, not from a
# live search, and guessing from them is the mistake `KI-004-A` names.
SEARCH_CLICK_SELECTORS = (
    '[data-testid="cell-frame-container"]',
    '#pane-side div[role="listitem"]',
    '#pane-side div[role="row"]',
)
# How long a click gets to produce an open conversation before it is judged.
OPEN_SETTLE_MS = 1_500

# Structural attributes only. `data-pre-plain-text`, `title`, `alt` and
# `aria-label` are all absent by design: each can carry a person's name.
_SIGNATURE_JS = """
(el) => {
  const allow = ['data-icon', 'data-testid', 'role', 'class', 'dir', 'tabindex'];
  const attrs = {};
  for (const name of allow) {
    const value = el.getAttribute(name);
    if (value !== null) { attrs[name] = value.slice(0, 160); }
  }
  return {
    tag: el.tagName.toLowerCase(),
    attrs: attrs,
    has_data_id: el.hasAttribute('data-id'),
    child_count: el.childElementCount,
  };
}
"""

_TOP_CHROME_JS = """
(panel, limit) => {
  const allow = ['data-icon', 'data-testid', 'role', 'class', 'dir', 'tabindex'];
  const sign = (el) => {
    const attrs = {};
    for (const name of allow) {
      const value = el.getAttribute(name);
      if (value !== null) { attrs[name] = value.slice(0, 160); }
    }
    return {
      tag: el.tagName.toLowerCase(),
      attrs: attrs,
      has_data_id: el.hasAttribute('data-id'),
      child_count: el.childElementCount,
    };
  };
  const all = Array.from(panel.querySelectorAll('*')).slice(0, 600);
  const chrome = all.filter(
    (el) => !el.closest('[data-id], .message-in, .message-out')
  );
  return chrome.slice(0, limit).map(sign);
}
"""

_OUTSIDE_PANE_JS = """
(el) => !el.closest('#pane-side')
"""

# Whether the focused element sits inside the open conversation. `_clear_and_type`
# types into whatever holds focus, so this is the difference between running a
# search and writing into someone's chat.
_FOCUS_IN_CONVERSATION_JS = """
() => {
  const el = document.activeElement;
  return !!(el && el.closest('#main'));
}
"""

# The first search hit and its descendants. Which node carries the click
# handler is the open question, and a signature of the subtree is what answers
# it. Text is never read: `class` and `role` say enough about shape.
_RESULT_TREE_JS = """
(el, limit) => {
  const allow = ['data-icon', 'data-testid', 'role', 'class', 'tabindex', 'dir'];
  const sign = (node, depth) => {
    const attrs = {};
    for (const name of allow) {
      const value = node.getAttribute(name);
      if (value !== null) { attrs[name] = value.slice(0, 160); }
    }
    return {
      tag: node.tagName.toLowerCase(),
      depth: depth,
      attrs: attrs,
      child_count: node.childElementCount,
    };
  };
  const out = [sign(el, 0)];
  for (const kid of Array.from(el.querySelectorAll('*')).slice(0, limit)) {
    let depth = 0;
    for (let p = kid.parentElement; p && p !== el; p = p.parentElement) { depth++; }
    out.push(sign(kid, depth + 1));
  }
  return out;
}
"""

# A tally, not a sample. `top_chrome_signatures` walks the panel in document
# order and spends its budget on whatever comes first — in a live panel that is
# a stack of nested wrappers and bare `<span>`s, and the encryption notice can
# fall outside the limit entirely. That failure is silent and it points the
# wrong way: a marker that exists but was not dumped reads exactly like H2.
# This inventory has no budget, so a marker-like node cannot hide from it.
_CHROME_INVENTORY_JS = """
(panel) => {
  const nodes = Array.from(
    panel.querySelectorAll('[data-icon], [data-testid], [role]')
  );
  const chrome = nodes.filter(
    (el) => !el.closest('[data-id], .message-in, .message-out')
  );
  const tally = (name) => {
    const out = {};
    for (const el of chrome) {
      const value = el.getAttribute(name);
      if (value !== null) { out[value] = (out[value] || 0) + 1; }
    }
    return out;
  };
  return {
    data_icon: tally('data-icon'),
    data_testid: tally('data-testid'),
    role: tally('role'),
    chrome_nodes: chrome.length,
  };
}
"""


def _first_present(page: Page, selectors: tuple[str, ...]) -> str | None:
    """Return the first selector of ``selectors`` that matches on ``page``.

    Args:
        page: Live WhatsApp Web page.
        selectors: Candidate CSS selectors, in preference order.

    Returns:
        str | None: The matching selector, or None when none match.
    """
    for selector in selectors:
        if page.query_selector(selector):
            return selector
    return None


def marker_evidence(page: Page) -> dict[str, Any]:
    """Report which start-of-conversation selector matches, if any.

    Args:
        page: Page with an open conversation, scrolled to its top.

    Returns:
        dict[str, Any]: ``matched_selector`` (None when absent) and the match
            count of every candidate, so a selector that fires on the wrong
            node is distinguishable from one that never fires.
    """
    per_selector = {
        selector: len(page.query_selector_all(selector))
        for selector in CHAT_START_SELECTORS
    }
    matched = _first_present(page, CHAT_START_SELECTORS)
    return {
        "marker_found": matched is not None,
        "matched_selector": matched,
        "counts_per_selector": per_selector,
    }


def top_chrome_signatures(page: Page, *, limit: int = TOP_NODE_LIMIT) -> list[dict]:
    """Dump the structural attribute chain of the panel's topmost chrome nodes.

    "Chrome" is everything that is not inside a message bubble. A start marker,
    an encryption notice and a date divider are all chrome, and this is the
    evidence that answers H1 versus H2 for a chat with no matching selector:
    it shows what WhatsApp *did* draw at the top instead.

    Args:
        page: Page with an open conversation, scrolled to its top.
        limit: How many nodes to record.

    Returns:
        list[dict]: One structural signature per node, in document order.
    """
    panel_selector = _first_present(page, MESSAGE_PANEL_SELECTORS)
    if panel_selector is None:
        logger.warning("No message panel found; top-of-panel evidence skipped")
        return []
    panel = page.query_selector(panel_selector)
    if panel is None:
        return []
    return list(panel.evaluate(_TOP_CHROME_JS, limit))


def chrome_attribute_inventory(page: Page) -> dict[str, Any]:
    """Tally every structural attribute value the panel's chrome carries.

    `top_chrome_signatures` samples the first nodes in document order, so a
    marker sitting below a deep stack of wrappers can fall outside its limit.
    That miss is indistinguishable from a marker that does not exist, which is
    the exact confusion this sprint has to resolve — so completeness is
    measured here instead, with no limit to fall outside of.

    Args:
        page: Page with an open conversation, scrolled to its top.

    Returns:
        dict[str, Any]: Counts per distinct ``data-icon``, ``data-testid`` and
            ``role`` value found outside message bubbles, plus how many chrome
            nodes were examined. Empty when the panel cannot be located.
    """
    panel_selector = _first_present(page, MESSAGE_PANEL_SELECTORS)
    if panel_selector is None:
        logger.warning("No message panel found; chrome inventory skipped")
        return {}
    panel = page.query_selector(panel_selector)
    if panel is None:
        return {}
    return dict(panel.evaluate(_CHROME_INVENTORY_JS))


def kind_census(page: Page) -> dict[str, Any]:
    """Count the media kinds among the rows currently in the DOM.

    Observation only (plan D3): the six `kind: unknown` rows of Sprint 005 are
    not corrected here, they are characterised. For every unknown row this
    records the structural signature that `_row_kind` failed to classify, which
    is precisely the evidence Sprint 007 needs and does not have.

    Args:
        page: Page with an open conversation.

    Returns:
        dict[str, Any]: Counts per kind plus signatures of the unknown rows.
    """
    # Private helpers of the exporter, used on purpose: re-implementing the
    # classification here would let the probe and the exporter disagree, and
    # then the probe would be measuring itself rather than WhatsApp.
    from whatsapp_chat_extractor.export_one import _row_body, _row_kind

    row_selector = _first_present(page, MESSAGE_ROW_SELECTORS)
    if row_selector is None:
        return {"rows_seen": 0, "counts": {}, "unknown_signatures": []}

    counts: dict[str, int] = {}
    unknown: list[dict] = []
    rows = page.query_selector_all(row_selector)
    for row in rows:
        kind = _row_kind(row, _row_body(row))
        counts[kind] = counts.get(kind, 0) + 1
        if kind == "unknown" and len(unknown) < TOP_NODE_LIMIT:
            unknown.append(row.evaluate(_SIGNATURE_JS))
    return {"rows_seen": len(rows), "counts": counts, "unknown_signatures": unknown}


def search_scope_evidence(page: Page) -> list[dict[str, Any]]:
    """Measure how far each search-result selector reaches outside `#pane-side`.

    Observation only (plan D3). `search_selector_scope` is deferred to Sprint
    007, and the question it needs answered is whether any candidate selector
    matches nodes beyond the chat-list pane — which is what would let a search
    click land somewhere other than a conversation row.

    Args:
        page: Page showing search results, or any ready page.

    Returns:
        list[dict[str, Any]]: Per selector, total matches and how many of them
            sit outside `#pane-side`.
    """
    evidence: list[dict[str, Any]] = []
    for selector in SEARCH_RESULT_SELECTORS:
        nodes = page.query_selector_all(selector)
        outside = sum(1 for node in nodes if node.evaluate(_OUTSIDE_PANE_JS))
        evidence.append(
            {"selector": selector, "matches": len(nodes), "outside_pane_side": outside}
        )
    return evidence


def scroll_to_top(
    page: Page,
    *,
    max_passes: int = DEFAULT_MAX_PASSES,
    stall_threshold: int = DEFAULT_STALL_THRESHOLD,
    load_wait_ms: int = DEFAULT_LOAD_WAIT_MS,
) -> dict[str, Any]:
    """Scroll upward until the marker appears, the panel stalls, or the cap hits.

    This mirrors `history.harvest_history`'s termination rules but collects no
    messages: the probe answers a question about the DOM, and harvesting a real
    conversation to answer it would write content this sprint has no reason to
    hold.

    Args:
        page: Page with an open conversation.
        max_passes: Hard cap that guarantees termination.
        stall_threshold: Consecutive passes with no older messages that end it.
        load_wait_ms: How long one pass waits for older messages to arrive.

    Returns:
        dict[str, Any]: ``stopped_reason`` and ``passes_used``.
    """
    stall_count = 0
    passes_used = 0
    while True:
        if at_chat_start(page):
            return {"stopped_reason": STOP_CHAT_START, "passes_used": passes_used}
        if stall_count >= stall_threshold:
            return {"stopped_reason": STOP_STALLED, "passes_used": passes_used}
        if passes_used >= max_passes:
            return {"stopped_reason": STOP_MAX_PASSES, "passes_used": passes_used}
        if scroll_one_pass(page, max_wait_ms=load_wait_ms):
            stall_count = 0
        else:
            # The scroll waited for older messages and none came. That is the
            # stall signal (`history.harvest_history` reasons the same way).
            stall_count += 1
        passes_used += 1
        logger.info("Pass %s (stall %s/%s)", passes_used, stall_count, stall_threshold)


def _reload_to_chat_list(page: Page) -> None:
    """Reload WhatsApp Web and block until the chat list is usable again.

    The heavier recovery, used only when dismissing the search was not enough.

    Args:
        page: WhatsApp Web page.
    """
    logger.info("Reloading WhatsApp Web to recover the chat list")
    page.goto(WA_WEB_URL, wait_until="domcontentloaded")
    wait_until_ready(page)


def search_results_evidence(page: Page) -> dict[str, Any]:
    """Record what a live search left in the chat-list pane.

    This is the measurement that run 1 could not make. Every earlier count came
    from a page with a conversation already open, so which node a search hit
    actually is — and which of its descendants takes the click — has never been
    observed. Both are needed before `_open_first_result` can be corrected in
    the exporter rather than guessed at.

    Args:
        page: Page showing search results for a query already typed.

    Returns:
        dict[str, Any]: Match count per candidate selector, plus the subtree of
            the first hit of the first selector that matched.
    """
    counts = {
        selector: len(page.query_selector_all(selector))
        for selector in SEARCH_CLICK_SELECTORS
    }
    tree: list[dict] = []
    for selector in SEARCH_CLICK_SELECTORS:
        node = page.query_selector(selector)
        if node is None:
            continue
        tree = list(node.evaluate(_RESULT_TREE_JS, RESULT_TREE_LIMIT))
        return {"counts": counts, "first_hit_selector": selector, "first_hit": tree}
    return {"counts": counts, "first_hit_selector": None, "first_hit": tree}


def _click_and_verify(page: Page, query: str, selector: str) -> str | None:
    """Click the first node matching ``selector`` and check what opened.

    Args:
        page: Page showing search results.
        query: Fragment the operator typed, used to verify the conversation.
        selector: Candidate to click.

    Returns:
        str | None: The verified title, or None when this candidate did not
            open a conversation matching ``query``.
    """
    from playwright.sync_api import Error as PlaywrightError

    locator = page.locator(selector)
    try:
        if locator.count() == 0:
            return None
        locator.first.click(timeout=5_000)
    except PlaywrightError as exc:
        logger.debug("Click miss on %s: %s", selector, exc)
        return None

    page.wait_for_timeout(OPEN_SETTLE_MS)
    return _verified_title(page, query)


def _try_open_strategies(page: Page, query: str) -> tuple[str | None, str, dict]:
    """Type ``query`` and try each opening strategy until one verifies.

    Args:
        page: Ready WhatsApp Web page.
        query: Chat fragment typed by the operator.

    Returns:
        tuple[str | None, str, dict]: Verified title (or None), the strategy
            that worked (or ""), and the search-results evidence.
    """
    _search_for(page, query)
    evidence = search_results_evidence(page)

    for selector in SEARCH_CLICK_SELECTORS:
        title = _click_and_verify(page, query, selector)
        if title:
            logger.info("Opened via %s", selector)
            return title, selector, evidence
        _search_for(page, query)

    # There is deliberately no Enter fallback. `_clear_and_type` types into
    # whatever holds focus, and run 2 showed focus can end up outside the search
    # box entirely: for two chats every candidate matched zero nodes, meaning
    # the text never reached the results pane. Pressing Enter in that state, on
    # a page with a conversation open, sends the query to the contact as a
    # message. `export_one._open_first_result:191` still has that fallback.
    return None, "", evidence


def _search_for(page: Page, query: str) -> None:
    """Return to a clean chat list and type ``query`` into the search box.

    Reloading rather than pressing Escape is the lesson of run 2: chats 1-2
    opened, chat 3 could not find the search box, and chats 4-5 searched into
    nothing. State degraded across chats, and Escape from inside a conversation
    did not reliably restore the chat list.

    Args:
        page: WhatsApp Web page in any state.
        query: Fragment to type.

    Raises:
        RuntimeError: If focus lands inside the conversation panel, where typed
            text becomes a draft message rather than a search.
    """
    from whatsapp_chat_extractor.export_one import _type_query

    _reload_to_chat_list(page)
    _type_query(page, query)
    if page.evaluate(_FOCUS_IN_CONVERSATION_JS):
        raise RuntimeError(
            "Focus landed inside the conversation panel, so the query was typed "
            "into the message composer rather than the search box. Refusing to "
            "continue: the next keystroke would edit a real conversation."
        )


def _verified_title(page: Page, query: str) -> str | None:
    """Return the open conversation's title when it matches ``query``."""
    from whatsapp_chat_extractor.export_one import (
        _title_matches_query,
        read_open_chat_title,
    )

    title = read_open_chat_title(page)
    return title if title and _title_matches_query(title, query) else None


def open_for_probe(page: Page, query: str) -> tuple[str | None, str, dict]:
    """Open ``query``'s chat, trying every strategy and recording which worked.

    `export_one.open_chat_by_query` is deliberately **not** called. Run 1 showed
    its click opens nothing in this build, and `_open_first_result:191` then
    presses Enter as a fallback — which, with focus outside the search box, sends
    the query to a contact as a message. The probe reproduces the exporter's
    verification but not that fallback.

    Verification is never relaxed: every strategy must leave a conversation
    whose title contains ``query``, which is hotfix H-001's guarantee. A
    strategy that opens the wrong chat is discarded, not reported.

    Args:
        page: Ready WhatsApp Web page.
        query: Chat fragment typed by the operator.

    Returns:
        tuple[str | None, str, dict]: The verified title (or None), the reason
            it failed (empty when it did not), and a diagnosis recording which
            strategy opened the chat plus the search-results evidence.
    """
    try:
        title, strategy, evidence = _try_open_strategies(page, query)
    except RuntimeError as exc:
        logger.error("Chat could not be opened: %s", exc)
        return None, str(exc)[:300], {"strategy": None}

    diagnosis = {"strategy": strategy or None, "search_results": evidence}
    if title is None:
        return None, "No strategy opened a conversation matching the query", diagnosis
    return title, "", diagnosis


def probe_one_chat(page: Page, query: str, *, max_passes: int) -> dict[str, Any]:
    """Open one chat, scroll it to the top and record the structural evidence.

    Args:
        page: Ready WhatsApp Web page.
        query: Chat fragment typed by the operator.
        max_passes: Hard cap on scroll passes for this chat.

    Returns:
        dict[str, Any]: The chat's pseudonymous id and every measurement taken.
            On failure, ``error`` carries the reason and the rest is absent, so
            one unopenable chat does not void the whole probe.
    """
    title, error, opening = open_for_probe(page, query)
    if title is None:
        return {"chat_id": None, "error": error, "opening": opening}

    scroll = scroll_to_top(page, max_passes=max_passes)
    return {
        "chat_id": pseudonymous_chat_id(title),
        "opening": opening,
        "scroll": scroll,
        "marker": marker_evidence(page),
        "top_chrome": top_chrome_signatures(page),
        "chrome_inventory": chrome_attribute_inventory(page),
        "kinds": kind_census(page),
        "search_scope": search_scope_evidence(page),
    }


def summarize(chats: list[dict[str, Any]], *, min_chats: int) -> dict[str, Any]:
    """Decide H1 versus H2 from the probed chats, or decline to decide.

    Args:
        chats: One entry per probed chat, as `probe_one_chat` returns them.
        min_chats: Below this many successful probes the result is anecdote.

    Returns:
        dict[str, Any]: Counts and a ``verdict`` of ``H1``, ``H2`` or
            ``inconclusive``.
    """
    probed = [c for c in chats if c.get("error") is None]
    with_marker = [c for c in probed if c["marker"]["marker_found"]]
    exhausted = [c for c in probed if c["scroll"]["stopped_reason"] != STOP_MAX_PASSES]
    verdict = "inconclusive"
    if len(probed) >= min_chats and with_marker:
        verdict = "H1"
    elif len(probed) >= min_chats and len(exhausted) >= min_chats:
        verdict = "H2"
    return {
        "chats_requested": len(chats),
        "chats_probed": len(probed),
        "chats_with_marker": len(with_marker),
        "chats_reaching_a_top": len(exhausted),
        "minimum_required": min_chats,
        "verdict": verdict,
    }


def _build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the probe."""
    parser = argparse.ArgumentParser(
        description="Measure whether WA Web draws a start-of-conversation marker.",
    )
    parser.add_argument(
        "-q", "--query", action="append", default=[], metavar="FRAGMENT",
        help="Chat fragment to probe; repeat once per chat (at least 5).",
    )
    parser.add_argument(
        "--min-chats", type=int, default=DEFAULT_MIN_CHATS,
        help=f"Successful probes below which the verdict is anecdote "
             f"(default: {DEFAULT_MIN_CHATS})",
    )
    parser.add_argument(
        "--max-passes", type=int, default=DEFAULT_MAX_PASSES,
        help=f"Scroll passes per chat (default: {DEFAULT_MAX_PASSES})",
    )
    parser.add_argument(
        "--profile-dir", type=Path, default=DEFAULT_PROFILE_DIR,
        help="Persistent Chromium profile (default: data/browser_profile)",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=DEFAULT_OUT_DIR,
        help=f"Where the JSON evidence is written (default: {DEFAULT_OUT_DIR})",
    )
    return parser


def _write_report(report: dict[str, Any], out_dir: Path) -> Path:
    """Write ``report`` under ``out_dir`` and return the path.

    Args:
        report: The probe report.
        out_dir: Directory to create and write into; gitignored `data/` by
            default, because even structural evidence comes from a real session.

    Returns:
        Path: The file written.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"chat_start_probe_{stamp}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _run_probes(args: argparse.Namespace) -> dict[str, Any]:
    """Drive the browser through every requested chat and build the report.

    Args:
        args: Parsed command line.

    Returns:
        dict[str, Any]: The full report, summary included.
    """
    from playwright.sync_api import sync_playwright

    chats: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        context = launch_context(playwright, profile_dir=args.profile_dir)
        try:
            page = open_whatsapp(context)
            wait_until_ready(page)
            for query in args.query:
                logger.info("Probing chat %s of %s", len(chats) + 1, len(args.query))
                chats.append(probe_one_chat(page, query, max_passes=args.max_passes))
        finally:
            context.close()
    return {
        "probe": "chat_start",
        "sprint": "006",
        "taken_at": datetime.now(UTC).isoformat(),
        "chats": chats,
        "summary": summarize(chats, min_chats=args.min_chats),
    }


def main(argv: list[str] | None = None) -> int:
    """Run the probe and report where the evidence landed.

    Returns:
        int: ``0`` when the probe met its chat minimum, ``3`` when it ran but
            probed fewer chats than required, ``2`` when nothing was asked of
            it. The verdict itself never changes the exit code: H2 is a valid
            measurement, not a failure.
    """
    args = _build_parser().parse_args(argv)
    if not args.query:
        logger.error("No chats requested. Pass -q FRAGMENT at least once.")
        return 2

    report = _run_probes(args)
    path = _write_report(report, args.out_dir)
    summary = report["summary"]
    logger.info("Evidence written to %s", path)
    logger.info(
        "Verdict %s: %s of %s chats probed, %s carried a start marker.",
        summary["verdict"], summary["chats_probed"],
        summary["chats_requested"], summary["chats_with_marker"],
    )
    if summary["chats_probed"] < args.min_chats:
        logger.warning(
            "Below the %s-chat minimum: the verdict is anecdote, not evidence.",
            args.min_chats,
        )
        return EXIT_BELOW_MINIMUM
    return 0


if __name__ == "__main__":
    sys.exit(main())
