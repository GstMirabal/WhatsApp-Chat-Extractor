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
# Deliberately narrow. The first version added `#main a` and `#main [tabindex]`,
# which are every link and nearly every focusable node *inside the conversation*,
# and paired them with a `haz clic aquí` alternative — a phrase that occurs in
# ordinary messages. The harvester clicked links inside the chat.
LOAD_EARLIER_CANDIDATES = (
    '#main button, #main div[role="button"], #main span[role="button"]'
)
# Every alternative requires the noun "mensajes"/"messages": a verb phrase alone
# ("haz clic aquí", "click here") is message content as often as it is a control.
LOAD_EARLIER_PATTERN = re.compile(
    r"mensajes\s+(m[áa]s\s+)?(antiguos|anteriores|viejos)"
    r"|(cargar|ver|obtener|mostrar)\s+\S{0,30}?\s?mensajes"
    r"|(older|earlier|previous)\s+messages"
    r"|(load|get|show)\s+\S{0,30}?\s?messages",
    re.IGNORECASE,
)
# A control's label is short. A message that happens to mention older messages is
# usually not, and this is the cheapest discriminator between the two.
LOAD_EARLIER_MAX_LABEL = 120
# Best-effort start-of-conversation markers. WA Web does not always render one,
# so `history.decide_stop` uses these only to report a *proven* start.
# Direction signals, in the order the live DOM proved reliable (Sprint 004
# probe). WhatsApp draws the bubble "tail" only on the first message of a run,
# so consecutive messages from one speaker carry no tail and need the label.
TAIL_OUT_SELECTOR = '[data-testid="tail-out"], [data-icon="tail-out"]'
TAIL_IN_SELECTOR = '[data-testid="tail-in"], [data-icon="tail-in"]'
SPEAKER_LABEL_PATTERN = re.compile(r"^(?P<name>.+):$")
PRE_PLAIN_NAME_PATTERN = re.compile(r"\]\s*(?P<name>.*?):\s*$")
CHAT_START_SELECTORS = (
    '#main [data-icon="lock-refreshed"]',
    '#main [data-testid="msg-system"] [data-icon="lock"]',
    '#main div.message-system [data-icon="lock"]',
)

# Media signals, each observed on a live row by the Sprint 005 W2 probe
# (2026-08-30, 36-row window: 4 voice notes, 1 photo). Nothing here is inferred
# from WhatsApp's structure — `KI-004-A`: three successive theories about
# message direction were reasoned rather than measured, and all three were wrong.
VOICE_SELECTOR = '[data-testid="ptt-status"], [data-icon="ptt-status"]'
IMAGE_SELECTOR = '[data-testid="image-thumb"]'
# An emoji is drawn as `<img alt="…">`, and the node containing it is a
# `div[data-testid="selectable-text"]` — never the `span.selectable-text` that
# `_row_body` matches. A message of only emoji therefore read as bodiless and
# was dropped. The probe measured two such rows, carrying one and two emoji.
EMOJI_IMG_SELECTOR = 'img[data-testid="selectable-text"][alt]'


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
        bool: True when the text matches a known label in ES or EN and is short
            enough to be a control rather than a message that mentions one.
    """
    label = (text or "").strip()
    if not label or len(label) > LOAD_EARLIER_MAX_LABEL:
        return False
    return bool(LOAD_EARLIER_PATTERN.search(label))


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
            if _inside_a_message(node):
                continue
            label = (node.inner_text() or "").strip()
            if not is_load_earlier_label(label):
                continue
            node.click(timeout=2_000)
            logger.info("Clicked load-earlier control: %r", label[:60])
            return True
        except PlaywrightError as exc:
            logger.debug("Load-earlier click miss: %s", exc)
    return False


def _inside_a_message(node: object) -> bool:
    """Whether a node sits inside a message bubble rather than the panel chrome.

    The loader is chrome: it is never inside a message. Text matching alone is
    not enough of a guard, because a message can quote a control's wording, and
    clicking inside a bubble opens links and context menus in the operator's
    live session.
    """
    return bool(
        node.evaluate(  # type: ignore[attr-defined]
            "el => !!el.closest('[data-id], .message-in, .message-out')"
        )
    )


def at_chat_start(page: Page) -> bool:
    """Whether a start-of-conversation marker is present in the panel.

    Args:
        page: Page with an open conversation.

    Returns:
        bool: True when a marker is found. False is not proof of more history —
            WA Web omits the marker in many conversations.
    """
    return _first_selector(page, CHAT_START_SELECTORS) is not None


def collect_visible_rows(page: Page, *, chat_title: str = "") -> list[HarvestedRow]:
    """Read the message rows currently in the DOM, each with a stable identity.

    Every row is emitted, including one with no text. Skipping the bodiless ones
    is what ADR-0003 corrects: a photo or a voice note left no trace at all, so
    the exported conversation showed question → next question and taught an
    adjacency that never happened.

    Args:
        page: Page with an open conversation.
        chat_title: Passed through for direction detection only; never stored.

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
        body = _row_body(row) or _row_emoji_body(row)
        kind = _row_kind(row, body)
        # Read the id once and hand it on: it is a DOM round trip per row, and
        # the direction is derived from it rather than from a second query.
        message_id = _row_id(row)
        sender = _row_sender(row, message_id, chat_title)
        timestamp = _row_timestamp(row)
        rows.append(
            {
                "message_id": message_id or fallback_message_id(
                    sender, timestamp, body, kind
                ),
                "sender": sender,
                "timestamp": timestamp,
                "body": body,
                "kind": kind,
            }
        )
    return rows


