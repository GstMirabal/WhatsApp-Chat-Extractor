"""CLI entrypoints: ``login`` (QR / session) and ``export-one``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from whatsapp_chat_extractor.chat_list import (
    DEFAULT_SETTLE_MS as CHAT_LIST_SETTLE_MS,
)
from whatsapp_chat_extractor.chat_list import (
    ENUMERATION_CONVERGED,
    open_chat_by_digest,
    sweep_until_stable,
)
from whatsapp_chat_extractor.export_one import open_chat_by_query
from whatsapp_chat_extractor.history import (
    COMPLETENESS_TRUNCATED,
    COMPLETENESS_UNPROVEN,
    DEFAULT_LOAD_WAIT_MS,
    DEFAULT_MAX_PASSES,
    DEFAULT_STALL_THRESHOLD,
    harvest_history,
)
from whatsapp_chat_extractor.manifest import (
    build_manifest,
    exported,
    failed,
    now,
    skipped,
    write_chat_index,
    write_manifest,
)
from whatsapp_chat_extractor.session import (
    DEFAULT_PROFILE_DIR,
    launch_context,
    open_whatsapp,
    qr_visible,
    wait_until_ready,
)
from whatsapp_chat_extractor.writers import (
    DEFAULT_DATA_DIR,
    build_export,
    write_chat_export,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("wa-extract")

EXIT_INCOMPLETE = 3


def _add_shared_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile-dir",
        type=Path,
        default=DEFAULT_PROFILE_DIR,
        help="Persistent Chromium profile (default: data/browser_profile)",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=300_000,
        help="Max wait for ready state / QR (milliseconds)",
    )


def cmd_login(args: argparse.Namespace) -> int:
    """Open WhatsApp Web and wait until the chat list is ready."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        context = launch_context(
            playwright,
            profile_dir=args.profile_dir,
            headless=False,
        )
        try:
            page = open_whatsapp(context)
            if qr_visible(page):
                logger.info("QR visible — scan with the business phone")
            ready = wait_until_ready(page, timeout_ms=args.timeout_ms)
            logger.info("Session ready (%s). Profile kept at %s", ready, args.profile_dir)
            if args.keep_open:
                logger.info("Keeping browser open until Enter…")
                input()
        finally:
            context.close()
    return 0


