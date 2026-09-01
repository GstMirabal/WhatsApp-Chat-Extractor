"""Pure logic of the chat-list probe, with no browser involved.

The probe's job is to answer two questions the Sprint 007 enumerator depends on,
and its verdict functions are what turn raw counts into those answers. A wrong
verdict here would not crash — it would quietly send the enumerator down the
wrong design, which is the failure mode `KI-004-A` was written against.

Only the pure parts are covered: scrolling a real `#pane-side` needs WhatsApp
Web and the operator, and the notes record that run separately.
"""

from __future__ import annotations

import sys
from pathlib import Path

from whatsapp_chat_extractor.writers import pseudonymous_chat_id

# The probe is an operator-run script, not part of the installed package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from probe_chat_list import (
    TITLE_SELECTORS,
    at_pane_bottom,
    compare_readings,
    read_list_digests,
    virtualization_verdict,
)


class FakeNode:
    """A node that answers `title` or `inner_text`, like a title span."""

    def __init__(self, title: str = "", text: str = "") -> None:
        self._title = title
        self._text = text

    def get_attribute(self, name: str) -> str | None:
        return self._title if name == "title" else None

    def inner_text(self) -> str:
        return self._text


class FakeRow:
    """A chat-list row that exposes a title under one named selector."""

    def __init__(self, matches: dict[str, FakeNode]) -> None:
        self._matches = matches

    def query_selector(self, selector: str) -> FakeNode | None:
        return self._matches.get(selector)


class FakePage:
    """A page whose chat list is a fixed set of rows."""

    def __init__(self, rows: list[FakeRow]) -> None:
        self._rows = rows

    def query_selector_all(self, selector: str) -> list[FakeRow]:
        return list(self._rows)


def row_titled(title: str, selector: str = TITLE_SELECTORS[0]) -> FakeRow:
    return FakeRow({selector: FakeNode(title=title)})


# --- at_pane_bottom -------------------------------------------------------


def test_a_pane_with_pixels_left_is_not_at_the_bottom() -> None:
    """Run 1's actual geometry: 3.3% of the pane traversed."""
    assert at_pane_bottom(
        {"scroll_top": 2238, "scroll_height": 68407, "client_height": 746}
    ) is False


def test_a_fully_scrolled_pane_is_at_the_bottom() -> None:
    assert at_pane_bottom(
        {"scroll_top": 67661, "scroll_height": 68407, "client_height": 746}
    ) is True


def test_a_pane_shorter_than_its_viewport_is_at_the_bottom() -> None:
    """Nothing to scroll is a legitimate bottom, not a failure to reach one."""
    assert at_pane_bottom(
        {"scroll_top": 0, "scroll_height": 500, "client_height": 746}
    ) is True


def test_an_unreadable_pane_is_never_at_the_bottom() -> None:
    """`_pane_metrics` returns zeroes when the selector misses.

    Calling that "finished" would let a wrong selector produce a confident
    verdict about a list it never found.
    """
    assert at_pane_bottom(
        {"scroll_top": 0, "scroll_height": 0, "client_height": 0}
    ) is False


# --- virtualization_verdict ----------------------------------------------


def test_more_distinct_than_ever_rendered_means_virtualized() -> None:
    """The finding that would force the enumerator to scroll the pane itself."""
    assert virtualization_verdict(
        59, 140, passes_used=8, reached_bottom=True
    ) == "virtualized"


def test_virtualization_is_proven_wherever_it_is_seen() -> None:
    """Seeing more chats than ever rendered proves it, bottom reached or not."""
    assert virtualization_verdict(
        59, 140, passes_used=8, reached_bottom=False
    ) == "virtualized"


def test_everything_rendered_at_once_means_not_virtualized() -> None:
    assert virtualization_verdict(
        59, 59, passes_used=8, reached_bottom=True
    ) == "not-virtualized"


def test_a_sweep_that_never_reached_the_bottom_decides_nothing() -> None:
    """The run-1 defect, pinned.

    Four passes, no new digests after the first, and a verdict of
    `not-virtualized` drawn from 2238 of 68407 pixels. An unchanged count over a
    stretch that was never finished says nothing about the whole list — it is
    equally what a sweep still inside the render buffer looks like. This is
    `history.py:38-44` one panel over, and the assertion below is the fix.
    """
    assert virtualization_verdict(
        70, 70, passes_used=4, reached_bottom=False
    ) == "inconclusive"


