"""Open one WhatsApp Web chat and read the message panel one pass at a time.

Single-pass primitives only. The loop that walks a whole conversation lives in
`history.harvest_history`, because the panel virtualizes its rows and a correct
walk needs an accumulator, not a scroll count.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import TYPE_CHECKING

from whatsapp_chat_extractor.history import (
    DEFAULT_LOAD_WAIT_MS,
    HarvestedRow,
    fallback_message_id,
)

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
# The control that pulls older history from the phone. Matching `button` alone
# was the first version and it never fired: WhatsApp renders this as a
# `div[role="button"]` in current builds, so the operator had to click it by
# hand on every batch. Tag and locale are both unreliable — the text is what
# identifies it, across whichever element carries it.
LOAD_EARLIER_TESTID = 'button[data-testid="load-earlier-msgs"]'
LOAD_EARLIER_CANDIDATES = (
    '#main button, #main div[role="button"], #main span[role="button"], '
    "#main a, #main [tabindex]"
)
LOAD_EARLIER_PATTERN = re.compile(
    r"mensajes?\s+(m[áa]s\s+)?antiguos"
    r"|mensajes\s+anteriores"
    r"|(older|earlier)\s+messages"
    r"|click\s+here\s+to\s+get"
    r"|haz\s+clic\s+aqu[íi]",
    re.IGNORECASE,
)
# Best-effort start-of-conversation markers. WA Web does not always render one,
# so `history.decide_stop` uses these only to report a *proven* start.
CHAT_START_SELECTORS = (
    '#main [data-icon="lock-refreshed"]',
    '#main [data-testid="msg-system"] [data-icon="lock"]',
    '#main div.message-system [data-icon="lock"]',
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
    # The title is a real person's name. It is returned so the caller can derive
    # a pseudonymous id from it, and is deliberately kept out of the log.
    logger.info("Opened chat for query=%r", query)
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


def panel_signature(page: Page) -> str:
    """A cheap fingerprint of what the message panel currently holds.

    Older messages arriving changes the row count and the panel's scroll height,
    so comparing this before and after a scroll is direct evidence of loading —
    unlike a fixed sleep, which only measures that time passed.

    Args:
        page: Page with an open conversation.

    Returns:
        str: ``"<rowCount>:<scrollHeight>"``, or ``""`` when the panel is gone.
    """
    panel_sel = _first_selector(page, MESSAGE_PANEL_SELECTORS)
    if panel_sel is None:
        return ""
    handle = page.query_selector(panel_sel)
    if handle is None:
        return ""
    return str(
        handle.evaluate(
            "el => `${el.querySelectorAll('[data-id]').length}:${el.scrollHeight}`"
        )
    )


def scroll_one_pass(
    page: Page,
    *,
    poll_ms: int = 250,
    max_wait_ms: int = DEFAULT_LOAD_WAIT_MS,
) -> bool:
    """Scroll to the top of the panel and wait until older messages arrive.

    Waiting on a fixed timeout was the first version of this and it ended the
    harvest early: WhatsApp Web needed longer than the 400 ms allowed to hydrate
    the next batch, three passes in a row saw nothing new, and the run declared
    the start of the chat reached after 1.2 seconds.

    Args:
        page: Page with an open conversation.
        poll_ms: Gap between checks for newly arrived rows.
        max_wait_ms: How long to keep waiting before calling it a real stall.

    Returns:
        bool: True when the panel changed, i.e. older messages loaded. False
            means nothing arrived within ``max_wait_ms`` — the caller treats
            that as evidence, not as a completed history.
    """
    panel_sel = _first_selector(page, MESSAGE_PANEL_SELECTORS)
    if panel_sel is None:
        logger.warning("No message panel for scrolling")
        return False
    handle = page.query_selector(panel_sel)
    if handle is None:
        return False

    before = panel_signature(page)
    handle.evaluate("el => { el.scrollTop = 0; }")
    clicked = _click_load_earlier(page)

    waited = 0
    while waited < max_wait_ms:
        page.wait_for_timeout(poll_ms)
        waited += poll_ms
        if panel_signature(page) != before:
            return True
        if not clicked:
            # The control is frequently rendered only once the scroll settles,
            # so one attempt before the wait is not enough.
            clicked = _click_load_earlier(page)
    logger.info(
        "Panel unchanged after %s ms at the top (load-earlier control %s)",
        max_wait_ms,
        "clicked" if clicked else "not found",
    )
    return False


def is_load_earlier_label(text: str) -> bool:
    """Whether a control's text marks it as the 'older messages' loader.

    Args:
        text: The control's visible text.

    Returns:
        bool: True when the text matches a known label in ES or EN.
    """
    return bool(LOAD_EARLIER_PATTERN.search(text or ""))


def _click_load_earlier(page: Page) -> bool:
    """Click the 'load older messages' control when the panel renders one.

    Identified by text across any clickable element rather than by tag: the
    previous version matched `button` only and never fired, which left the
    operator clicking it by hand once per batch.

    Args:
        page: Page with an open conversation.

    Returns:
        bool: True when a control was clicked.
    """
    from playwright.sync_api import Error as PlaywrightError

    try:
        node = page.query_selector(LOAD_EARLIER_TESTID)
        if node is not None:
            node.click(timeout=2_000)
            logger.info("Clicked load-earlier control (testid)")
            return True
    except PlaywrightError as exc:
        logger.debug("Load-earlier testid click miss: %s", exc)

    for node in page.query_selector_all(LOAD_EARLIER_CANDIDATES):
        try:
            label = (node.inner_text() or "").strip()
            if not is_load_earlier_label(label):
                continue
            node.click(timeout=2_000)
            logger.info("Clicked load-earlier control: %r", label[:60])
            return True
        except PlaywrightError as exc:
            logger.debug("Load-earlier click miss: %s", exc)
    return False


def at_chat_start(page: Page) -> bool:
    """Whether a start-of-conversation marker is present in the panel.

    Args:
        page: Page with an open conversation.

    Returns:
        bool: True when a marker is found. False is not proof of more history —
            WA Web omits the marker in many conversations.
    """
    return _first_selector(page, CHAT_START_SELECTORS) is not None


def collect_visible_rows(page: Page) -> list[HarvestedRow]:
    """Read the text rows currently in the DOM, each with a stable identity.

    Args:
        page: Page with an open conversation.

    Returns:
        list[HarvestedRow]: Rows in document order (oldest first); empty if
            selectors miss.
    """
    row_sel = _first_selector(page, MESSAGE_ROW_SELECTORS)
    if row_sel is None:
        logger.warning("No message rows found")
        return []

    rows: list[HarvestedRow] = []
    for row in page.query_selector_all(row_sel):
        body = _row_body(row)
        if not body:
            continue
        sender = _row_sender(row)
        timestamp = _row_timestamp(row)
        rows.append(
            {
                "message_id": _row_id(row) or fallback_message_id(
                    sender, timestamp, body
                ),
                "sender": sender,
                "timestamp": timestamp,
                "body": body,
            }
        )
    return rows


def _row_id(row: object) -> str:
    """WhatsApp's own message id, read from the row or its nearest ancestor."""
    own = row.get_attribute("data-id")  # type: ignore[attr-defined]
    if own:
        return own.strip()
    nearest = row.evaluate(  # type: ignore[attr-defined]
        "el => el.closest('[data-id]')?.getAttribute('data-id') || ''"
    )
    return (nearest or "").strip()