def cmd_export_one(args: argparse.Namespace) -> int:
    """Export one human-selected chat's full history to JSON under ``data/``.

    Returns:
        int: ``0`` when the harvest reached the start of the chat, ``3`` when it
            stopped at the pass cap, so a caller can tell a complete corpus from
            a truncated one without parsing the file.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        context = launch_context(
            playwright,
            profile_dir=args.profile_dir,
            headless=False,
        )
        try:
            page = open_whatsapp(context)
            wait_until_ready(page, timeout_ms=args.timeout_ms)
            title = open_chat_by_query(page, args.query, timeout_ms=60_000)
            harvest = harvest_history(
                page,
                chat_title=title,
                max_passes=args.max_passes,
                stall_threshold=args.stall_threshold,
                load_wait_ms=args.load_wait_ms,
            )
            export = build_export(
                chat_title=title,
                messages=harvest["messages"],
                completeness=harvest["completeness"],
                stopped_reason=harvest["stopped_reason"],
            )
            path = write_chat_export(export, data_dir=args.data_dir)
            print(path)
        finally:
            context.close()

    return report_completeness(harvest)


def report_completeness(harvest: dict) -> int:
    """Tell the operator what the harvest reached, and pick the exit code.

    Only `truncated` is a failure. Under the v4 boolean this branch fired on
    every single export ever produced, because `complete` was never True
    (ADR-0004): the operator was told each run had failed and to raise a cap
    that was not the cause. `unproven` is the expected outcome and exits 0.

    Args:
        harvest: A ``HarvestResult``.

    Returns:
        int: ``0`` unless the harvest was truncated.
    """
    if harvest["completeness"] == COMPLETENESS_TRUNCATED:
        logger.error(
            "Truncated export: the harvest ended at %s passes (%s) before the "
            "conversation did. Re-run with a higher --max-passes.",
            harvest["passes_used"],
            harvest["stopped_reason"],
        )
        return EXIT_INCOMPLETE
    if harvest["completeness"] == COMPLETENESS_UNPROVEN:
        logger.info(
            "Export complete as far as can be shown: the panel stopped "
            "producing history after %s passes, but no start-of-chat marker "
            "was observed, so the beginning is not proven.",
            harvest["passes_used"],
        )
    return 0


def _export_open_chat(page: object, title: str, args: argparse.Namespace) -> tuple:
    """Harvest and write the conversation currently on screen.

    Args:
        page: Page with the conversation open.
        title: Verified title of that conversation. Hashed, never stored.
        args: Parsed command line.

    Returns:
        tuple: The harvest result and the path written.
    """
    harvest = harvest_history(
        page,
        chat_title=title,
        max_passes=args.max_passes,
        stall_threshold=args.stall_threshold,
        load_wait_ms=args.load_wait_ms,
    )
    export = build_export(
        chat_title=title,
        messages=harvest["messages"],
        completeness=harvest["completeness"],
        stopped_reason=harvest["stopped_reason"],
    )
    return harvest, write_chat_export(export, data_dir=args.data_dir)


def _export_every_chat(page: object, args: argparse.Namespace) -> tuple:
    """Walk the enumerated list, exporting each conversation in turn.

    A failure on one conversation does not end the run: a run of hundreds that
    dies on the third wastes the manual login and the exports already made
    (`IMPLEMENTATION_PLAN.md` §D3). Losing the WhatsApp session does end it,
    because every later attempt would fail identically and produce a manifest
    full of identical failures that says nothing.

    Args:
        page: Ready WhatsApp Web page showing the chat list.
        args: Parsed command line.

    Returns:
        tuple: The outcome entries, the `ADR-0005` enumeration result, and the
            digest-to-title index.
    """
    enumerated = sweep_until_stable(page, settle_ms=args.settle_ms)
    refs = enumerated["refs"]
    targets = refs[: args.limit] if args.limit else refs
    outcomes: list[dict] = []
    index: dict[str, str] = {}
    for position, ref in enumerate(targets, start=1):
        logger.info("Chat %s of %s (%s)", position, len(targets), ref["chat_id"])
        try:
            title = open_chat_by_digest(page, ref, total=len(refs),
                                        settle_ms=args.settle_ms)
            harvest, path = _export_open_chat(page, title, args)
        except (LookupError, RuntimeError) as exc:
            logger.warning("Chat %s failed: %s", ref["chat_id"], exc)
            outcomes.append(failed(ref["chat_id"], index=ref["index"], reason=str(exc)))
            continue
        index[ref["chat_id"]] = title
        outcomes.append(exported(
            ref["chat_id"], index=ref["index"],
            completeness=harvest["completeness"],
            message_count=len(harvest["messages"]), file=path.name,
        ))
    outcomes.extend(
        skipped(ref["chat_id"], index=ref["index"], reason="beyond --limit")
        for ref in refs[len(targets):]
    )
    return outcomes, enumerated, index


def cmd_export_all(args: argparse.Namespace) -> int:
    """Export every conversation in the chat list, and record what happened.

    Returns:
        int: ``0`` when every attempted conversation exported, ``3`` when any
            failed or the enumeration did not reach the foot of the pane. The
            manifest carries the detail either way.
    """
    from playwright.sync_api import sync_playwright

    started_at = now()
    with sync_playwright() as playwright:
        context = launch_context(
            playwright, profile_dir=args.profile_dir, headless=False
        )
        try:
            page = open_whatsapp(context)
            wait_until_ready(page, timeout_ms=args.timeout_ms)
            outcomes, enumerated, index = _export_every_chat(page, args)
        finally:
            context.close()

    manifest = build_manifest(
        outcomes, started_at=started_at,
        chats_enumerated=len(enumerated["refs"]),
        enumeration=enumerated["enumeration"], sweeps=enumerated["sweeps"],
    )
    print(write_manifest(manifest, data_dir=args.data_dir))
    if args.write_index and index:
        write_chat_index(index, data_dir=args.data_dir)
    if enumerated["enumeration"] != ENUMERATION_CONVERGED:
        logger.error(
            "Enumeration is %s over %s sweeps, so this is not a whole-account "
            "export. `truncated` means the sweep never reached the foot of the "
            "chat list: raise --max-passes. `unconverged` means the list was "
            "still yielding new conversations when the sweep budget ran out.",
            enumerated["enumeration"], enumerated["sweeps"],
        )
    converged = enumerated["enumeration"] == ENUMERATION_CONVERGED
    return 0 if converged and not manifest["counts"]["failed"] else EXIT_INCOMPLETE


def _add_harvest_args(parser: argparse.ArgumentParser) -> None:
    """Scroll-and-wait knobs shared by both export subcommands.

    Args:
        parser: The subcommand parser to extend.
    """
    parser.add_argument(
        "--max-passes", type=int, default=DEFAULT_MAX_PASSES,
        help=f"Hard cap on scroll passes per chat (default: {DEFAULT_MAX_PASSES})",
    )
    parser.add_argument(
        "--stall-threshold", type=int, default=DEFAULT_STALL_THRESHOLD,
        help="Consecutive passes without new messages that end one harvest "
             f"(default: {DEFAULT_STALL_THRESHOLD})",
    )
    parser.add_argument(
        "--load-wait-ms", type=int, default=DEFAULT_LOAD_WAIT_MS,
        help="How long one pass waits for older messages from the phone "
             f"(default: {DEFAULT_LOAD_WAIT_MS})",
    )


def _add_login(sub: argparse._SubParsersAction) -> None:
    """Register the `login` subcommand.

    Args:
        sub: The subparser registry.
    """
    login = sub.add_parser("login", help="Open WA Web; wait for QR / chat list")
    _add_shared_args(login)
    login.add_argument(
        "--keep-open",
        action="store_true",
        help="Wait for Enter before closing the browser",
    )
    login.set_defaults(func=cmd_login)



def _add_export_one(sub: argparse._SubParsersAction) -> None:
    """Register the `export-one` subcommand.

    Args:
        sub: The subparser registry.
    """
    export_one = sub.add_parser(
        "export-one",
        help="Open one chat by search query and write its full history to data/",
    )
    _add_shared_args(export_one)
    export_one.add_argument(
        "--query",
        required=True,
        help="Chat title / contact fragment (human-chosen)",
    )
    export_one.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Output directory (default: data/)",
    )
    # No --chat-id: the export is pseudonymous, and a caller-supplied id is a
    # way to put a real name back into the filename and the payload.
    _add_harvest_args(export_one)
    export_one.set_defaults(func=cmd_export_one)



def _add_export_all(sub: argparse._SubParsersAction) -> None:
    """Register the `export-all` subcommand.

    Args:
        sub: The subparser registry.
    """
    export_all = sub.add_parser(
        "export-all",
        help="Enumerate every chat and export each, writing a run manifest",
    )
    _add_shared_args(export_all)
    export_all.add_argument(
        "--data-dir", type=Path, default=DEFAULT_DATA_DIR,
        help="Output directory (default: data/)",
    )
    export_all.add_argument(
        "--limit", type=int, default=0,
        help="Export only the first N enumerated chats (0 = all). The rest are "
             "recorded as skipped rather than omitted",
    )
    export_all.add_argument(
        "--settle-ms", type=int, default=CHAT_LIST_SETTLE_MS,
        help=f"Wait after each chat-list scroll (default: {CHAT_LIST_SETTLE_MS})",
    )
    # Off by default and named for what it does. This is the only flag in the
    # project that causes real conversation names to be written to disk
    # (ADR-0001); the manifest never carries them.
    export_all.add_argument(
        "--write-index", action="store_true",
        help="Also write data/chat_index_<stamp>.json mapping chat_id to the "
             "REAL conversation name. Off by default; delete it when done",
    )
    _add_harvest_args(export_all)
    export_all.set_defaults(func=cmd_export_all)



def build_parser() -> argparse.ArgumentParser:
    """The `wa-extract` command line.

    Returns:
        argparse.ArgumentParser: Parser with every subcommand registered.
    """
    parser = argparse.ArgumentParser(
        prog="wa-extract",
        description="WhatsApp Web text export (one chat, or every chat).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _add_login(sub)
    _add_export_one(sub)
    _add_export_all(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI main. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except TimeoutError as exc:
        logger.error("%s", exc)
        return 2
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