def _row_id(row: object) -> str:
    """WhatsApp's own message id, read from the row or its nearest ancestor.

    Falls back to the `conv-msg-<HEX>` test id on the wrapping element, which
    the Sprint 005 W2 probe found on every row (7 rows, 7 distinct values) and
    which is derived from the same message identity, so it is stable across
    scroll passes. Without it a captionless media row reaches
    `fallback_message_id`, whose key cannot separate two voice notes sent by one
    speaker inside the same minute.
    """
    own = row.get_attribute("data-id")  # type: ignore[attr-defined]
    if own:
        return own.strip()
    nearest = row.evaluate(  # type: ignore[attr-defined]
        "el => el.closest('[data-id]')?.getAttribute('data-id') || ''"
    )
    if nearest and nearest.strip():
        return nearest.strip()
    wrapper = row.evaluate(  # type: ignore[attr-defined]
        "el => el.closest('[data-testid^=\"conv-msg-\"]')"
        "?.getAttribute('data-testid') || ''"
    )
    return (wrapper or "").strip()


def _row_body(row: object) -> str:
    selectable = row.query_selector(  # type: ignore[attr-defined]
        'span.selectable-text, span[data-testid="msg-text"], div.copyable-text'
    )
    if selectable is None:
        return ""
    return (selectable.inner_text() or "").strip()


def _row_emoji_body(row: object) -> str:
    """Text of a message whose characters are drawn as emoji images.

    Args:
        row: Element handle for one message row.

    Returns:
        str: The emoji in document order, or `""` when the row carries none.
    """
    images = row.query_selector_all(EMOJI_IMG_SELECTOR)  # type: ignore[attr-defined]
    return "".join((image.get_attribute("alt") or "") for image in images)


def _row_kind(row: object, body: str) -> str:
    """Which medium a row carries, so a media message is recorded, not dropped.

    Media is tested before text because a photo with a caption is a photo: it
    carries both a thumbnail and a body, and the caption belongs in `body` while
    `kind` names what it captions.

    Only signals the W2 probe observed on live rows are tested. A bodiless row
    matching none of them is `unknown` rather than a guess (`KI-004-A`), which
    still preserves the turn structure that dropping it destroyed.

    Args:
        row: Element handle for one message row.
        body: Text already extracted for the row, emoji included.

    Returns:
        str: One of `voice`, `image`, `text`, `unknown`.
    """
    if row.query_selector(VOICE_SELECTOR) is not None:  # type: ignore[attr-defined]
        return "voice"
    if row.query_selector(IMAGE_SELECTOR) is not None:  # type: ignore[attr-defined]
        return "image"
    return "text" if body else "unknown"


def _row_sender(row: object, message_id: str = "", chat_title: str = "") -> str:
    """Which side of the conversation a row belongs to — never who wrote it.

    Returns a role, not a name. The operator's data-protection constraint is
    that no personal identifier reaches the exported file; the speaker label is
    read here, compared against the chat title, and discarded.

    Three signals in order, each covering what the previous one misses — every
    earlier single-signal attempt failed against the live DOM, most recently
    producing a 513-message export with every sender `unknown`:

    1. The bubble tail (`tail-in`/`tail-out`), definitive when present.
    2. An `aria-label` of the form `Name:`, which media rows carry when the
       tail is absent.
    3. The name in `data-pre-plain-text`, which covers consecutive text
       messages in a run, where WhatsApp draws neither tail nor label.

    Args:
        row: The message container element.
        message_id: Unused for direction; kept so callers can pass the id they
            already read without a second DOM round trip.
        chat_title: The contact's title, used only as the comparison target.

    Returns:
        str: ``me``, ``contact``, or ``unknown`` when no signal resolves.
    """
    if row.query_selector(TAIL_OUT_SELECTOR):  # type: ignore[attr-defined]
        return "me"
    if row.query_selector(TAIL_IN_SELECTOR):  # type: ignore[attr-defined]
        return "contact"

    for label in (_row_speaker_label(row), _row_pre_plain_name(row)):
        role = sender_from_speaker_label(label, chat_title)
        if role:
            return role

    if row.query_selector(  # type: ignore[attr-defined]
        '[data-testid="msg-dblcheck"], [data-testid="msg-check"]'
    ):
        return "me"
    return "unknown"


def sender_from_speaker_label(label: str, chat_title: str) -> str:
    """Turn a speaker label into a role by comparing it with the chat title.

    The label itself is never returned. In a one-to-one chat the title is the
    contact, so a label equal to it is the contact and any other non-empty
    label — `Tú:`, `You:`, an own display name — is the operator.

    Args:
        label: Speaker label with any trailing colon already stripped.
        chat_title: The open chat's title.

    Returns:
        str: ``contact``, ``me``, or ``""`` when the label is empty or no title
            is available to compare against.
    """
    name = (label or "").strip()
    title = (chat_title or "").strip()
    if not name or not title:
        return ""
    return "contact" if name.casefold() == title.casefold() else "me"


def _row_speaker_label(row: object) -> str:
    """First `aria-label` shaped like `Name:`, or empty."""
    for node in row.query_selector_all("[aria-label]"):  # type: ignore[attr-defined]
        match = SPEAKER_LABEL_PATTERN.match((node.get_attribute("aria-label") or "").strip())
        if match:
            return match.group("name").strip()
    return ""


def _row_pre_plain_name(row: object) -> str:
    """Sender name held in `data-pre-plain-text`, or empty."""
    node = row.query_selector("[data-pre-plain-text]")  # type: ignore[attr-defined]
    raw = node.get_attribute("data-pre-plain-text") if node else None
    match = PRE_PLAIN_NAME_PATTERN.search(raw or "")
    return match.group("name").strip() if match else ""


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
