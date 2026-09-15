"""Merge and termination rules for the full-history harvest.

Synthetic pass sequences only: no browser, no WhatsApp Web. Each test states the
DOM windows a scroll would have produced, which is the part of the harvest that
can be wrong in a way the operator would not notice.
"""

from __future__ import annotations

import pytest

from whatsapp_chat_extractor.history import (
    STOP_CHAT_START,
    STOP_DEADLINE,
    STOP_MAX_PASSES,
    STOP_STALLED,
    HarvestedRow,
    MessageAccumulator,
    build_result,
    decide_stop,
    fallback_message_id,
)


def row(
    message_id: str,
    body: str,
    sender: str = "contact",
    kind: str = "text",
    timestamp: str = "12:00, 27/8/2026",
) -> HarvestedRow:
    """One harvested row, shaped as `export_one` actually produces it.

    The timestamp carries **no brackets**: `_row_timestamp` matches
    `\\[(.*?)\\]` against `data-pre-plain-text` and returns `group(1)`, so the
    brackets are gone before a row is built. This fixture used to include them,
    which cost nothing while `timestamp` was only copied through, and would have
    made every v6 `timestamp_iso` empty for a reason that exists nowhere but in
    the fixture.
    """
    return {
        "message_id": message_id,
        "sender": sender,
        "timestamp": timestamp,
        "body": body,
        "kind": kind,
    }


def test_overlapping_passes_keep_each_message_once() -> None:
    """The window a scroll reveals overlaps the previous one; ids deduplicate."""
    accumulator = MessageAccumulator()
    assert accumulator.add_pass([row("c", "third"), row("d", "fourth")]) == 2
    assert accumulator.add_pass([row("a", "first"), row("b", "second"),
                                 row("c", "third")]) == 2

    bodies = [message["body"] for message in accumulator.consolidate()]
    assert bodies == ["first", "second", "third", "fourth"]


def test_order_is_conversation_order_not_discovery_order() -> None:
    """Scrolling upward discovers newest first; `order` must still read oldest first."""
    accumulator = MessageAccumulator()
    accumulator.add_pass([row("z", "newest")])
    accumulator.add_pass([row("m", "middle")])
    accumulator.add_pass([row("a", "oldest")])

    messages = accumulator.consolidate()
    assert [message["body"] for message in messages] == ["oldest", "middle", "newest"]
    assert [message["order"] for message in messages] == [0, 1, 2]


def test_a_pass_revealing_nothing_new_adds_nothing() -> None:
    accumulator = MessageAccumulator()
    accumulator.add_pass([row("a", "first")])
    assert accumulator.add_pass([row("a", "first")]) == 0
    assert len(accumulator.consolidate()) == 1


def test_empty_pass_is_tolerated() -> None:
    accumulator = MessageAccumulator()
    assert accumulator.add_pass([]) == 0
    assert accumulator.consolidate() == []


# --- schema v6: the record keeps the identity it deduped on (ADR-0007) ------


def test_the_message_id_reaches_the_record_it_was_deduped_on() -> None:
    """Until v6 `consolidate` dropped it, so no message survived re-export.

    The id is not recomputed here — it is the same string `add_pass` used as
    the deduplication key, which is the whole point: a value the harvest
    already trusted for identity is the one the file should carry.
    """
    accumulator = MessageAccumulator()
    accumulator.add_pass([row("true_id_1", "first"), row("true_id_2", "second")])

    assert [m["message_id"] for m in accumulator.consolidate()] == [
        "true_id_1", "true_id_2"
    ]


def test_writing_the_id_out_does_not_stop_it_deduplicating() -> None:
    """Regression: `message_id` gains a second job and must keep the first."""
    accumulator = MessageAccumulator()
    accumulator.add_pass([row("same", "first")])

    assert accumulator.add_pass([row("same", "first seen again")]) == 0
    assert len(accumulator.consolidate()) == 1


def test_the_rendered_timestamp_is_kept_and_a_parsed_one_added_beside_it() -> None:
    accumulator = MessageAccumulator()
    accumulator.add_pass([row("a", "hola", timestamp="14:32, 3/9/2026")])

    (message,) = accumulator.consolidate()
    assert message["timestamp"] == "14:32, 3/9/2026"
    assert message["timestamp_iso"] == "2026-09-03T14:32"


def test_a_row_with_only_a_clock_consolidates_with_an_empty_parsed_stamp() -> None:
    """The `msg-meta` fallback yields `HH:MM`. It must not become today's date."""
    accumulator = MessageAccumulator()
    accumulator.add_pass([row("a", "hola", timestamp="14:33")])

    (message,) = accumulator.consolidate()
    assert message["timestamp"] == "14:33"
    assert message["timestamp_iso"] == ""


