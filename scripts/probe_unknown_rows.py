"""Capture the DOM signature of every row the classifiers cannot read.

Two fields fall back to ``unknown`` and both rates rose in Sprint 007's live run:

===============  ==========================================================
``sender``       5 of 129 messages (3.9%), against 0 of 513 in Sprint 004
``kind``         30 of 311 rows (9.6%), against 6 of 301 in Sprint 005
===============  ==========================================================

Either figure could be chat-dependent or a regression; nothing measured so far
separates the two. `KI-004-A` is why this is a probe and not a fix: three
successive theories about this DOM were each wrong and each shipped, the last
producing a 513-message export with every sender ``unknown``.

**This script classifies nothing and proposes nothing.** For each row that
``_row_sender`` or ``_row_kind`` gives up on, it records which known selectors
were tried and missed, and what the row actually carries — attribute names,
class tokens, ``data-*`` keys, the shape of any ``aria-label``. The output is
the input to a later decision, not the decision.

Privacy: no message body, no ``aria-label`` value, no ``data-pre-plain-text``
value and no title is ever written. Only **presence** and **structure** are
recorded — an attribute's name, never its content — because the values are the
conversation. Chat titles are hashed through ``pseudonymous_chat_id`` exactly as
``writers.py`` treats them.

invoked_by: docs/sprints/008-backend-extractor/PROBE_UNKNOWN_ROWS_RUN.md
(operator, manually — it needs a real login and real conversations)

Usage:
    python3 scripts/probe_unknown_rows.py
    python3 scripts/probe_unknown_rows.py --chats 5 --max-signatures 20

Exit codes:
    0 — the probe ran and at least one unknown row was captured
    3 — the probe ran and found no unknown rows, so it measured nothing
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
    IMAGE_SELECTOR,
    TAIL_IN_SELECTOR,
    TAIL_OUT_SELECTOR,
    VOICE_SELECTOR,
    _row_body,
    _row_kind,
    _row_sender,
    read_open_chat_title,
)
from whatsapp_chat_extractor.session import (
    launch_context,
    open_whatsapp,
    wait_until_ready,
)
from whatsapp_chat_extractor.writers import pseudonymous_chat_id

if TYPE_CHECKING:  # pragma: no cover - typing only
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)

UNKNOWN = "unknown"
DEFAULT_CHATS = 5
DEFAULT_MAX_SIGNATURES = 12
DEFAULT_SETTLE_MS = 1_200

# Every selector the two classifiers consult, named so a signature can say which
# ones were tried rather than leaving a reader to rediscover them.
SENDER_SELECTORS = {
    "tail_out": TAIL_OUT_SELECTOR,
    "tail_in": TAIL_IN_SELECTOR,
    "receipt": '[data-testid="msg-dblcheck"], [data-testid="msg-check"]',
    "speaker_label": "[aria-label]",
    "pre_plain": "[data-pre-plain-text]",
}
KIND_SELECTORS = {"voice": VOICE_SELECTOR, "image": IMAGE_SELECTOR}


def selector_hits(row: object, selectors: dict[str, str]) -> dict[str, bool]:
    """Which of ``selectors`` match ``row``, by name.

    Args:
        row: Element handle for one message row.
        selectors: Name to CSS selector.

    Returns:
        dict[str, bool]: One entry per selector, True when it matched. A row
            whose every entry is False is the interesting case: it means the
            classifier had nothing to go on, rather than having read a signal
            and drawn the wrong conclusion.
    """
    hits: dict[str, bool] = {}
    for name, selector in selectors.items():
        try:
            hits[name] = row.query_selector(selector) is not None  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001 - a bad selector must not end the probe
            logger.warning("Selector %s failed on a row: %s", name, exc)
            hits[name] = False
    return hits


def structural_shape(row: object) -> dict[str, Any]:
    """What a row carries, by name and shape only — never by value.

    Reads attribute **names**, class **tokens** and the presence of the two
    attributes the direction contract depends on. Values are deliberately not
    returned: `aria-label` and `data-pre-plain-text` both contain the sender's
    real name, and this file is written to gitignored ``data/`` but is still a
    file (`ADR-0001`).

    Args:
        row: Element handle for one message row.

    Returns:
        dict[str, Any]: ``attributes`` (sorted names), ``classes`` (sorted
            tokens), ``has_aria_label``, ``has_pre_plain_text``,
            ``aria_label_ends_with_colon`` and ``child_count``.
    """
    shape = row.evaluate(  # type: ignore[attr-defined]
        """(node) => {
            const label = node.getAttribute('aria-label') || '';
            return {
                attributes: Array.from(node.attributes).map(a => a.name).sort(),
                classes: Array.from(node.classList).sort(),
                has_aria_label: label.length > 0,
                has_pre_plain_text:
                    node.querySelector('[data-pre-plain-text]') !== null,
                aria_label_ends_with_colon: label.trim().endsWith(':'),
                child_count: node.children.length,
            };
        }"""
    )
    return dict(shape)


def signature_for(row: object, *, chat_title: str) -> dict[str, Any] | None:
    """The record for one row, or None when both classifiers resolved it.

    Args:
        row: Element handle for one message row.
        chat_title: Title of the open conversation, used only for comparison
            inside ``_row_sender`` and never stored.

    Returns:
        dict[str, Any] | None: The signature when `sender` or `kind` came back
            ``unknown``; None otherwise.
    """
    body = _row_body(row)
    sender = _row_sender(row, chat_title=chat_title)
    kind = _row_kind(row, body)
    if sender != UNKNOWN and kind != UNKNOWN:
        return None
    return {
        "sender": sender,
        "kind": kind,
        "has_body": bool(body),
        "sender_selectors": selector_hits(row, SENDER_SELECTORS),
        "kind_selectors": selector_hits(row, KIND_SELECTORS),
        "shape": structural_shape(row),
    }


def probe_open_chat(page: Page, *, max_signatures: int) -> dict[str, Any]:
    """Walk the rows currently rendered in the open conversation.

    Only the rendered window is read. Scrolling the panel would multiply the
    session cost of a probe whose purpose is to characterise a signature, and a
    9.6% rate means the window already holds several instances.

    Args:
        page: WhatsApp Web page with a conversation open.
        max_signatures: Stop after this many unknown rows in this conversation.

    Returns:
        dict[str, Any]: Counts for the conversation plus the captured
            signatures. The title is hashed, never stored.
    """
    title = read_open_chat_title(page)
    rows = page.query_selector_all('[data-testid="msg-container"]')
    signatures: list[dict[str, Any]] = []
    for row in rows:
        signature = signature_for(row, chat_title=title)
        if signature is not None and len(signatures) < max_signatures:
            signatures.append(signature)
    return {
        "chat_id": pseudonymous_chat_id(title),
        "rows_examined": len(rows),
        "unknown_sender": sum(1 for s in signatures if s["sender"] == UNKNOWN),
        "unknown_kind": sum(1 for s in signatures if s["kind"] == UNKNOWN),
        "signatures": signatures,
    }


def summarize(chats: list[dict[str, Any]]) -> dict[str, Any]:
    """Rates across every conversation the probe visited.

    Args:
        chats: One entry per conversation, from :func:`probe_open_chat`.

    Returns:
        dict[str, Any]: Totals and the two rates, or zeroes when nothing was
            examined. A rate over zero rows is reported as ``0.0`` rather than
            omitted, so a run that saw nothing is visible instead of absent.
    """
    examined = sum(chat["rows_examined"] for chat in chats)
    unknown_sender = sum(chat["unknown_sender"] for chat in chats)
    unknown_kind = sum(chat["unknown_kind"] for chat in chats)
    return {
        "chats": len(chats),
        "rows_examined": examined,
        "unknown_sender": unknown_sender,
        "unknown_kind": unknown_kind,
        "unknown_sender_rate": round(unknown_sender / examined, 4) if examined else 0.0,
        "unknown_kind_rate": round(unknown_kind / examined, 4) if examined else 0.0,
    }


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
    path = out_dir / f"unknown_rows_probe_{stamp}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _build_parser() -> argparse.ArgumentParser:
    """The command line.

    Returns:
        argparse.ArgumentParser: The configured parser.
    """
    parser = argparse.ArgumentParser(
        description="Capture DOM signatures of rows with an unknown sender or kind.",
    )
    parser.add_argument("--chats", type=int, default=DEFAULT_CHATS,
                        help="How many conversations to visit, from the list head.")
    parser.add_argument("--max-signatures", type=int, default=DEFAULT_MAX_SIGNATURES,
                        help="Cap on captured signatures per conversation.")
    parser.add_argument("--settle-ms", type=int, default=DEFAULT_SETTLE_MS,
                        help="Wait after opening a conversation.")
    parser.add_argument("--profile-dir", type=Path, default=None,
                        help="Persistent Chromium profile directory.")
    parser.add_argument("--out-dir", type=Path, default=Path("data"),
                        help="Where to write the JSON evidence.")
    return parser


def _visit_chats(page: Page, args: argparse.Namespace) -> list[dict[str, Any]]:
    """Open each of the first ``--chats`` conversations and probe it.

    Args:
        page: Ready WhatsApp Web page showing the chat list.
        args: Parsed command line.

    Returns:
        list[dict[str, Any]]: One entry per conversation successfully opened. A
            conversation that fails is logged and skipped: a probe that dies on
            one chat measures nothing about the other four.
    """
    from whatsapp_chat_extractor.chat_list import (
        open_chat_by_digest,
        sweep_until_stable,
    )

    enumerated = sweep_until_stable(page, settle_ms=args.settle_ms)
    refs = enumerated["refs"][: args.chats]
    chats: list[dict[str, Any]] = []
    for ref in refs:
        try:
            open_chat_by_digest(page, ref, total=len(enumerated["refs"]),
                                settle_ms=args.settle_ms)
            chats.append(probe_open_chat(page, max_signatures=args.max_signatures))
        except (LookupError, RuntimeError) as exc:
            logger.warning("Chat %s could not be probed: %s", ref["chat_id"], exc)
    return chats


def _run_probe(args: argparse.Namespace) -> dict[str, Any]:
    """Drive the browser and build the report.

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
            chats = _visit_chats(page, args)
        finally:
            context.close()
    return {
        "probe": "unknown_rows",
        "sprint": "008",
        "taken_at": datetime.now(UTC).isoformat(),
        "summary": summarize(chats),
        "chats": chats,
    }


def main(argv: list[str] | None = None) -> int:
    """Run the probe and report where the evidence landed.

    Returns:
        int: ``0`` when at least one unknown row was captured, ``3`` when none
            was. Zero unknown rows is not success: it means this run produced no
            evidence about the thing it exists to characterise.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)
    report = _run_probe(args)
    path = _write_report(report, args.out_dir)
    summary = report["summary"]
    logger.info("Evidence written to %s", path)
    logger.info(
        "%s rows over %s conversations: %s unknown sender (%s), %s unknown kind (%s)",
        summary["rows_examined"], summary["chats"], summary["unknown_sender"],
        summary["unknown_sender_rate"], summary["unknown_kind"],
        summary["unknown_kind_rate"],
    )
    if not summary["unknown_sender"] and not summary["unknown_kind"]:
        logger.error("No unknown rows found, so this run characterises nothing.")
        return 3
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    sys.exit(main())
