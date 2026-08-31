"""Enumeration and identity rules for the chat list.

No browser: the pane is a fake whose rendered window is a slice of a list, which
is what the probe measured WhatsApp Web to be — 899 conversations behind a
70-row window.

The failure this file exists to prevent is silent. An enumerator that skips a
conversation, visits one twice, or opens the wrong one raises nothing: the run
completes, the manifest looks healthy, and the corpus is wrong. H-001 was
exactly that, found by the operator rather than by the code.
"""

from __future__ import annotations

import pytest

from whatsapp_chat_extractor.chat_list import (
    CHAT_ROW_SELECTOR,
    TITLE_SELECTORS,
    ChatRef,
    at_pane_bottom,
    find_row,
    open_chat_by_digest,
    row_digests,
    row_title,
    seek_scroll_top,
    sweep_chat_list,
)
from whatsapp_chat_extractor.writers import pseudonymous_chat_id


class FakeNode:
    """A row's title span: the name lives in the `title` attribute."""

    def __init__(self, title: str) -> None:
        self._title = title

    def get_attribute(self, name: str) -> str | None:
        return self._title if name == "title" else None

    def inner_text(self) -> str:
        return ""


class HeaderNode:
    """The open conversation's header, which `read_open_chat_title` reads."""

    def __init__(self, title: str) -> None:
        self._title = title

    def inner_text(self) -> str:
        return self._title


class FakeRow:
    """A chat-list row exposing its title under the working selector."""

    def __init__(self, title: str, selector: str = TITLE_SELECTORS[-1]) -> None:
        self._title = title
        self._selector = selector
        self.clicked = False

    def query_selector(self, selector: str) -> FakeNode | None:
        if selector != self._selector or not self._title:
            return None
        return FakeNode(self._title)

    def click(self, timeout: int = 0) -> None:
        self.clicked = True


