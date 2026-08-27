"""Open one WhatsApp Web chat and collect visible text messages."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from whatsapp_chat_extractor.writers import MessageRecord

if TYPE_CHECKING:
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)

CHAT_SEARCH_SELECTORS = (
    '[data-testid="chat-list-search"]',
    'div[contenteditable="true"][data-tab="3"]',
    '[title="Search input textbox"]',
)
MESSAGE_PANEL_SELECTORS = (
    '[data-testid="conversation-panel-messages"]',
    '#main div[role="application"]',
    "#main",
)
MESSAGE_ROW_SELECTORS = (
    'div[data-testid="msg-container"]',
    "#main div.message-in, #main div.message-out",
)
TITLE_SELECTORS = (
    '#main header span[dir="auto"]',
    '[data-testid="conversation-info-header"] span[dir="auto"]',
)


def _first_selector(page: Page, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        if page.query_selector(selector):
            return selector
    return None


def open_chat_by_query(page: Page, query: str, *, timeout_ms: int = 30_000) -> str:
    """Search the chat list and open the first match for ``query``.

    Args:
        page: Ready WhatsApp Web page.
        query: Chat title / contact fragment typed by the human.
        timeout_ms: Wait for search results / conversation panel.

    Returns:
        Resolved chat title from the conversation header when available.

    Raises:
        RuntimeError: If search UI or results cannot be used.
    """
    search = _first_selector(page, CHAT_SEARCH_SELECTORS)
    if search is None:
        raise RuntimeError(
            "Chat search box not found; update CHAT_SEARCH_SELECTORS in export_one.py"
        )

    page.click(search)
    page.fill(search, "")
    page.type(search, query, delay=40)
    page.keyboard.press("Enter")

    panel = ", ".join(MESSAGE_PANEL_SELECTORS)
    try:
        page.wait_for_selector(panel, timeout=timeout_ms)
    except Exception as exc:
        raise RuntimeError(
            f"Conversation panel did not open for query={query!r}"
        ) from exc

    title = read_open_chat_title(page) or query
    logger.info("Opened chat title=%r query=%r", title, query)
    return title


def read_open_chat_title(page: Page) -> str:
    """Best-effort title from the open conversation header."""
    for selector in TITLE_SELECTORS:
        node = page.query_selector(selector)
        if node is None:
            continue
        text = (node.inner_text() or "").strip()
        if text:
            return text
    return ""


def scroll_message_panel(page: Page, *, passes: int = 8) -> None:
    """Scroll the message panel upward to load older visible history.

    Args:
        page: Page with an open conversation.
        passes: Number of PageUp-style scrolls (spike default, not full history).
    """
    panel_sel = _first_selector(page, MESSAGE_PANEL_SELECTORS)
    if panel_sel is None:
        logger.warning("No message panel for scrolling")
        return
    handle = page.query_selector(panel_sel)
    if handle is None:
        return
    for _ in range(passes):
        handle.evaluate("el => { el.scrollTop = 0; }")
        page.wait_for_timeout(400)


def collect_visible_messages(page: Page) -> list[MessageRecord]:
    """Collect text-only messages currently in the DOM (spike, not full history).

    Args:
        page: Page with an open conversation.

    Returns:
        Ordered ``MessageRecord`` list; empty if selectors miss.
    """
    row_sel = _first_selector(page, MESSAGE_ROW_SELECTORS)
    if row_sel is None:
        logger.warning("No message rows found")
        return []

    rows = page.query_selector_all(row_sel)
    records: list[MessageRecord] = []
    order = 0
    for row in rows:
        body = _row_body(row)
        if not body:
            continue
        sender = _row_sender(row)
        timestamp = _row_timestamp(row)
        records.append(
            {
                "sender": sender,
                "timestamp": timestamp,
                "body": body,
                "order": order,
            }
        )
        order += 1
    logger.info("Collected %s visible text messages", len(records))
    return records


def _row_body(row: object) -> str:
    selectable = row.query_selector(  # type: ignore[attr-defined]
        'span.selectable-text, span[data-testid="msg-text"], div.copyable-text'
    )
    if selectable is None:
        return ""
    return (selectable.inner_text() or "").strip()


def _row_sender(row: object) -> str:
    if row.query_selector(  # type: ignore[attr-defined]
        '[data-testid="msg-dblcheck"], [data-testid="msg-check"]'
    ):
        return "me"
    pre = row.get_attribute("data-pre-plain-text")  # type: ignore[attr-defined]
    if pre:
        match = re.match(r"\[.*?\]\s*(.+?):\s*$", pre.strip())
        if match:
            return match.group(1).strip()
    author = row.query_selector(  # type: ignore[attr-defined]
        'span[aria-label*="You"], span.chat-title, span[dir="auto"]'
    )
    if author:
        text = (author.inner_text() or "").strip()
        if text:
            return text
    return "contact"


def _row_timestamp(row: object) -> str:
    meta = row.query_selector(  # type: ignore[attr-defined]
        '[data-testid="msg-meta"] span, span[dir="auto"].x1rg5ohu, div.copyable-text'
    )
    if meta is None:
        pre = row.get_attribute("data-pre-plain-text")  # type: ignore[attr-defined]
        return (pre or "").strip()
    return (meta.inner_text() or "").strip()
