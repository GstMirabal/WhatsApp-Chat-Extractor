"""Playwright session helpers for WhatsApp Web (persistent profile)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page

logger = logging.getLogger(__name__)

WA_WEB_URL = "https://web.whatsapp.com/"
DEFAULT_PROFILE_DIR = Path("data/browser_profile")

# Pinned so the rendered date format is known by construction rather than
# inferred. WhatsApp writes `data-pre-plain-text="[HH:MM, D/M/YYYY] Name: "` in
# the browser's locale, and `D/M` versus `M/D` cannot be told apart from the
# string alone — `3/9` is a valid date either way. Until now nothing set this,
# so every exported timestamp was rendered under whatever the operator's Mac
# happened to be, unrecorded.
#
# `es-ES` is chosen because it is what the operator already runs: this pins the
# current behaviour rather than changing it. It is also compatible with the
# harvest, which matches its control labels in Spanish and English
# (`export_one.LOAD_EARLIER_PATTERN`).
DEFAULT_LOCALE = "es-ES"

# Read from the page rather than imposed. Forcing a timezone would shift every
# rendered clock away from what the operator sees and away from every export
# written before today; which zone the corpus *should* be in is a decision for
# the operator, taken with `--timezone`, not a default chosen here.
TIMEZONE_QUERY = "() => Intl.DateTimeFormat().resolvedOptions().timeZone"

# Selectors are spike-fragile; record changes in SPIKE_NOTES.md.
QR_SELECTORS = (
    'canvas[aria-label*="Scan"]',
    '[data-testid="qrcode"]',
    "div[data-ref]",
)
READY_SELECTORS = (
    '[data-testid="chat-list"]',
    "#pane-side",
    '[aria-label="Chat list"]',
)


def ensure_profile_dir(profile_dir: Path | None = None) -> Path:
    """Create and return the persistent Chromium profile directory.

    Args:
        profile_dir: Override path; default ``data/browser_profile``.

    Returns:
        Absolute profile path.
    """
    path = (profile_dir or DEFAULT_PROFILE_DIR).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def launch_context(
    playwright: object,
    *,
    profile_dir: Path | None = None,
    headless: bool = False,
    locale: str = DEFAULT_LOCALE,
) -> BrowserContext:
    """Launch Chromium with a persistent profile for WhatsApp Web.

    Args:
        playwright: A Playwright instance from ``sync_playwright()``.
        profile_dir: Persistent user-data directory under gitignored ``data/``.
        headless: Must stay False for QR login on the operator Mac.
        locale: BCP 47 tag the page renders under. Pinned rather than inherited
            so the date format in every timestamp is known — see
            :data:`DEFAULT_LOCALE`.

    Returns:
        A Playwright ``BrowserContext``.
    """
    from playwright.sync_api import Playwright

    if not isinstance(playwright, Playwright):
        raise TypeError("playwright must be a Playwright instance")

    user_data = str(ensure_profile_dir(profile_dir))
    logger.info("Launching Chromium profile at %s under locale %s", user_data, locale)
    return playwright.chromium.launch_persistent_context(
        user_data_dir=user_data,
        headless=headless,
        locale=locale,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )


def resolve_timezone(page: Page) -> str:
    """Which timezone the page rendered its clocks in.

    Read, never imposed. The exported file records this so a reader knows what
    the message timestamps are relative to; without it the corpus carries times
    with no frame, which is the gap `ADR-0007` closes.

    Failure is not fatal and is not silent: a run must not die because a
    diagnostic query did not answer, but an empty value in the export must be
    distinguishable from a real zone, so the empty string is returned and the
    reason logged.

    Args:
        page: Page with WhatsApp Web loaded.

    Returns:
        str: An IANA zone such as ``Europe/Madrid``, or ``""`` when the page
            could not answer.
    """
    try:
        resolved = page.evaluate(TIMEZONE_QUERY)
    except Exception:
        logger.exception("Could not resolve the browser timezone; recording none")
        return ""
    if isinstance(resolved, str) and resolved.strip():
        return resolved.strip()
    logger.warning("Browser returned no timezone (%r); recording none", resolved)
    return ""


def open_whatsapp(context: BrowserContext) -> Page:
    """Navigate to WhatsApp Web on an existing page or a new one.

    Args:
        context: Persistent browser context.

    Returns:
        The page showing WhatsApp Web.
    """
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(WA_WEB_URL, wait_until="domcontentloaded")
    return page


def wait_until_ready(page: Page, *, timeout_ms: int = 300_000) -> str:
    """Block until the chat list is visible (post-QR) or raise.

    Args:
        page: WhatsApp Web page.
        timeout_ms: Max wait for the operator to scan QR (default 5 minutes).

    Returns:
        The CSS selector that matched the ready state.

    Raises:
        TimeoutError: If the chat list does not appear in time.
    """
    deadline_selectors = ", ".join(READY_SELECTORS)
    logger.info(
        "Waiting for WhatsApp Web ready state (scan QR if shown). timeout_ms=%s",
        timeout_ms,
    )
    try:
        page.wait_for_selector(deadline_selectors, timeout=timeout_ms)
    except Exception as exc:
        logger.exception("WhatsApp Web did not reach ready state")
        raise TimeoutError(
            "WhatsApp Web chat list not visible within timeout; "
            "see SPIKE_NOTES.md for selector updates."
        ) from exc

    for selector in READY_SELECTORS:
        if page.query_selector(selector):
            logger.info("Ready via selector %s", selector)
            return selector
    return READY_SELECTORS[0]


def qr_visible(page: Page) -> bool:
    """Return True if a QR canvas/node is currently visible."""
    for selector in QR_SELECTORS:
        node = page.query_selector(selector)
        if node and node.is_visible():
            return True
    return False
