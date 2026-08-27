"""Regression: chat search must resolve ES/EN placeholders before CSS."""

from __future__ import annotations

from whatsapp_chat_extractor.export_one import (
    CHAT_SEARCH_SELECTORS,
    SEARCH_PLACEHOLDERS,
    _locate_search_box,
)


class _FakeLocator:
    def __init__(self, count: int) -> None:
        self._count = count
        self.first = self

    def count(self) -> int:
        return self._count


class _FakePage:
    """Minimal Page double for locator resolution (no Playwright)."""

    def __init__(self, *, placeholder_hits: dict[str, int], role_count: int = 0) -> None:
        self._placeholder_hits = placeholder_hits
        self._role_count = role_count
        self.query_calls: list[str] = []

    def get_by_placeholder(self, text: str) -> _FakeLocator:
        return _FakeLocator(self._placeholder_hits.get(text, 0))

    def get_by_role(self, role: str, name: object = None) -> _FakeLocator:
        assert role == "textbox"
        return _FakeLocator(self._role_count)

    def query_selector(self, selector: str) -> object | None:
        self.query_calls.append(selector)
        return None

    def locator(self, selector: str) -> _FakeLocator:
        return _FakeLocator(0)


def test_spanish_placeholder_is_preferred() -> None:
    page = _FakePage(
        placeholder_hits={"Buscar un chat o iniciar uno nuevo": 1},
    )
    box = _locate_search_box(page)  # type: ignore[arg-type]
    assert box is not None


def test_search_fallbacks_include_es_en_and_css() -> None:
    assert any("Buscar" in p for p in SEARCH_PLACEHOLDERS)
    assert any("Search" in p for p in SEARCH_PLACEHOLDERS)
    assert any("contenteditable" in s for s in CHAT_SEARCH_SELECTORS)


def test_missing_search_returns_none() -> None:
    page = _FakePage(placeholder_hits={}, role_count=0)
    assert _locate_search_box(page) is None  # type: ignore[arg-type]
