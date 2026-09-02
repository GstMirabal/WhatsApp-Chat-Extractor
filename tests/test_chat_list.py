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

import random

import pytest

from whatsapp_chat_extractor.chat_list import (
    CHAT_ROW_SELECTOR,
    ENUMERATION_CONVERGED,
    ENUMERATION_TRUNCATED,
    ENUMERATION_UNCONVERGED,
    TITLE_SELECTORS,
    ChatRef,
    at_pane_bottom,
    classify_enumeration,
    find_row,
    open_chat_by_digest,
    row_digests,
    row_title,
    seek_scroll_top,
    sweep_chat_list,
    sweep_until_stable,
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


class ReorderingPane(FakePane):
    """A list that moves the last conversation to the top every N reads.

    What an arriving message does to a real chat list. `FakePane` never
    reorders, which makes it more forgiving than WhatsApp Web on exactly the
    axis Q2 could not settle: the probe measured position stable over a
    two-minute sweep, and an enumeration of 899 conversations runs longer.
    """

    def __init__(self, *args: object, every: int = 5, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._every = every
        self._reads = 0

    def query_selector_all(self, selector: str) -> list[FakeRow]:
        self._reads += 1
        if self._reads % self._every == 0 and len(self.titles) > 1:
            self.titles.insert(0, self.titles.pop())
        return super().query_selector_all(selector)


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


# --- fidelity of the double, and the limit it exposes ---------------------

# Geometry as measured on WhatsApp Web (probe runs 2 and 3, 2026-08-31):
# 899 conversations, at most 70 rendered at once, 746px viewport over a
# ~68 400px pane — roughly 76px per row, so the render buffer is about 7.8x
# the one-viewport scroll step. The default fixture above tiles exactly
# (window == step), which is more forgiving on that axis; these use the real
# numbers instead.
MEASURED = {"window": 70, "row_height": 76, "client_height": 746}


def test_the_sweep_is_complete_under_the_measured_geometry() -> None:
    pane = FakePane(titles(899), **MEASURED)
    refs = sweep_chat_list(pane, max_passes=4000, settle_ms=0)
    assert len(refs) == 899
    assert len({ref["chat_id"] for ref in refs}) == 899


def test_the_sweep_survives_a_virtualizer_that_renders_late() -> None:
    """A real virtualizer re-renders asynchronously; `FakePane` never lags."""
    class LaggyPane(FakePane):
        def __init__(self, *args: object, lag: int = 2, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            self._lag = lag
            self._pending: list[int] = []

        def query_selector_all(self, selector: str) -> list[FakeRow]:
            self._pending.append(self.scroll_top)
            shown = self._pending.pop(0) if len(self._pending) > self._lag else 0
            live, self.scroll_top = self.scroll_top, shown
            rows = super().query_selector_all(selector)
            self.scroll_top = live
            return rows

    pane = LaggyPane(titles(899), lag=3, **MEASURED)
    assert len(sweep_chat_list(pane, max_passes=4000, settle_ms=0)) == 899


def test_a_reordering_list_makes_the_sweep_UNDERCOUNT_silently() -> None:
    """A MEASURED LIMIT of the shipped enumerator, pinned so it is not a surprise.

    When the list reorders mid-sweep — one arriving message does it — a
    conversation can move from below the sweep position to above it and never be
    seen. The digest key prevents visiting one twice, so there are **no
    duplicates**; the loss is silent undercounting, and `enumeration_complete`
    still reports `true` because the pane foot *was* reached.

    Measured here: 899 conversations, one reorder every 5 reads, ~882 found.
    This asserts the defect exists rather than asserting a fixed number, because
    the exact count depends on interleaving. Sprint 007 shipped it knowingly:
    Q2 measured position stable over a two-minute sweep and did not measure a
    busy account over a longer one. The fix belongs to a later sprint — sweeping
    until two consecutive sweeps agree is the obvious candidate — and it needs
    its own measurement, not a guess.
    """
    pane = ReorderingPane(titles(899), every=5, **MEASURED)
    refs = sweep_chat_list(pane, max_passes=4000, settle_ms=0)
    ids = [ref["chat_id"] for ref in refs]
    assert len(ids) == len(set(ids)), "no conversation may be enumerated twice"
    assert len(refs) < 899, "this test exists to pin an undercount that is real"


# --- converging enumeration (ADR-0005) --------------------------------------
#
# The four tests above document `sweep_chat_list`, the single-pass primitive,
# and remain true of it: Sprint 008 did not change that function. What follows
# covers `sweep_until_stable`, which repeats it and unions the results.


def test_repeated_sweeping_recovers_what_a_reordering_list_hid() -> None:
    """The defect above, at the same reorder rate, against the converging sweep."""
    pane = ReorderingPane(titles(899), every=5, **MEASURED)
    result = sweep_until_stable(pane, max_passes=4000, settle_ms=0)
    ids = [ref["chat_id"] for ref in result["refs"]]
    assert len(ids) == 899, "a single sweep found 882 of these"
    assert len(set(ids)) == 899
    assert result["enumeration"] == ENUMERATION_CONVERGED


def test_the_worst_measured_reorder_rate_also_recovers_everything() -> None:
    """One reorder every two reads — where a single sweep found 856 of 899."""
    pane = ReorderingPane(titles(899), every=2, **MEASURED)
    result = sweep_until_stable(pane, max_passes=4000, settle_ms=0)
    assert len({ref["chat_id"] for ref in result["refs"]}) == 899
    assert result["enumeration"] == ENUMERATION_CONVERGED


def test_a_quiet_list_converges_on_the_minimum_number_of_sweeps() -> None:
    """Three: one to discover, two to agree. The cost of the fix, pinned."""
    pane = FakePane(titles(899), **MEASURED)
    result = sweep_until_stable(pane, max_passes=4000, settle_ms=0)
    assert len(result["refs"]) == 899
    assert result["sweeps"] == 3
    assert result["enumeration"] == ENUMERATION_CONVERGED


def test_the_union_is_reindexed_contiguously_in_discovery_order() -> None:
    """`index` is a seek hint, so it must span the union with no holes."""
    pane = ReorderingPane(titles(899), every=5, **MEASURED)
    result = sweep_until_stable(pane, max_passes=4000, settle_ms=0)
    assert [ref["index"] for ref in result["refs"]] == list(range(899))


def test_a_sweep_that_never_reaches_the_foot_is_truncated_not_converged() -> None:
    """The pass cap ended it, so nothing may be claimed about the whole list."""
    pane = FakePane(titles(899), **MEASURED)
    result = sweep_until_stable(pane, max_passes=2, settle_ms=0, max_sweeps=3)
    assert result["enumeration"] == ENUMERATION_TRUNCATED
    assert len(result["refs"]) < 899


def test_a_budget_that_runs_out_while_still_finding_chats_is_unconverged() -> None:
    """The foot was reached, but the sweeps had not stopped contributing."""
    pane = ReorderingPane(titles(899), every=2, **MEASURED)
    result = sweep_until_stable(pane, max_passes=4000, settle_ms=0, max_sweeps=2)
    assert result["enumeration"] == ENUMERATION_UNCONVERGED
    assert result["sweeps"] == 2


class RandomReorderPane(FakePane):
    """A harder list: moves a **random** conversation to the top, not the last.

    `ReorderingPane` rotates the tail to the head, which is a favourable shape
    for a converging sweep — a rotation eventually walks every conversation past
    the window on its own. This moves an arbitrary conversation instead, so
    recovery cannot be an artifact of the fixture's regularity.

    Added at the Phase 7 gate, after the committed evidence was found to rest on
    the friendlier fixture alone.
    """

    def __init__(
        self, *args: object, every: int = 5, seed: int = 0, **kwargs: object
    ) -> None:
        super().__init__(*args, **kwargs)
        self._every = every
        self._reads = 0
        self._rng = random.Random(seed)

    def query_selector_all(self, selector: str) -> list[FakeRow]:
        self._reads += 1
        if self._reads % self._every == 0 and len(self.titles) > 1:
            self.titles.insert(0, self.titles.pop(self._rng.randrange(len(self.titles))))
        return super().query_selector_all(selector)


@pytest.mark.parametrize("every", [5, 2])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_recovery_survives_an_irregular_reordering(every: int, seed: int) -> None:
    """The fix must not depend on the reordering being a tidy rotation."""
    single = sweep_chat_list(
        RandomReorderPane(titles(899), every=every, seed=seed, **MEASURED),
        max_passes=4000, settle_ms=0,
    )
    assert len(single) < 899, "the single-pass sweep must still lose conversations here"

    result = sweep_until_stable(
        RandomReorderPane(titles(899), every=every, seed=seed, **MEASURED),
        max_passes=4000, settle_ms=0,
    )
    assert len({ref["chat_id"] for ref in result["refs"]}) == 899
    assert result["enumeration"] == ENUMERATION_CONVERGED


def test_the_union_keeps_first_discovery_order() -> None:
    """`index` is a live-pane seek hint, so the order is load-bearing, not cosmetic.

    Contiguity alone does not pin it: reversing the union keeps `index` a clean
    `range` while sending every seek to the opposite end of the pane. Gap F-3,
    found by mutation at the Phase 7 gate.
    """
    pane = FakePane(titles(30), window=4)
    result = sweep_until_stable(pane, max_passes=4000, settle_ms=0)
    expected = [pseudonymous_chat_id(title) for title in titles(30)]
    assert [ref["chat_id"] for ref in result["refs"]] == expected


def test_the_loop_does_not_stop_on_quiet_sweeps_alone() -> None:
    """Both halves of the break condition must be load-bearing.

    A pane that goes quiet *before* the foot must not end the enumeration:
    dropping `reached_bottom and` from the stop test leaves the suite green
    otherwise. Gap F-5, found by mutation at the Phase 7 gate.
    """
    class LateRevealingPane(FakePane):
        """Withholds most of the list, and never reports its foot until it yields.

        Sweeps 1-3 see only the head and add nothing after the first, so two
        consecutive quiet sweeps accumulate while the pane is demonstrably not
        at its foot. A stop test that ignores `reached_bottom` ends here, with
        most of the account unseen.
        """

        REAL_TOTAL = 120
        HELD_BACK_UNTIL_SWEEP = 4

        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            self._sweeps = 0

        def evaluate(self, js: str, arg: object = None) -> object:
            if isinstance(arg, list):
                if int(arg[1]) == 0:
                    self._sweeps += 1
                return super().evaluate(js, arg)
            metrics = super().evaluate(js, arg)
            # Always taller than what is rendered, so the foot is never reached.
            metrics["scroll_height"] = self.REAL_TOTAL * self.row_height * 2
            return metrics

        def query_selector_all(self, selector: str) -> list[FakeRow]:
            if self._sweeps < self.HELD_BACK_UNTIL_SWEEP:
                return [FakeRow(title) for title in self.titles[:5]]
            return super().query_selector_all(selector)

    pane = LateRevealingPane(titles(120), window=10, row_height=10, client_height=20)
    result = sweep_until_stable(pane, max_passes=200, settle_ms=0, max_sweeps=8)
    assert len(result["refs"]) == 120, "a quiet stretch above the foot is not the end"
    assert result["enumeration"] == ENUMERATION_TRUNCATED, "the foot was never reached"


def test_the_classifier_never_reports_converged_without_the_foot() -> None:
    """Fail-closed: trailing agreement alone is not enough, in either direction."""
    assert classify_enumeration(reached_bottom=False, stable_sweeps=99) == (
        ENUMERATION_TRUNCATED
    )
    assert classify_enumeration(reached_bottom=True, stable_sweeps=0) == (
        ENUMERATION_UNCONVERGED
    )
    assert classify_enumeration(reached_bottom=True, stable_sweeps=2) == (
        ENUMERATION_CONVERGED
    )
