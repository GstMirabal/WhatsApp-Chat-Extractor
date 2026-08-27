"""Open one WhatsApp Web chat and collect visible text messages."""

from __future__ import annotations

import logging
import re
import sys
from typing import TYPE_CHECKING

from whatsapp_chat_extractor.writers import MessageRecord

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page

logger = logging.getLogger(__name__)

# WA Web churns testids; prefer role/placeholder (ES + EN), then CSS fallbacks.
SEARCH_ICON_SELECTORS = (
    'span[data-icon="search"]',
    'span[data-icon="search-refreshed"]',
    'button[aria-label*="Search"]',
    'button[aria-label*="Buscar"]',
    '[data-testid="chat-list-search"]',
)
CHAT_SEARCH_SELECTORS = (
    'div[contenteditable="true"][data-tab="3"]',
    'div[contenteditable="true"][role="textbox"][data-tab="3"]',
    'div[title="Search input textbox"]',
    'div[title="Cuadro de texto de búsqueda"]',
    '#side div[contenteditable="true"][role="textbox"]',
    'div[contenteditable="true"][data-tab="2"]',
)
SEARCH_PLACEHOLDERS = (
    "Buscar un chat o iniciar uno nuevo",
    "Search or start new chat",
    "Search input textbox",
    "Buscar o empezar un chat nuevo",
)
SEARCH_RESULT_SELECTORS = (
    '#pane-side div[role="listitem"]',
    '#pane-side div[role="row"]',
    '[data-testid="cell-frame-container"]',
    '#side div[role="listitem"]',
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


def _click_search_icon(page: Page) -> None:
    """Open the search field if WA shows an icon instead of a permanent box."""
    icon = _first_selector(page, SEARCH_ICON_SELECTORS)
    if icon is None:
        return
    try:
        page.click(icon, timeout=3_000)
        page.wait_for_timeout(300)
    except Exception:
        logger.debug("Search icon click skipped", exc_info=True)


def _locate_search_box(page: Page) -> Locator | None:
    """Return a Playwright locator for the chat-list search textbox."""
    for placeholder in SEARCH_PLACEHOLDERS:
        loc = page.get_by_placeholder(placeholder)
        if loc.count() > 0:
            return loc.first
    role = page.get_by_role("textbox", name=re.compile(r"search|buscar", re.IGNORECASE))
    if role.count() > 0:
        return role.first
    css = _first_selector(page, CHAT_SEARCH_SELECTORS)
    if css is not None:
        return page.locator(css).first
    return None


def _clear_and_type(page: Page, query: str) -> None:
    """Clear the focused field and type ``query`` (contenteditable-safe)."""
    mod = "Meta" if sys.platform == "darwin" else "Control"
    page.keyboard.press(f"{mod}+A")
    page.keyboard.press("Backspace")
    page.keyboard.type(query, delay=40)
    page.wait_for_timeout(800)


def _type_query(page: Page, query: str) -> None:
    """Focus search and type ``query``."""
    _click_search_icon(page)
    box = _locate_search_box(page)
    if box is None:
        raise RuntimeError(
            "Chat search box not found; update SEARCH_* selectors in export_one.py "
            "(see SPIKE_NOTES.md)."
        )
    box.click(timeout=5_000)
    _clear_and_type(page, query)


def _open_first_result(page: Page, timeout_ms: int) -> None:
    """Click the first search hit, else press Enter and wait for the panel."""
    from playwright.sync_api import Error as PlaywrightError

    for selector in SEARCH_RESULT_SELECTORS:
        loc = page.locator(selector)
        try:
            if loc.count() == 0:
                continue
            loc.first.click(timeout=5_000)
            return
        except PlaywrightError as exc:
            logger.debug("Search result click miss on %s: %s", selector, exc)
            continue
    page.keyboard.press("Enter")
    page.wait_for_selector(", ".join(MESSAGE_PANEL_SELECTORS), timeout=timeout_ms)


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
    try:
        _type_query(page, query)
        _open_first_result(page, timeout_ms)
        page.wait_for_selector(", ".join(MESSAGE_PANEL_SELECTORS), timeout=timeout_ms)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"Could not open chat for query={query!r}; see SPIKE_NOTES.md"
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
