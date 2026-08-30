"""Regression (hotfix H-001): opening a chat must be verified, not assumed.

The defect these tests pin is that every post-condition in `open_chat_by_query`
was satisfiable by the page state that already held before the search: a wait on
an open panel, a click on the always-present chat list, and a title that was read
but never compared. A search that opened nothing returned success.
"""

from __future__ import annotations

import pytest

from whatsapp_chat_extractor import export_one
from whatsapp_chat_extractor.export_one import open_chat_by_query


class _FakeNode:
    def __init__(self, text: str) -> None:
        self._text = text

    def inner_text(self) -> str:
        return self._text


class _FakePage:
    """Page double whose conversation panel is already open."""

    def __init__(self, title: str) -> None:
        self.title_text = title
        self.waited: list[str] = []

    def query_selector(self, selector: str) -> object | None:
        return _FakeNode(self.title_text) if self.title_text else None

    def wait_for_selector(self, selector: str, timeout: int | None = None) -> object:
        # The heart of the defect: an already-open panel satisfies this instantly.
        self.waited.append(selector)
        return object()


@pytest.fixture(autouse=True)
def _silent_search(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate a search that types but opens nothing — the reported failure."""
    monkeypatch.setattr(export_one, "_type_query", lambda page, query: None)
    monkeypatch.setattr(
        export_one, "_open_first_result", lambda page, timeout_ms: None
    )


def test_open_panel_that_never_changes_must_raise() -> None:
    """The exact silent failure: wrong chat on screen, search does nothing."""
    page = _FakePage("Alice Alvarez")
    with pytest.raises(RuntimeError, match="wrong-chat"):
        open_chat_by_query(page, "Bob Boronat")  # type: ignore[arg-type]


def test_unreadable_title_must_raise_not_fall_back_to_query() -> None:
    """`read_open_chat_title(page) or query` used to fabricate agreement."""
    page = _FakePage("")
    with pytest.raises(RuntimeError, match="unverifiable"):
        open_chat_by_query(page, "Bob Boronat")  # type: ignore[arg-type]


def test_matching_title_still_returns() -> None:
    """Fail-closed must not break the legitimate case."""
    page = _FakePage("Bob Boronat")
    assert open_chat_by_query(page, "Boronat") == "Bob Boronat"  # type: ignore[arg-type]


def test_error_message_never_leaks_the_title() -> None:
    """Titles are real people's names; they stay out of logs and errors."""
    page = _FakePage("Alice Alvarez")
    with pytest.raises(RuntimeError) as excinfo:
        open_chat_by_query(page, "Bob Boronat")  # type: ignore[arg-type]
    assert "Alice" not in str(excinfo.value)


@pytest.mark.parametrize(
    ("title", "query", "expected"),
    [
        ("Bob Boronat", "boronat", True),
        ("Bob Borónat", "boronat", True),
        ("Bob   Boronat", "bob boronat", True),
        ("Bob Boronat", "Alice", False),
        ("", "Bob", False),
        ("Bob Boronat", "", False),
    ],
)
def test_title_matching_is_accent_and_case_insensitive(
    title: str, query: str, expected: bool
) -> None:
    # Resolved at call time, not import time, so the behavioural tests above
    # still collect against a build that lacks this helper.
    assert export_one._title_matches_query(title, query) is expected
