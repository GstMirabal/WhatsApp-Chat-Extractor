"""Merge and termination rules for the full-history harvest.

Synthetic pass sequences only: no browser, no WhatsApp Web. Each test states the
DOM windows a scroll would have produced, which is the part of the harvest that
can be wrong in a way the operator would not notice.
"""

from __future__ import annotations

from whatsapp_chat_extractor.history import (
    STOP_CHAT_START,
    STOP_MAX_PASSES,
    STOP_STALLED,
    HarvestedRow,
    MessageAccumulator,
    build_result,
    decide_stop,
    fallback_message_id,
)


def row(
    message_id: str, body: str, sender: str = "contact", kind: str = "text"
) -> HarvestedRow:
    return {
        "message_id": message_id,
        "sender": sender,
        "timestamp": "[12:00, 27/8/2026]",
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
