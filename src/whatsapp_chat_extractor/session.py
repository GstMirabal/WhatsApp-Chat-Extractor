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
) -> BrowserContext:
    """Launch Chromium with a persistent profile for WhatsApp Web.

    Args:
        playwright: A Playwright instance from ``sync_playwright()``.
        profile_dir: Persistent user-data directory under gitignored ``data/``.
        headless: Must stay False for QR login on the operator Mac.

    Returns:
        A Playwright ``BrowserContext``.
    """
    from playwright.sync_api import Playwright

    if not isinstance(playwright, Playwright):
        raise TypeError("playwright must be a Playwright instance")

    user_data = str(ensure_profile_dir(profile_dir))
    logger.info("Launching Chromium profile at %s", user_data)
    return playwright.chromium.launch_persistent_context(
        user_data_dir=user_data,
        headless=headless,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )


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
