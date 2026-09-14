"""Offline tests for JSON writers (no live WhatsApp)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from whatsapp_chat_extractor.writers import (
    SCHEMA_VERSION,
    MessageRecord,
    build_export,
    pseudonymous_chat_id,
    write_chat_export,
)

REAL_NAME = "Ana Pérez García"


def a_message(*, order: int, timestamp_iso: str) -> MessageRecord:
    """A schema v6 message record, for the cases that only vary its stamp."""
    return {
        "message_id": "true_id",
        "sender": "contact",
        "timestamp": "14:32, 3/9/2026",
        "timestamp_iso": timestamp_iso,
        "body": "hola",
        "kind": "text",
        "order": order,
    }


def test_build_export_sets_fields() -> None:
    messages: list[MessageRecord] = [
        {"sender": "me", "timestamp": "10:00, 27/8/2026", "body": "hola", "kind": "text", "order": 0},
        {"sender": "contact", "timestamp": "10:01, 27/8/2026", "body": "hi", "kind": "text", "order": 1},
    ]
    export = build_export(
        chat_title="Cliente Demo",
        messages=messages,
        completeness="proven",
        stopped_reason="chat_start",
    )
    assert export["exported_at"].endswith("Z")
    assert len(export["messages"]) == 2
    assert export["messages"][1]["body"] == "hi"


def test_build_export_declares_schema_and_completeness() -> None:
    """A learning corpus must be able to say whether it holds the whole chat."""
    export = build_export(
        chat_title="Cliente Demo",
        messages=[
            {"sender": "me", "timestamp": "10:00, 27/8/2026", "body": "hola", "kind": "text", "order": 0},
        ],
        completeness="truncated",
        stopped_reason="max_passes",
    )
    assert export["schema_version"] == SCHEMA_VERSION
    assert export["message_count"] == 1
    assert export["completeness"] == "truncated"
    assert export["complete"] is False
    assert export["stopped_reason"] == "max_passes"


def test_message_count_tracks_the_message_list() -> None:
    export = build_export(
        chat_title="Cliente Demo",
        messages=[],
        completeness="unproven",
        stopped_reason="stalled",
    )
    assert export["message_count"] == 0


def test_the_chat_name_never_reaches_the_payload() -> None:
    """The operator's data-protection constraint, asserted rather than assumed."""
    export = build_export(
        chat_title=REAL_NAME,
        messages=[],
        completeness="unproven",
        stopped_reason="stalled",
    )
    assert "title" not in export
    assert REAL_NAME not in json.dumps(export, ensure_ascii=False)
    assert "Ana" not in export["chat_id"]
    assert export["chat_id"].startswith("chat_")


def test_the_chat_name_never_reaches_the_filename(tmp_path: Path) -> None:
    """A directory listing is where a name is read without opening anything."""
    export = build_export(
        chat_title=REAL_NAME,
        messages=[],
        completeness="unproven",
        stopped_reason="stalled",
    )
    path = write_chat_export(export, data_dir=tmp_path)
    assert "Ana" not in path.name
    assert "Perez" not in path.name and "Pérez" not in path.name
    assert path.name.startswith(export["chat_id"])


def test_pseudonymous_id_is_stable_and_distinct() -> None:
    assert pseudonymous_chat_id(REAL_NAME) == pseudonymous_chat_id(REAL_NAME)
    assert pseudonymous_chat_id(f" {REAL_NAME} ") == pseudonymous_chat_id(REAL_NAME)
    assert pseudonymous_chat_id(REAL_NAME) != pseudonymous_chat_id("Otro Contacto")


def test_write_chat_export_creates_json(tmp_path: Path) -> None:
    export = build_export(
        chat_title="Cliente Demo",
        messages=[
            {"sender": "me", "timestamp": "10:00, 27/8/2026", "body": "hola", "kind": "text", "order": 0},
        ],
        completeness="proven",
        stopped_reason="chat_start",
    )
    path = write_chat_export(export, data_dir=tmp_path)
    assert path.is_file()
    assert path.parent == tmp_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["chat_id"] == export["chat_id"]
    assert payload["messages"][0]["body"] == "hola"


def test_written_json_carries_the_completeness_fields(tmp_path: Path) -> None:
    """The consumer reads the file, not the process that produced it."""
    export = build_export(
        chat_title="Cliente Demo",
        messages=[],
        completeness="truncated",
        stopped_reason="max_passes",
    )
    payload = json.loads(
        write_chat_export(export, data_dir=tmp_path).read_text(encoding="utf-8")
    )
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["completeness"] == "truncated"
    assert payload["complete"] is False
    assert payload["stopped_reason"] == "max_passes"
    assert payload["message_count"] == 0


# --- schema v6: identity, comparable time, render frame (ADR-0007) ----------


def test_the_schema_version_is_six() -> None:
    """The version is what tells a reader which contract a file was written to.

    v3 carries no `kind`; v4 carries `kind` and a boolean `complete` that is
    always False; v5 carries `completeness`; v6 carries `message_id`,
    `timestamp_iso`, and the locale and timezone the file was rendered under. A
    consumer cannot infer any of this from the payload alone, which is why the
    number is asserted rather than assumed.

    Asserted against the literal as well as the constant, deliberately: reading
    `SCHEMA_VERSION == SCHEMA_VERSION` would pass through any bump at all
    (`KI-008-F`).
    """
    assert SCHEMA_VERSION == 6


