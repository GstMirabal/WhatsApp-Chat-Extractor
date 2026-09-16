"""Regression: `_open_first_result` must click the selector that opens a chat.

`scripts/probe_chat_start.py` runs 1-2 measured `#pane-side div[role="row"]`
as a wrapper that accepts a click and opens nothing (59 matches, none of them
the search result), while `[data-testid="cell-frame-container"]` is the entry
that actually opens the conversation. Both selectors match and neither
raises on `.click()`, so the defect is silent: `_open_first_result` returns
after the first successful click regardless of which node it hit.
"""

from __future__ import annotations

from whatsapp_chat_extractor.export_one import _open_first_result


class _FakeLocator:
    def __init__(self, count: int, on_click) -> None:
        self._count = count
        self._on_click = on_click
        self.first = self

    def count(self) -> int:
        return self._count

    def click(self, timeout: int | None = None) -> None:
        self._on_click()


class _FakePage:
    """Minimal Page double: records which selector's node was clicked."""

    def __init__(self, counts: dict[str, int]) -> None:
        self._counts = counts
        self.clicked: list[str] = []

    def locator(self, selector: str) -> _FakeLocator:
        return _FakeLocator(
            self._counts.get(selector, 0),
            on_click=lambda s=selector: self.clicked.append(s),
        )

    def keyboard_press_unreachable(self, *_a: object, **_k: object) -> None:
        raise AssertionError("Enter fallback should not fire: a selector matched")


def _refuse_fallback(page: _FakePage) -> None:
    page.keyboard = type(
        "K", (), {"press": lambda self, *a, **k: page.keyboard_press_unreachable()}
    )()
    page.wait_for_selector = lambda *a, **k: page.keyboard_press_unreachable()


def test_the_selector_that_opens_a_chat_is_tried_before_the_dead_wrapper() -> None:
    """Measured signature: listitem 0, row 59 (opens nothing), data-testid 1."""
    page = _FakePage(
        {
            '#pane-side div[role="listitem"]': 0,
            '#pane-side div[role="row"]': 59,
            '[data-testid="cell-frame-container"]': 1,
            '#side div[role="listitem"]': 0,
        }
    )
    _refuse_fallback(page)
    _open_first_result(page, timeout_ms=1_000)  # type: ignore[arg-type]
    assert page.clicked == ['[data-testid="cell-frame-container"]']


def test_a_dead_zero_match_selector_is_skipped_without_clicking() -> None:
    page = _FakePage({'[data-testid="cell-frame-container"]': 1})
    _refuse_fallback(page)
    _open_first_result(page, timeout_ms=1_000)  # type: ignore[arg-type]
    assert page.clicked == ['[data-testid="cell-frame-container"]']
