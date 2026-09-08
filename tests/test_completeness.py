"""The completeness contract of ADR-0004.

`complete` was a boolean derived from a single stop reason, and Sprint 006
measured that reason never firing: five conversations, two runs, zero
`chat_start` stops. A constant field cannot distinguish a whole history from a
truncated one, which is the only thing it exists to do.

These tests pin the three-valued replacement. No browser and no WhatsApp Web:
the classification is a pure function of the stop reason and the panel's loading
state, which is what makes it testable at all.
"""

from __future__ import annotations

from whatsapp_chat_extractor.history import (
    COMPLETENESS_PROVEN,
    COMPLETENESS_TRUNCATED,
    COMPLETENESS_UNPROVEN,
    STOP_CHAT_START,
    STOP_LOADING_UNRESOLVED,
    STOP_MAX_PASSES,
    STOP_STALLED,
    HarvestedRow,
    MessageAccumulator,
    build_result,
    classify_completeness,
    decide_stop,
)
from whatsapp_chat_extractor.writers import SCHEMA_VERSION, build_export


def row(message_id: str, body: str) -> HarvestedRow:
    return {
        "message_id": message_id,
        "sender": "contact",
        "timestamp": "[12:00, 27/8/2026]",
        "body": body,
        "kind": "text",
    }


def accumulator_with_one_message() -> MessageAccumulator:
    accumulator = MessageAccumulator()
    accumulator.add_pass([row("m1", "hola")])
    return accumulator


# --- classify_completeness: the three states ------------------------------


def test_reaching_the_start_marker_is_proven() -> None:
    assert classify_completeness(STOP_CHAT_START, panel_loading=False) == (
        COMPLETENESS_PROVEN
    )


def test_a_quiet_stall_is_unproven_not_proven() -> None:
    """The whole point of ADR-0004.

    A stall is the strongest signal available and it is still an inference, so
    it gets its own name rather than being flattened into the boolean. Option B
    did the flattening and shipped 217 messages labelled complete.
    """
    assert classify_completeness(STOP_STALLED, panel_loading=False) == (
        COMPLETENESS_UNPROVEN
    )


def test_the_pass_cap_is_truncated() -> None:
    assert classify_completeness(STOP_MAX_PASSES, panel_loading=False) == (
        COMPLETENESS_TRUNCATED
    )


def test_the_pass_cap_stays_truncated_while_loading() -> None:
    assert classify_completeness(STOP_MAX_PASSES, panel_loading=True) == (
        COMPLETENESS_TRUNCATED
    )


def test_a_stall_over_a_loading_panel_is_truncated() -> None:
    """Defensive, and deliberately kept after W4a made it unreachable.

    `decide_stop` suppresses the stall verdict while the panel is loading, so
    this pairing can no longer come out of the harvest loop. It is exactly what
    probe run 3 recorded before that fix — `chat_41d97`, 175 passes, a
    `loading-spinner` still in the chrome — and a classifier that reported it as
    `unproven` would repeat the error the fix removed.
    """
    assert classify_completeness(STOP_STALLED, panel_loading=True) == (
        COMPLETENESS_TRUNCATED
    )


def test_an_unrecognised_stop_reason_is_truncated_never_proven() -> None:
    """Fail closed. An unknown reason is not evidence of having arrived."""
    assert classify_completeness("some_future_reason", panel_loading=False) == (
        COMPLETENESS_TRUNCATED
    )


def test_an_unresolved_loading_spinner_is_truncated() -> None:
    """H-003: `classify_completeness` needed no edit for the new reason.

    `STOP_LOADING_UNRESOLVED` is a reason this function does not explicitly
    recognise, and its fail-closed design (see the unrecognised-reason case
    above) already routes anything it does not name to `truncated` rather than
    `proven`. That is why the fix to `decide_stop` did not require a matching
    change here: a harvest that gave up because a spinner never resolved has
    not proven it reached the top of the conversation.
    """
    assert classify_completeness(STOP_LOADING_UNRESOLVED, panel_loading=True) == (
        COMPLETENESS_TRUNCATED
    )


# --- decide_stop: bounding the H-003 spinner suppression -------------------


def test_ordinary_stalling_still_stops_the_harvest() -> None:
    """Regression guard: the loading bound must not weaken the plain case.

    With no spinner on screen, reaching `stall_threshold` must keep returning
    `STOP_STALLED` exactly as it did before H-003 touched `decide_stop`.
    """
    assert decide_stop(
        at_start=False,
        stall_count=3,
        stall_threshold=3,
        passes_used=10,
        max_passes=2000,
        panel_loading=False,
    ) == STOP_STALLED