def test_the_v6_fields_are_present_on_a_built_export() -> None:
    export = build_export(
        chat_title="Some Contact",
        messages=[],
        completeness="unproven",
        stopped_reason="stalled",
        passes_used=12,
        source_locale="es-ES",
        source_timezone="Europe/Madrid",
    )

    assert export["schema_version"] == 6
    assert export["passes_used"] == 12
    assert export["source_locale"] == "es-ES"
    assert export["source_timezone"] == "Europe/Madrid"
    assert export["undated_messages"] == 0


def test_undated_messages_counts_the_rows_that_carry_no_date() -> None:
    """The corpus reports its own gaps rather than leaving them to be discovered."""
    export = build_export(
        chat_title="Some Contact",
        messages=[
            a_message(order=0, timestamp_iso="2026-09-03T14:32"),
            a_message(order=1, timestamp_iso=""),
            a_message(order=2, timestamp_iso=""),
        ],
        completeness="unproven",
        stopped_reason="stalled",
    )

    assert export["message_count"] == 3
    assert export["undated_messages"] == 2


def test_the_undated_count_is_derived_not_accepted_from_a_caller() -> None:
    """Same reason `complete` is derived: a supplied count can contradict the messages.

    `build_export` takes no `undated_messages` argument, so there is no way to
    hand it a number that disagrees with the list beside it.
    """
    with pytest.raises(TypeError):
        build_export(  # type: ignore[call-arg]
            chat_title="Some Contact",
            messages=[],
            completeness="unproven",
            stopped_reason="stalled",
            undated_messages=99,
        )


def test_the_render_frame_defaults_to_empty_rather_than_to_a_guess() -> None:
    """An unrecorded locale must be distinguishable from a real one.

    Every file written before v6 is effectively in this state, and `ADR-0007`
    decided they are not repaired: nothing stored what they were rendered under.
    """
    export = build_export(
        chat_title="Some Contact",
        messages=[],
        completeness="unproven",
        stopped_reason="stalled",
    )

    assert export["source_locale"] == ""
    assert export["source_timezone"] == ""


def test_a_message_keeps_both_its_rendered_and_its_parsed_timestamp() -> None:
    export = build_export(
        chat_title="Some Contact",
        messages=[a_message(order=0, timestamp_iso="2026-09-03T14:32")],
        completeness="unproven",
        stopped_reason="stalled",
    )

    (message,) = export["messages"]
    assert message["timestamp"] == "14:32, 3/9/2026"
    assert message["timestamp_iso"] == "2026-09-03T14:32"
    assert message["message_id"] == "true_id"


def test_a_media_message_is_exported_with_an_empty_body_and_its_kind() -> None:
    """Under v3 this message produced no record at all.

    The conversation then read question → next question, teaching an adjacency
    that never happened. No media content is stored — only that one was sent.
    """
    messages: list[MessageRecord] = [
        {"sender": "contact", "timestamp": "10:00, 27/8/2026", "body": "¿lo tienes?",
         "kind": "text", "order": 0},
        {"sender": "me", "timestamp": "10:01, 27/8/2026", "body": "",
         "kind": "voice", "order": 1},
        {"sender": "contact", "timestamp": "10:02, 27/8/2026", "body": "vale",
         "kind": "text", "order": 2},
    ]
    export = build_export(
        chat_title="Cliente Demo",
        messages=messages,
        completeness="proven",
        stopped_reason="chat_start",
    )
    assert export["message_count"] == 3
    assert [m["kind"] for m in export["messages"]] == ["text", "voice", "text"]
    assert export["messages"][1]["body"] == ""


def test_message_count_counts_every_medium_not_only_text() -> None:
    """`message_count` named itself a message count while counting text only."""
    messages: list[MessageRecord] = [
        {"sender": "me", "timestamp": "10:00, 27/8/2026", "body": "",
         "kind": "image", "order": 0},
        {"sender": "me", "timestamp": "10:01, 27/8/2026", "body": "",
         "kind": "voice", "order": 1},
    ]
    export = build_export(
        chat_title="Cliente Demo",
        messages=messages,
        completeness="truncated",
        stopped_reason="max_passes",
    )
    assert export["message_count"] == 2


def test_no_media_url_or_binary_reaches_the_written_file(tmp_path: Path) -> None:
    """ADR-0003 §2: the medium is named, its content is never stored."""
    messages: list[MessageRecord] = [
        {"sender": "me", "timestamp": "10:00, 27/8/2026", "body": "",
         "kind": "image", "order": 0},
    ]
    export = build_export(
        chat_title=REAL_NAME,
        messages=messages,
        completeness="proven",
        stopped_reason="chat_start",
    )
    path = write_chat_export(export, data_dir=tmp_path)
    raw = path.read_text(encoding="utf-8")
    assert "blob:" not in raw
    assert "data:image" not in raw
    assert "https://" not in raw
    assert REAL_NAME not in raw