def test_an_unobserved_locale_leaves_the_parsed_stamp_empty_not_wrong() -> None:
    accumulator = MessageAccumulator()
    accumulator.add_pass([row("a", "hola", timestamp="14:32, 3/9/2026")])

    (message,) = accumulator.consolidate(locale="ja-JP")
    assert message["timestamp_iso"] == ""
    assert message["timestamp"] == "14:32, 3/9/2026"


def test_a_row_with_no_message_id_is_rejected_at_the_pass_not_at_the_record() -> None:
    """`message_id` is mandatory, and the accumulator is where that is enforced.

    Written after a first draft of `_as_record` defended against a missing id
    with `row.get(...)`. That branch was unreachable — `add_pass` indexes
    `message_id` to deduplicate — and the comment justifying it was wrong. The
    tolerance `kind` gets is not owed to `message_id`, because nothing indexes
    `kind`.
    """
    accumulator = MessageAccumulator()

    with pytest.raises(KeyError, match="message_id"):
        accumulator.add_pass(
            [{"sender": "me", "timestamp": "14:32, 3/9/2026", "body": "hola"}]  # type: ignore[list-item]
        )


def test_a_row_predating_kind_still_consolidates_as_text() -> None:
    """A replayed v3 fixture: nothing indexes `kind`, so it does reach the record."""
    accumulator = MessageAccumulator()
    accumulator.add_pass(
        [{"message_id": "a", "sender": "me",  # type: ignore[list-item]
          "timestamp": "14:32, 3/9/2026", "body": "hola"}]
    )

    (message,) = accumulator.consolidate()
    assert message["kind"] == "text"
    assert message["message_id"] == "a"


def test_identical_text_from_different_senders_stays_distinct() -> None:
    """The fallback id folds in the sender, so a repeated 'ok' is not collapsed."""
    first = fallback_message_id("ana", "[12:00, 27/8/2026]", "ok")
    second = fallback_message_id("me", "[12:00, 27/8/2026]", "ok")
    assert first != second

    accumulator = MessageAccumulator()
    accumulator.add_pass([row(first, "ok", "ana"), row(second, "ok", "me")])
    assert len(accumulator.consolidate()) == 2


def test_fallback_id_is_stable_across_calls() -> None:
    args = ("ana", "[12:00, 27/8/2026]", "hola")
    assert fallback_message_id(*args) == fallback_message_id(*args)
    assert fallback_message_id(*args).startswith("sha1:")


def test_chat_start_marker_stops_the_harvest() -> None:
    reason = decide_stop(
        at_start=True, stall_count=0, stall_threshold=3,
        passes_used=1, max_passes=2000,
    )
    assert reason == STOP_CHAT_START


def test_stalled_passes_stop_the_harvest() -> None:
    assert decide_stop(
        at_start=False, stall_count=3, stall_threshold=3,
        passes_used=10, max_passes=2000,
    ) == STOP_STALLED
    assert decide_stop(
        at_start=False, stall_count=2, stall_threshold=3,
        passes_used=10, max_passes=2000,
    ) is None


def test_a_loading_panel_is_not_a_stall() -> None:
    """The defect the Sprint 006 probe measured, in the rule that caused it.

    Walking five conversations, one was declared `stalled` after 175 passes
    with `data-testid="loading-spinner"` still in the panel chrome: the harvest
    gave up while WhatsApp was still fetching and reported a top it had never
    reached. A spinner is positive evidence that more history is coming, so it
    cannot be read as the beginning of the conversation.
    """
    assert decide_stop(
        at_start=False, stall_count=3, stall_threshold=3,
        passes_used=10, max_passes=2000, panel_loading=True,
    ) is None


def test_a_spinner_that_never_resolves_still_terminates() -> None:
    """Suppressing the stall must not cost the termination guarantee.

    `max_passes` is deliberately not suppressed, so a spinner stuck forever
    ends the run — and reports `max_passes`, which is the honest reason, rather
    than a top it did not reach.
    """
    assert decide_stop(
        at_start=False, stall_count=3, stall_threshold=3,
        passes_used=2000, max_passes=2000, panel_loading=True,
    ) == STOP_MAX_PASSES


def test_a_reached_start_still_wins_while_loading() -> None:
    """A visible marker is measured evidence and outranks a spinner."""
    assert decide_stop(
        at_start=True, stall_count=3, stall_threshold=3,
        passes_used=10, max_passes=2000, panel_loading=True,
    ) == STOP_CHAT_START


def test_a_deadline_stops_the_harvest_once_elapsed() -> None:
    """KI-009-H: a synthetic clock past the budget stops the harvest.

    No browser and no real clock: `elapsed_seconds` is the number the impure
    caller would have computed from `time.monotonic()`, handed straight to
    this pure function.
    """
    assert decide_stop(
        at_start=False, stall_count=0, stall_threshold=3,
        passes_used=10, max_passes=2000,
        elapsed_seconds=5.1, deadline_seconds=5.0,
    ) == STOP_DEADLINE