def test_loading_grace_is_honored_at_its_exact_boundary() -> None:
    """The grace period is applied, not merely accepted as an argument.

    `stall_threshold=3` and `loading_grace=5` bound the suppression at 8. At
    that exact count the harvest must still be allowed to continue: the
    landed comparison is `stall_count > stall_threshold + loading_grace`, so
    a value equal to the sum must fail it. A regression that dropped
    `loading_grace` from the sum (so the boundary is judged against
    `stall_threshold` alone) or that flipped the operator to `>=` would both
    return `STOP_LOADING_UNRESOLVED` here instead of `None`.
    """
    assert decide_stop(
        at_start=False,
        stall_count=8,
        stall_threshold=3,
        passes_used=10,
        max_passes=2000,
        panel_loading=True,
        loading_grace=5,
    ) is None


def test_loading_grace_expires_and_the_harvest_gives_up_honestly() -> None:
    """Past the bound, the spinner no longer suppresses the stall verdict.

    One pass beyond the boundary pinned above, `decide_stop` must report
    `STOP_LOADING_UNRESOLVED` rather than `None` (the pre-H-003 unbounded
    suppression) or `STOP_STALLED` (which would misreport a spinner still on
    screen as an ordinary stall).
    """
    assert decide_stop(
        at_start=False,
        stall_count=9,
        stall_threshold=3,
        passes_used=10,
        max_passes=2000,
        panel_loading=True,
        loading_grace=5,
    ) == STOP_LOADING_UNRESOLVED


def test_chat_start_still_wins_over_an_unresolved_spinner() -> None:
    """Ordering pin: a proven start outranks every other stop reason.

    Even past the loading-grace boundary, a visible start-of-chat marker must
    still produce `STOP_CHAT_START`, not the new `STOP_LOADING_UNRESOLVED`.
    """
    assert decide_stop(
        at_start=True,
        stall_count=9,
        stall_threshold=3,
        passes_used=10,
        max_passes=2000,
        panel_loading=True,
        loading_grace=5,
    ) == STOP_CHAT_START


# --- build_result: the harvest reports its own completeness ---------------


def test_build_result_carries_completeness() -> None:
    result = build_result(
        accumulator_with_one_message(),
        stopped_reason=STOP_STALLED,
        passes_used=9,
        panel_loading=False,
    )
    assert result["completeness"] == COMPLETENESS_UNPROVEN
    assert result["stopped_reason"] == STOP_STALLED
    assert result["passes_used"] == 9


def test_build_result_keeps_the_boolean_derived_from_proven() -> None:
    """`complete` is retained for v4 readers and is never set independently."""
    proven = build_result(
        accumulator_with_one_message(),
        stopped_reason=STOP_CHAT_START,
        passes_used=4,
        panel_loading=False,
    )
    stalled = build_result(
        accumulator_with_one_message(),
        stopped_reason=STOP_STALLED,
        passes_used=4,
        panel_loading=False,
    )
    assert proven["complete"] is True
    assert stalled["complete"] is False
    for result in (proven, stalled):
        assert result["complete"] is (result["completeness"] == COMPLETENESS_PROVEN)


def test_panel_loading_defaults_to_not_loading() -> None:
    """Callers predating the argument keep working, and get the honest value."""
    result = build_result(
        accumulator_with_one_message(),
        stopped_reason=STOP_STALLED,
        passes_used=2,
    )
    assert result["completeness"] == COMPLETENESS_UNPROVEN


# --- the export payload ---------------------------------------------------


def test_export_is_schema_v6_and_states_completeness() -> None:
    """The completeness contract is unchanged by v6; only the version moved.

    `ADR-0007` is additive: `completeness`, `complete` and `stopped_reason`
    carry exactly what `ADR-0004` gave them. This case exists to prove that a
    schema bump did **not** quietly alter the three-valued verdict — which is
    also why it asserts the literal, not `SCHEMA_VERSION == SCHEMA_VERSION`
    (`KI-008-F`).
    """
    export = build_export(
        chat_title="Some Contact",
        messages=[],
        completeness=COMPLETENESS_UNPROVEN,
        stopped_reason=STOP_STALLED,
    )
    assert export["schema_version"] == 6
    assert SCHEMA_VERSION == 6
    assert export["completeness"] == COMPLETENESS_UNPROVEN
    assert export["complete"] is False
    assert export["stopped_reason"] == STOP_STALLED


def test_export_derives_complete_from_completeness() -> None:
    unproven = build_export(
        chat_title="Some Contact",
        messages=[],
        completeness=COMPLETENESS_UNPROVEN,
        stopped_reason=STOP_STALLED,
    )
    proven = build_export(
        chat_title="Some Contact",
        messages=[],
        completeness=COMPLETENESS_PROVEN,
        stopped_reason=STOP_CHAT_START,
    )
    assert unproven["complete"] is False
    assert proven["complete"] is True


def test_export_still_carries_no_title() -> None:
    """ADR-0001 unchanged: the title is hashed and dropped, never stored."""
    export = build_export(
        chat_title="Some Contact",
        messages=[],
        completeness=COMPLETENESS_TRUNCATED,
        stopped_reason=STOP_MAX_PASSES,
    )
    assert "Some Contact" not in str(export)
    assert export["chat_id"].startswith("chat_")