class FakePane:
    """A virtualized chat list: a window of ``window`` rows over ``titles``.

    Models what the probe measured rather than a convenient abstraction — the
    DOM holds a slice, and which slice depends on where the pane is scrolled.
    """

    def __init__(
        self, titles: list[str], *, window: int = 4, row_height: int = 10,
        client_height: int = 40,
    ) -> None:
        self.titles = titles
        self.window = window
        self.row_height = row_height
        self.client_height = client_height
        self.scroll_top = 0
        self.opened: str | None = None
        self.waits = 0

    # --- Page surface used by chat_list ---------------------------------

    def query_selector_all(self, selector: str) -> list[FakeRow]:
        assert selector == CHAT_ROW_SELECTOR
        start = min(self.scroll_top // self.row_height, max(0, len(self.titles) - 1))
        rows = [FakeRow(title) for title in self.titles[start:start + self.window]]
        for row in rows:
            row.click = self._click_for(row)  # type: ignore[method-assign]
        return rows

    def _click_for(self, row: FakeRow):
        def click(timeout: int = 0) -> None:
            self.opened = row._title
        return click

    def query_selector(self, selector: str) -> HeaderNode | None:
        """The conversation header, once something has been opened."""
        return None if self.opened is None else HeaderNode(self.opened)

    def evaluate(self, js: str, arg: object = None) -> object:
        if isinstance(arg, list):
            self.scroll_top = max(0, min(int(arg[1]), self._max_scroll()))
            return None
        return {
            "scroll_top": self.scroll_top,
            "scroll_height": len(self.titles) * self.row_height,
            "client_height": self.client_height,
        }

    def wait_for_timeout(self, ms: int) -> None:
        self.waits += 1

    def _max_scroll(self) -> int:
        return max(0, len(self.titles) * self.row_height - self.client_height)


def titles(count: int) -> list[str]:
    return [f"Chat {index:03d}" for index in range(count)]


# --- row reading ----------------------------------------------------------


def test_a_row_yields_its_title() -> None:
    assert row_title(FakeRow("Ana")) == "Ana"


def test_a_row_with_no_title_yields_empty() -> None:
    assert row_title(FakeRow("")) == ""


def test_rows_become_digests_and_untitled_rows_are_counted() -> None:
    pane = FakePane(["Ana", "", "Beto"], window=3)
    digests, untitled = row_digests(pane)
    assert digests == [pseudonymous_chat_id("Ana"), pseudonymous_chat_id("Beto")]
    assert untitled == 1


def test_no_name_survives_into_a_digest() -> None:
    pane = FakePane(["Ana Real Name"], window=1)
    digests, _ = row_digests(pane)
    assert "Ana" not in "".join(digests)


# --- sweeping a virtualized list -----------------------------------------


def test_a_sweep_finds_every_conversation_behind_the_window() -> None:
    """The finding that shaped this module: 899 chats, a 70-row window."""
    pane = FakePane(titles(40), window=4)
    refs = sweep_chat_list(pane, settle_ms=0)
    assert len(refs) == 40
    assert [ref["chat_id"] for ref in refs] == [
        pseudonymous_chat_id(title) for title in titles(40)
    ]


def test_a_sweep_visits_each_conversation_exactly_once() -> None:
    """Overlapping windows must not enumerate a conversation twice."""
    pane = FakePane(titles(40), window=8)
    refs = sweep_chat_list(pane, settle_ms=0)
    ids = [ref["chat_id"] for ref in refs]
    assert len(ids) == len(set(ids))


def test_indexes_are_list_order_and_contiguous() -> None:
    pane = FakePane(titles(25), window=4)
    refs = sweep_chat_list(pane, settle_ms=0)
    assert [ref["index"] for ref in refs] == list(range(25))


def test_a_sweep_does_not_stop_inside_the_render_buffer() -> None:
    """Probe run 1's defect, pinned at the module that inherited its lesson.

    A window wider than the scroll step means several passes in a row can add
    nothing while conversations remain below. Stopping there would enumerate a
    fraction of the list and report success.
    """
    pane = FakePane(titles(60), window=30, row_height=10, client_height=20)
    refs = sweep_chat_list(pane, settle_ms=0)
    assert len(refs) == 60


def test_a_short_list_needing_no_scroll_still_enumerates() -> None:
    pane = FakePane(titles(3), window=10, row_height=10, client_height=100)
    assert len(sweep_chat_list(pane, settle_ms=0)) == 3


def test_the_pass_cap_bounds_a_sweep_that_never_settles() -> None:
    pane = FakePane(titles(500), window=2)
    refs = sweep_chat_list(pane, max_passes=5, settle_ms=0)
    assert len(refs) < 500


# --- pane geometry --------------------------------------------------------


def test_a_pane_with_distance_left_is_not_at_the_bottom() -> None:
    assert at_pane_bottom(
        {"scroll_top": 2238, "scroll_height": 68407, "client_height": 746}
    ) is False


def test_an_unreadable_pane_is_never_at_the_bottom() -> None:
    assert at_pane_bottom(
        {"scroll_top": 0, "scroll_height": 0, "client_height": 0}
    ) is False


def test_the_seek_centres_the_target_in_the_viewport() -> None:
    metrics = {"scroll_top": 0, "scroll_height": 8990, "client_height": 746}
    # 899 chats over 8990px is 10px per row; chat 500 sits at 5000.
    assert seek_scroll_top(500, total=899, metrics=metrics) == 5000 - 373


def test_the_seek_never_returns_a_negative_position() -> None:
    metrics = {"scroll_top": 0, "scroll_height": 8990, "client_height": 746}
    assert seek_scroll_top(0, total=899, metrics=metrics) == 0


def test_an_unusable_geometry_seeks_the_head_rather_than_guessing() -> None:
    metrics = {"scroll_top": 0, "scroll_height": 0, "client_height": 0}
    assert seek_scroll_top(500, total=899, metrics=metrics) == 0
    assert seek_scroll_top(500, total=0, metrics=metrics) == 0


# --- identity: opening the chat that was asked for -------------------------


def test_find_row_matches_on_the_digest() -> None:
    rows = [FakeRow("Ana"), FakeRow("Beto")]
    assert find_row(rows, pseudonymous_chat_id("Beto")) is rows[1]


def test_find_row_never_matches_a_titleless_row() -> None:
    """A row with no identity cannot be the row that was asked for."""
    assert find_row([FakeRow("")], pseudonymous_chat_id("")) is None


def test_opening_returns_the_verified_title() -> None:
    pane = FakePane(titles(40), window=4)
    ref: ChatRef = {"chat_id": pseudonymous_chat_id("Chat 021"), "index": 21}
    assert open_chat_by_digest(pane, ref, total=40, settle_ms=0) == "Chat 021"
    assert pane.opened == "Chat 021"


def test_opening_finds_a_conversation_whose_position_shifted() -> None:
    """Position is a hint. The digest is what decides."""
    pane = FakePane(titles(40), window=6)
    ref: ChatRef = {"chat_id": pseudonymous_chat_id("Chat 020"), "index": 18}
    assert open_chat_by_digest(pane, ref, total=40, settle_ms=0) == "Chat 020"


def test_a_conversation_that_is_gone_raises_rather_than_opening_a_neighbour() -> None:
    """The H-001 failure mode: a click that opens *something* is not success."""
    pane = FakePane(titles(40), window=4)
    ref: ChatRef = {"chat_id": pseudonymous_chat_id("Chat 999"), "index": 5}
    with pytest.raises(LookupError):
        open_chat_by_digest(pane, ref, total=40, settle_ms=0)
    assert pane.opened is None


def test_opening_the_wrong_conversation_fails_closed() -> None:
    """The row matched, but the page put a different conversation on screen.

    This is H-001's defect exactly, and the refusal is what the hotfix added:
    the export never sees a conversation whose title does not hash back to the
    identity that was asked for.
    """
    pane = FakePane(titles(40), window=4)
    pane._click_for = lambda row: (lambda timeout=0: setattr(pane, "opened", "Chat 777"))
    ref: ChatRef = {"chat_id": pseudonymous_chat_id("Chat 010"), "index": 10}
    with pytest.raises(RuntimeError, match="wrong conversation"):
        open_chat_by_digest(pane, ref, total=40, settle_ms=0)


def test_an_unreadable_title_fails_closed() -> None:
    """An unattributable conversation is not exportable (same rule as H-001)."""
    pane = FakePane(titles(40), window=4)
    pane._click_for = lambda row: (lambda timeout=0: None)
    ref: ChatRef = {"chat_id": pseudonymous_chat_id("Chat 010"), "index": 10}
    with pytest.raises(RuntimeError, match="no readable title"):
        open_chat_by_digest(pane, ref, total=40, settle_ms=0)
