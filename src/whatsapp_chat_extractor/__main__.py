"""The `wa-extract` command line: argparse wiring, and nothing else.

Every subcommand's behaviour lives in
:mod:`whatsapp_chat_extractor.commands`; this module only describes the
options, binds each subparser to its handler with ``set_defaults(func=...)``,
and translates an escaped exception into a process exit code. The split was
made in Sprint 011 (`IMPLEMENTATION_PLAN.md` §D6), when this file had reached
854 lines by carrying both jobs at once.

No Playwright import appears here or in the import chain this module triggers:
``recover`` and ``consolidate`` must run on a machine that cannot launch
Chromium (`IMPLEMENTATION_PLAN.md` §D4), so the browser is imported inside the
three handlers that actually need it.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from whatsapp_chat_extractor.chat_list import (
    DEFAULT_SETTLE_MS as CHAT_LIST_SETTLE_MS,
)
from whatsapp_chat_extractor.commands import (
    cmd_consolidate,
    cmd_export_all,
    cmd_export_one,
    cmd_login,
    cmd_recover,
)
from whatsapp_chat_extractor.history import (
    DEFAULT_LOAD_WAIT_MS,
    DEFAULT_MAX_PASSES,
    DEFAULT_STALL_THRESHOLD,
)
from whatsapp_chat_extractor.session import DEFAULT_PROFILE_DIR
from whatsapp_chat_extractor.writers import DEFAULT_DATA_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("wa-extract")


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
    parser.add_argument(
        "--deadline-seconds", type=float, default=None,
        help="Wall-clock budget for the whole harvest of one chat, in "
             "seconds (KI-009-H). Unbounded by default: only --max-passes "
             "guarantees termination unless this is set",
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
    export_all.add_argument(
        "--resume", default="", metavar="RUN_ID",
        help="Continue the run with this id: append to its journal and step "
             "over the chats it already exported. The chat list is enumerated "
             "again from scratch, never taken from the journal",
    )
    export_all.add_argument(
        "--timezone", default="", metavar="IANA_ZONE",
        help="Ask the browser to render its clocks in this zone, e.g. "
             "Europe/Madrid. Each export records the zone the page actually "
             "resolved, never this request",
    )
    # Off by default and named for what it does. This is the only flag in the
    # project that causes real conversation names to be written to disk
    # (ADR-0001); the manifest never carries them.
    export_all.add_argument(
        "--write-index", action="store_true",
        help="Also write data/chat_index_<run_id>.json mapping chat_id to the "
             "REAL conversation name. Off by default; delete it when done",
    )
    _add_harvest_args(export_all)
    # Filled in once the session is ready, so it is always present to read.
    export_all.set_defaults(func=cmd_export_all, source_timezone="")


def _add_recover(sub: argparse._SubParsersAction) -> None:
    """Register the `recover` subcommand.

    It takes no browser arguments, because it drives no browser: answering
    "what did that run manage to do?" must not require opening WhatsApp Web
    (`§D4`).

    Args:
        sub: The subparser registry.
    """
    recover = sub.add_parser(
        "recover",
        help="Rebuild a run's manifest from its journal. Opens no browser",
    )
    recover.add_argument(
        "--run-id", required=True,
        help="Identity of the run to rebuild, as it appears in "
             "data/run_journal_<run-id>.ndjson",
    )
    recover.add_argument(
        "--data-dir", type=Path, default=DEFAULT_DATA_DIR,
        help="Directory holding the journal, and where the manifest is written "
             "(default: data/)",
    )
    recover.set_defaults(func=cmd_recover)


def _add_consolidate(sub: argparse._SubParsersAction) -> None:
    """Register the `consolidate` subcommand.

    It takes no browser arguments, because it drives no browser: joining the
    per-conversation export files into one corpus must not require opening
    WhatsApp Web (`§D4`).

    Args:
        sub: The subparser registry.
    """
    consolidate = sub.add_parser(
        "consolidate",
        help="Join data/chat_*.json into one NDJSON corpus. Opens no browser",
    )
    consolidate.add_argument(
        "--data-dir", type=Path, default=DEFAULT_DATA_DIR,
        help="Directory holding the per-conversation export files and, unless "
             "--from-manifest is given, the run manifests (default: data/)",
    )
    consolidate.add_argument(
        "--from-manifest", type=Path, default=None,
        help="Name the source run from this manifest path explicitly, instead "
             "of picking the newest run_manifest_*.json under --data-dir",
    )
    consolidate.add_argument(
        "--out", type=Path, default=None,
        help="Output file (default: <data-dir>/corpus_<source-run>.ndjson)",
    )
    consolidate.set_defaults(func=cmd_consolidate)


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
    _add_recover(sub)
    _add_consolidate(sub)
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