def test_a_single_pass_decides_nothing() -> None:
    """One pass cannot distinguish a short list from an unscrolled one."""
    assert virtualization_verdict(
        59, 59, passes_used=1, reached_bottom=True
    ) == "inconclusive"


# --- read_list_digests ----------------------------------------------------


def test_rows_become_digests_in_list_order() -> None:
    page = FakePage([row_titled("Ana"), row_titled("Beto"), row_titled("Caro")])
    digests, untitled = read_list_digests(page)
    assert digests == [
        pseudonymous_chat_id("Ana"),
        pseudonymous_chat_id("Beto"),
        pseudonymous_chat_id("Caro"),
    ]
    assert untitled == 0


def test_no_title_reaches_the_digest_list() -> None:
    """ADR-0001: a name is hashed on the way past and never kept."""
    page = FakePage([row_titled("Ana Real Name")])
    digests, _ = read_list_digests(page)
    assert "Ana" not in "".join(digests)
    assert all(digest.startswith("chat_") for digest in digests)


def test_an_unreadable_row_is_counted_not_guessed() -> None:
    """A row with no title gets no digest — a fabricated one would be worse."""
    page = FakePage([row_titled("Ana"), FakeRow({}), row_titled("Beto")])
    digests, untitled = read_list_digests(page)
    assert len(digests) == 2
    assert untitled == 1


def test_a_later_title_selector_is_used_when_the_first_misses() -> None:
    """Which selector works is measured per row, not fixed at the first."""
    page = FakePage([row_titled("Ana", selector=TITLE_SELECTORS[-1])])
    digests, untitled = read_list_digests(page)
    assert digests == [pseudonymous_chat_id("Ana")]
    assert untitled == 0


def test_two_chats_sharing_a_title_collide_into_one_digest() -> None:
    """A measured limit of digest identity, pinned so it is not a surprise.

    `pseudonymous_chat_id` hashes the title alone, so two conversations named
    the same are one identity. If the probe reports duplicates, the enumerator
    cannot use the digest as its key — which is exactly what the abort criterion
    of this sprint asks about.
    """
    page = FakePage([row_titled("Soporte"), row_titled("Soporte")])
    digests, _ = read_list_digests(page)
    assert len(digests) == 2
    assert len(set(digests)) == 1


# --- compare_readings -----------------------------------------------------


def test_identical_readings_are_stable() -> None:
    reading = ["chat_a", "chat_b", "chat_c"]
    assert compare_readings(reading, list(reading))["verdict"] == "stable"


def test_a_reordered_list_is_unstable() -> None:
    """One arriving message moves a chat to the top and shifts everything."""
    result = compare_readings(
        ["chat_a", "chat_b", "chat_c"], ["chat_c", "chat_a", "chat_b"]
    )
    assert result["verdict"] == "unstable"
    assert result["positions_that_changed"] == 3


def test_only_the_overlap_is_compared() -> None:
    """Two readings of a virtualized pane rarely render the same row count."""
    result = compare_readings(["chat_a", "chat_b"], ["chat_a", "chat_b", "chat_c"])
    assert result["positions_compared"] == 2
    assert result["verdict"] == "stable"


def test_two_empty_readings_decide_nothing() -> None:
    assert compare_readings([], [])["verdict"] == "inconclusive"


def test_a_repeated_digest_within_one_reading_is_counted() -> None:
    """A title collision: the one thing that would stop the digest being a key."""
    result = compare_readings(["chat_a", "chat_a", "chat_b"], ["chat_a", "chat_a", "chat_b"])
    assert result["duplicate_digests_in_reading_1"] == 1


def test_both_readings_declare_their_anchor() -> None:
    """Run 2 compared the pane foot against its head and called it reordering.

    68 of 68 positions "changed" because the readings were different windows of
    a 899-chat virtualized list, not because anything moved. Run 1 reported the
    opposite from the same code for the mirror-image reason. The anchor is now
    part of the record so a reader can see which question was answered.
    """
    result = compare_readings(["chat_a"], ["chat_a"])
    assert "scroll_top 0" in result["anchor"]
