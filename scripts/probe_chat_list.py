"""Measure the chat list before writing an enumerator against it.

Sprint 007 must export every conversation, and exactly one fact about the chat
list has ever been measured: `probe_chat_start.open_nth_from_list` read a
`list_size` from `[data-testid="cell-frame-container"]`, and a separate count
found 59 rows under `#pane-side div[role="row"]`. Neither answers the two
questions an enumerator depends on:

1. **Does the list virtualize?** If `query_selector_all` returns only the
   rendered rows, "every chat" requires scrolling `#pane-side` itself, not just
   the message panel.
2. **Is a chat's index stable?** WhatsApp reorders the list when a message
   arrives. If index `n` changes conversation mid-run, an index-driven
   enumerator exports one chat twice and skips another **with no error** — the
   same silent class of failure as H-001.

`KI-004-A` is why this is a probe and not an assumption: three successive
theories about a third-party DOM were each wrong and each shipped. This script
measures and reports; it changes nothing and exports nothing.

Privacy: chat titles are read to compute `pseudonymous_chat_id` and are never
stored, logged, or written to the report — the same treatment `writers.py` gives
them. No message body is read at all.

invoked_by: docs/sprints/007-backend-extractor/CHAT_LIST_PROBE_NOTES.md
(operator, manually — it needs a real login and real conversations)

Usage:
    python3 scripts/probe_chat_list.py
    python3 scripts/probe_chat_list.py --settle-ms 3000 --scroll-passes 800

Exit codes:
    0 — the probe ran and both questions carry a verdict
    3 — the probe ran but a verdict is `inconclusive`, which includes a sweep
        that never reached the foot of the pane
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from whatsapp_chat_extractor.session import (
    DEFAULT_PROFILE_DIR,
    launch_context,
    open_whatsapp,
    wait_until_ready,
)
from whatsapp_chat_extractor.writers import pseudonymous_chat_id

if TYPE_CHECKING:  # pragma: no cover - typing only
    from playwright.sync_api import ElementHandle, Page

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("wa-probe-list")

DEFAULT_OUT_DIR = Path("data/probes")
# High enough to reach the foot of a real pane, not a round number. Run 1 met a
# `scroll_height` of 68407 against a 746px viewport: 92 passes to traverse it,
# so a cap of 20 could not have finished even with a correct stop rule. The
# sweep stops at the bottom; this only guarantees termination.
DEFAULT_SCROLL_PASSES = 400
# How long the list gets to render newly requested rows after a scroll.
DEFAULT_SETTLE_MS = 1_200
EXIT_INCONCLUSIVE = 3

# The scrollable chat-list pane. Measured by the Sprint 006 probe, which found
# 59 rows beneath it and zero search-selector leakage outside it.
CHAT_PANE_SELECTOR = "#pane-side"
CHAT_ROW_SELECTOR = '[data-testid="cell-frame-container"]'

# Ordered candidates for a row's title, most specific first. Which one works is
# **measured and reported**, never assumed: this is the same shape as
# `probe_chat_start._try_open_strategies`, and for the same reason.
TITLE_SELECTORS = (
    'span[data-testid="cell-frame-title"] span[title]',
    'span[data-testid="cell-frame-title"]',
    "span[title]",
)

# A pass that reveals no digest the run has not already seen. Three in a row
# means the list stopped producing conversations — but ONLY once the sweep has
# actually reached the bottom of the pane.
#
# Measured, not theorised. Run 1 (2026-08-31) stopped after four passes having
# moved `scroll_top` from 0 to 2238 of a `scroll_height` of 68407 — 3.3% of the
# pane — and reported `not-virtualized` on the strength of three quiet passes.
# The chat list keeps a render buffer far larger than one viewport, so a sweep
# still inside that buffer sees nothing new and looks exactly like a sweep that
# has run out of conversations.
#
# This is `history.py:38-44` again, one panel over: an inference presented as an
# arrival. `W4a` fixed it for the message panel two days earlier by refusing to
# call a stall a top while evidence of more was on screen. Here the evidence is
# arithmetic — unscrolled pixels remain — which is stronger than a spinner.
QUIET_PASSES_TO_STOP = 3
# How close to the foot of the pane counts as having reached it. One viewport,
# because the last scroll step cannot overshoot by more than that.
BOTTOM_TOLERANCE_PX = 1


def _row_title(row: ElementHandle) -> str:
    """The conversation title of one chat-list row, or an empty string.

    The title is a person's name. It is returned so the caller can hash it
    immediately and is never logged or written.

    Args:
        row: A chat-list row element.

    Returns:
        str: The title as rendered, or ``""`` when no candidate matched.
    """
    for selector in TITLE_SELECTORS:
        node = row.query_selector(selector)
        if node is None:
            continue
        text = (node.get_attribute("title") or node.inner_text() or "").strip()
        if text:
            return text
    return ""


def _working_title_selector(rows: list[ElementHandle]) -> str:
    """Which of ``TITLE_SELECTORS`` actually yields a title on these rows.

    Reported so the notes record what was measured rather than what was hoped.

    Args:
        rows: Chat-list rows currently in the DOM.

    Returns:
        str: The first selector that matched on any row, or ``"none"``.
    """
    for selector in TITLE_SELECTORS:
        for row in rows:
            node = row.query_selector(selector)
            if node is None:
                continue
            if ((node.get_attribute("title") or node.inner_text() or "").strip()):
                return selector
    return "none"


def read_list_digests(page: Page) -> tuple[list[str], int]:
    """Pseudonymous digests of every chat-list row currently in the DOM.

    Args:
        page: WhatsApp Web page showing the chat list.

    Returns:
        tuple[list[str], int]: Digests in list order, and how many rows carried
            no readable title (those get no digest and are counted instead).
    """
    rows = page.query_selector_all(CHAT_ROW_SELECTOR)
    digests: list[str] = []
    untitled = 0
    for row in rows:
        title = _row_title(row)
        if not title:
            untitled += 1
            continue
        digests.append(pseudonymous_chat_id(title))
    return digests, untitled


def _pane_metrics(page: Page) -> dict[str, int]:
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


def _scroll_pane(page: Page, *, settle_ms: int) -> None:
    """Scroll the chat pane down by one viewport and wait for it to settle.

    Args:
        page: WhatsApp Web page showing the chat list.
        settle_ms: How long to wait for newly requested rows to render.
    """
    page.evaluate(
        """(selector) => {
            const pane = document.querySelector(selector);
            if (pane) pane.scrollTop += pane.clientHeight;
        }""",
        CHAT_PANE_SELECTOR,
    )
    page.wait_for_timeout(settle_ms)


def at_pane_bottom(metrics: dict[str, int]) -> bool:
    """Whether the pane has been scrolled to its foot.

    Args:
        metrics: A reading from :func:`_pane_metrics`.

    Returns:
        bool: True when no scrollable distance remains. A pane reporting a
            zero ``scroll_height`` is treated as **not** at the bottom: that is
            an unreadable pane, and calling it finished is the error this
            function exists to prevent.
    """
    if metrics["scroll_height"] <= 0:
        return False
    remaining = (
        metrics["scroll_height"] - metrics["scroll_top"] - metrics["client_height"]
    )
    return remaining <= BOTTOM_TOLERANCE_PX


def measure_virtualization(
    page: Page, *, scroll_passes: int, settle_ms: int
) -> dict[str, Any]:
    """Scroll the chat list to its foot and record what each pass adds.

    Args:
        page: WhatsApp Web page showing the chat list.
        scroll_passes: Hard cap on passes; guarantees termination.
        settle_ms: Wait after each scroll.

    Returns:
        dict[str, Any]: Per-pass rows plus a verdict.
    """
    seen: set[str] = set()
    passes: list[dict[str, Any]] = []
    quiet = 0
    max_rendered = 0
    reached_bottom = False
    for index in range(scroll_passes):
        digests, untitled = read_list_digests(page)
        added = [digest for digest in digests if digest not in seen]
        seen.update(added)
        max_rendered = max(max_rendered, len(digests))
        metrics = _pane_metrics(page)
        reached_bottom = at_pane_bottom(metrics)
        passes.append({
            "pass": index + 1, "rendered_rows": len(digests),
            "untitled_rows": untitled, "new_digests": len(added),
            "total_distinct": len(seen), "at_bottom": reached_bottom, **metrics,
        })
        # Quiet passes only mean "no more conversations" once there is nothing
        # left to scroll. Before that they mean the sweep is inside the render
        # buffer, which is not the same statement at all.
        quiet = quiet + 1 if not added else 0
        if reached_bottom and quiet >= QUIET_PASSES_TO_STOP:
            break
        _scroll_pane(page, settle_ms=settle_ms)
    return {
        "passes": passes,
        "max_rendered_at_once": max_rendered,
        "total_distinct_digests": len(seen),
        "reached_bottom": reached_bottom,
        "coverage": _coverage(passes),
        "verdict": virtualization_verdict(
            max_rendered, len(seen), len(passes), reached_bottom=reached_bottom
        ),
        "digests": sorted(seen),
    }


def _coverage(passes: list[dict[str, Any]]) -> dict[str, int | float]:
    """How much of the pane the sweep actually traversed.

    Args:
        passes: Per-pass records from :func:`measure_virtualization`.

    Returns:
        dict[str, int | float]: Final scroll position, total height, and the
            fraction covered. Reported so a verdict can never again rest on a
            sweep that moved 3% of the pane without that being visible.
    """
    if not passes:
        return {"scroll_top": 0, "scroll_height": 0, "fraction": 0.0}
    last = passes[-1]
    height = last["scroll_height"]
    covered = last["scroll_top"] + last["client_height"]
    return {
        "scroll_top": last["scroll_top"],
        "scroll_height": height,
        "fraction": round(covered / height, 4) if height else 0.0,
    }


def virtualization_verdict(
    max_rendered: int, total_distinct: int, passes_used: int, *, reached_bottom: bool
) -> str:
    """Whether scrolling revealed conversations the DOM did not already hold.

    ``not-virtualized`` is a claim about the **whole** list, so it requires the
    sweep to have reached the foot of the pane. Without that, an unchanged count
    says only that nothing new appeared in the stretch that was traversed —
    which is equally true of a sweep still inside the render buffer.

    ``virtualized`` needs no such condition: seeing more conversations than were
    ever in the DOM at once proves virtualization wherever it is observed.

    Args:
        max_rendered: Most rows present in the DOM at any one moment.
        total_distinct: Distinct conversations seen across every pass.
        passes_used: Passes actually run.
        reached_bottom: Whether the sweep reached the foot of the pane.

    Returns:
        str: ``virtualized``, ``not-virtualized`` or ``inconclusive``.
    """
    if total_distinct > max_rendered:
        return "virtualized"
    if passes_used < 2 or not reached_bottom:
        return "inconclusive"
    return "not-virtualized"


def measure_index_stability(
    page: Page, *, settle_ms: int
) -> dict[str, Any]:
    """Read the list twice and report whether position still means chat.

    The two readings are separated by a scroll to the top and a settle, which is
    the least disruptive thing an enumerator does between conversations. A run
    that opens chats does strictly more, so instability here is a lower bound.

    Args:
        page: WhatsApp Web page showing the chat list.
        settle_ms: Wait between the two readings.

    Returns:
        dict[str, Any]: Both readings, positions compared, and a verdict.
    """
    first, _ = read_list_digests(page)
    page.evaluate(
        """(selector) => {
            const pane = document.querySelector(selector);
            if (pane) pane.scrollTop = 0;
        }""",
        CHAT_PANE_SELECTOR,
    )
    page.wait_for_timeout(settle_ms)
    second, _ = read_list_digests(page)
    compared = min(len(first), len(second))
    changed = [i for i in range(compared) if first[i] != second[i]]
    return {
        "reading_1_rows": len(first),
        "reading_2_rows": len(second),
        "positions_compared": compared,
        "positions_that_changed": len(changed),
        "changed_positions": changed[:20],
        "duplicate_digests_in_reading_1": len(first) - len(set(first)),
        "verdict": "inconclusive" if compared == 0 else (
            "stable" if not changed else "unstable"
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    """Command line for the chat-list probe.

    Returns:
        argparse.ArgumentParser: The configured parser.
    """
    parser = argparse.ArgumentParser(
        description="Measure whether the WhatsApp Web chat list virtualizes "
                    "and whether a chat's index is stable.",
    )
    parser.add_argument(
        "--scroll-passes", type=int, default=DEFAULT_SCROLL_PASSES,
        help="Hard cap on chat-list scroll passes (default: %(default)s). The "
             "sweep stops when it reaches the foot of the pane; this only "
             "guarantees termination.",
    )
    parser.add_argument(
        "--settle-ms", type=int, default=DEFAULT_SETTLE_MS,
        help="Wait after each scroll, in ms (default: %(default)s).",
    )
    parser.add_argument(
        "--profile-dir", type=Path, default=DEFAULT_PROFILE_DIR,
        help="Persistent browser profile (default: %(default)s).",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=DEFAULT_OUT_DIR,
        help="Where the JSON report is written (default: %(default)s).",
    )
    return parser


def _write_report(report: dict[str, Any], out_dir: Path) -> Path:
    """Write ``report`` under ``out_dir`` and return the path.

    Args:
        report: The probe report.
        out_dir: Directory to create and write into; gitignored ``data/`` by
            default, because even structural evidence comes from a real session.

    Returns:
        Path: The file written.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"chat_list_probe_{stamp}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _run_probe(args: argparse.Namespace) -> dict[str, Any]:
    """Drive the browser through both measurements and build the report.

    Args:
        args: Parsed command line.

    Returns:
        dict[str, Any]: The full report.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        context = launch_context(playwright, profile_dir=args.profile_dir)
        try:
            page = open_whatsapp(context)
            wait_until_ready(page)
            title_selector = _working_title_selector(
                page.query_selector_all(CHAT_ROW_SELECTOR)
            )
            virtualization = measure_virtualization(
                page, scroll_passes=args.scroll_passes, settle_ms=args.settle_ms
            )
            stability = measure_index_stability(page, settle_ms=args.settle_ms)
        finally:
            context.close()
    return {
        "probe": "chat_list",
        "sprint": "007",
        "taken_at": datetime.now(UTC).isoformat(),
        "title_selector_used": title_selector,
        "virtualization": virtualization,
        "index_stability": stability,
    }


def main(argv: list[str] | None = None) -> int:
    """Run the probe and report where the evidence landed.

    Returns:
        int: ``0`` when both questions carry a verdict, ``3`` when either is
            ``inconclusive``. A verdict of ``virtualized`` or ``unstable`` is a
            measurement, not a failure, and does not change the exit code.
    """
    args = _build_parser().parse_args(argv)
    report = _run_probe(args)
    path = _write_report(report, args.out_dir)
    virtualization = report["virtualization"]
    stability = report["index_stability"]
    logger.info("Evidence written to %s", path)
    coverage = virtualization["coverage"]
    logger.info(
        "Virtualization: %s — %s distinct conversations, at most %s rendered "
        "at once, over %s passes.",
        virtualization["verdict"], virtualization["total_distinct_digests"],
        virtualization["max_rendered_at_once"], len(virtualization["passes"]),
    )
    logger.info(
        "Pane coverage: %s%% (%s of %s px), reached_bottom=%s.",
        round(coverage["fraction"] * 100, 1), coverage["scroll_top"],
        coverage["scroll_height"], virtualization["reached_bottom"],
    )
    if not virtualization["reached_bottom"]:
        logger.warning(
            "The sweep never reached the foot of the pane, so no claim about "
            "the whole list is supported. Raise --scroll-passes."
        )
    logger.info(
        "Index stability: %s — %s of %s positions changed between two readings.",
        stability["verdict"], stability["positions_that_changed"],
        stability["positions_compared"],
    )
    logger.info("Title selector that worked: %s", report["title_selector_used"])
    if "inconclusive" in (virtualization["verdict"], stability["verdict"]):
        logger.warning(
            "A verdict is inconclusive. Re-run with more --scroll-passes, or "
            "from an account with more conversations. An inconclusive result "
            "is an honest one: the alternative is the verdict run 1 produced, "
            "which named a whole list from 3%% of it."
        )
        return EXIT_INCONCLUSIVE
    return 0


if __name__ == "__main__":
    sys.exit(main())