def test_a_deadline_does_not_fire_before_it_elapses() -> None:
    assert decide_stop(
        at_start=False, stall_count=0, stall_threshold=3,
        passes_used=10, max_passes=2000,
        elapsed_seconds=4.9, deadline_seconds=5.0,
    ) is None


def test_no_deadline_means_unbounded_wall_clock_time() -> None:
    """`deadline_seconds=None` (the default) never stops the harvest on time."""
    assert decide_stop(
        at_start=False, stall_count=0, stall_threshold=3,
        passes_used=10, max_passes=2000,
        elapsed_seconds=999_999.0, deadline_seconds=None,
    ) is None


def test_a_deadline_fires_despite_a_loading_panel() -> None:
    """The un-suppressible property: a spinner does not buy the deadline extra time.

    Unlike the stall verdict, `STOP_DEADLINE` is not suppressed by
    `panel_loading=True`: a network round trip to the phone that never
    returns is exactly the case the deadline exists to catch.
    """
    assert decide_stop(
        at_start=False, stall_count=3, stall_threshold=3,
        passes_used=10, max_passes=2000, panel_loading=True,
        elapsed_seconds=5.1, deadline_seconds=5.0,
    ) == STOP_DEADLINE


def test_pass_cap_stops_the_harvest() -> None:
    assert decide_stop(
        at_start=False, stall_count=0, stall_threshold=3,
        passes_used=2000, max_passes=2000,
    ) == STOP_MAX_PASSES


def test_chat_start_wins_over_the_pass_cap() -> None:
    """A harvest that reaches the start on its last allowed pass is complete."""
    assert decide_stop(
        at_start=True, stall_count=0, stall_threshold=3,
        passes_used=2000, max_passes=2000,
    ) == STOP_CHAT_START


def test_reaching_the_start_reports_complete() -> None:
    accumulator = MessageAccumulator()
    accumulator.add_pass([row("a", "first")])
    result = build_result(accumulator, stopped_reason=STOP_CHAT_START, passes_used=4)

    assert result["complete"] is True
    assert result["stopped_reason"] == STOP_CHAT_START
    assert result["passes_used"] == 4


def test_stalling_does_not_count_as_a_complete_history() -> None:
    """The first live run stalled after 1.2s and reported a whole chat exported.

    217 messages came out of a conversation the operator knew to be longer,
    marked `complete: true`, because the panel had not finished loading inside
    the fixed wait. Only the start marker proves completeness now.
    """
    result = build_result(
        MessageAccumulator(), stopped_reason=STOP_STALLED, passes_used=9
    )
    assert result["complete"] is False
    assert result["stopped_reason"] == STOP_STALLED


def test_hitting_the_pass_cap_reports_incomplete() -> None:
    """The defect this sprint fixes: a truncated dump must say so."""
    result = build_result(
        MessageAccumulator(), stopped_reason=STOP_MAX_PASSES, passes_used=2000
    )
    assert result["complete"] is False
    assert result["stopped_reason"] == STOP_MAX_PASSES


# --- media rows survive the accumulator (ADR-0003) --------------------------


def test_two_media_rows_with_distinct_ids_are_both_kept() -> None:
    """Two voice notes in one minute have empty bodies and identical metadata.

    Only their DOM identity separates them, which is why `export_one._row_id`
    falls back to the `conv-msg-<HEX>` wrapper before the hashed key is reached.
    """
    accumulator = MessageAccumulator()
    added = accumulator.add_pass([
        row("conv-msg-3AFF87", "", kind="voice"),
        row("conv-msg-3AEE63", "", kind="voice"),
    ])
    assert added == 2
    assert [m["kind"] for m in accumulator.consolidate()] == ["voice", "voice"]


def test_kind_survives_consolidation() -> None:
    accumulator = MessageAccumulator()
    accumulator.add_pass([row("b", "", kind="image"), row("c", "vale")])
    accumulator.add_pass([row("a", "", kind="voice"), row("b", "", kind="image")])
    consolidated = accumulator.consolidate()
    assert [m["kind"] for m in consolidated] == ["voice", "image", "text"]
    assert [m["order"] for m in consolidated] == [0, 1, 2]


def test_the_fallback_key_separates_a_photo_from_a_voice_note() -> None:
    """Same speaker, same minute, both captionless: only `kind` differs."""
    photo = fallback_message_id("me", "[12:00, 27/8/2026]", "", "image")
    voice = fallback_message_id("me", "[12:00, 27/8/2026]", "", "voice")
    assert photo != voice


def test_the_fallback_key_still_collides_for_two_rows_of_one_kind() -> None:
    """Asserted so the limit is recorded rather than assumed to be solved.

    Nothing in a captionless voice note's text distinguishes it from the next
    one; the separation has to come from the DOM identity, not from this hash.
    """
    first = fallback_message_id("me", "[12:00, 27/8/2026]", "", "voice")
    second = fallback_message_id("me", "[12:00, 27/8/2026]", "", "voice")
    assert first == second
