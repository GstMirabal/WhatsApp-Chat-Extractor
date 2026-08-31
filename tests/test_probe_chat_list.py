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


# --- virtualization_verdict ----------------------------------------------


def test_more_distinct_than_ever_rendered_means_virtualized() -> None:
    """The finding that would force the enumerator to scroll the pane itself."""
    assert virtualization_verdict(59, 140, passes_used=8) == "virtualized"


def test_everything_rendered_at_once_means_not_virtualized() -> None:
    assert virtualization_verdict(59, 59, passes_used=8) == "not-virtualized"


def test_a_single_pass_decides_nothing() -> None:
    """One pass cannot distinguish a short list from an unscrolled one."""
    assert virtualization_verdict(59, 59, passes_used=1) == "inconclusive"


def test_a_single_pass_is_inconclusive_even_when_counts_differ() -> None:
    assert virtualization_verdict(10, 40, passes_used=1) == "inconclusive"


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