def _row_body(row: object) -> str:
    selectable = row.query_selector(  # type: ignore[attr-defined]
        'span.selectable-text, span[data-testid="msg-text"], div.copyable-text'
    )
    if selectable is None:
        return ""
    return (selectable.inner_text() or "").strip()


def _row_sender(row: object) -> str:
    """Which side of the conversation a row belongs to — never who wrote it.

    Returns a role, not a name. The operator's data-protection constraint is
    that no personal identifier reaches the exported file, and an agent learning
    from the conversation needs the turns separated, not the people named.

    The earlier implementation read `data-pre-plain-text` off the row itself,
    where WhatsApp does not put it, and fell through to a `span[dir="auto"]`
    fallback that matched the clock — which is why 214 of 217 messages in the
    first full export carried a time of day as their sender.

    Returns:
        str: ``me``, ``contact``, or ``unknown`` when the row shows neither
            side. ``unknown`` is reported rather than guessed.
    """
    side = row.evaluate(  # type: ignore[attr-defined]
        "el => el.closest('.message-out') ? 'me'"
        " : (el.closest('.message-in') ? 'contact' : '')"
    )
    if side:
        return str(side)
    if row.query_selector(  # type: ignore[attr-defined]
        '[data-testid="msg-dblcheck"], [data-testid="msg-check"]'
    ):
        return "me"
    return "unknown"


def _row_timestamp(row: object) -> str:
    """The message's own timestamp, with the sender name discarded on the spot.

    WhatsApp renders `data-pre-plain-text="[HH:MM, D/M/YYYY] Name: "` on a
    `div.copyable-text` **inside** the row. Only the bracketed part is kept, so
    the name never reaches the caller, let alone the file.

    Returns:
        str: The bracketed timestamp, or ``""`` when none can be read. An empty
            string is returned rather than any text that might be message body.
    """
    node = row.query_selector("[data-pre-plain-text]")  # type: ignore[attr-defined]
    pre = node.get_attribute("data-pre-plain-text") if node else None
    if pre:
        match = re.match(r"\s*\[(.*?)\]", pre)
        if match:
            return match.group(1).strip()

    meta = row.query_selector('[data-testid="msg-meta"] span')  # type: ignore[attr-defined]
    if meta is not None:
        text = (meta.inner_text() or "").strip()
        # Accept only clock-shaped text: the previous fallback matched
        # `div.copyable-text`, whose inner text is the message body.
        if re.match(r"^\d{1,2}:\d{2}", text):
            return text
    return ""
