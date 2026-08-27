"""CLI entrypoints: ``login`` (QR / session) and ``export-one``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from whatsapp_chat_extractor.export_one import (
    collect_visible_messages,
    open_chat_by_query,
    scroll_message_panel,
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
    """Export one human-selected chat to JSON under ``data/``."""
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
            scroll_message_panel(page, passes=args.scroll_passes)
            messages = collect_visible_messages(page)
            export = build_export(
                chat_id=args.chat_id or title,
                title=title,
                messages=messages,
            )
            path = write_chat_export(export, data_dir=args.data_dir)
            print(path)
        finally:
            context.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wa-extract",
        description="WhatsApp Web text export spike (one chat → JSON).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="Open WA Web; wait for QR / chat list")
    _add_shared_args(login)
    login.add_argument(
        "--keep-open",
        action="store_true",
        help="Wait for Enter before closing the browser",
    )
    login.set_defaults(func=cmd_login)

    export_one = sub.add_parser(
        "export-one",
        help="Open one chat by search query and write JSON under data/",
    )
    _add_shared_args(export_one)
    export_one.add_argument(
        "--query",
        required=True,
        help="Chat title / contact fragment (human-chosen)",
    )
    export_one.add_argument(
        "--chat-id",
        default="",
        help="Optional stable id; defaults to resolved title",
    )
    export_one.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Output directory (default: data/)",
    )
    export_one.add_argument(
        "--scroll-passes",
        type=int,
        default=8,
        help="Upward scroll passes before collect (spike, not full history)",
    )
    export_one.set_defaults(func=cmd_export_one)

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
