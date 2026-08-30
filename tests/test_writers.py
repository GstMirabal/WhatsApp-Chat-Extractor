"""Offline tests for JSON writers (no live WhatsApp)."""

from __future__ import annotations

import json
from pathlib import Path

from whatsapp_chat_extractor.writers import (
    SCHEMA_VERSION,
    MessageRecord,
    build_export,
    pseudonymous_chat_id,
    write_chat_export,
)

REAL_NAME = "Ana Pérez García"


def test_build_export_sets_fields() -> None:
    messages: list[MessageRecord] = [
        {"sender": "me", "timestamp": "10:00, 27/8/2026", "body": "hola", "kind": "text", "order": 0},
        {"sender": "contact", "timestamp": "10:01, 27/8/2026", "body": "hi", "kind": "text", "order": 1},
    ]
    export = build_export(
        chat_title="Cliente Demo",
        messages=messages,
        complete=True,
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
        complete=False,
        stopped_reason="max_passes",
    )
    assert export["schema_version"] == SCHEMA_VERSION
    assert export["message_count"] == 1
    assert export["complete"] is False
    assert export["stopped_reason"] == "max_passes"


def test_message_count_tracks_the_message_list() -> None:
    export = build_export(
        chat_title="Cliente Demo",
        messages=[],
        complete=False,
        stopped_reason="stalled",
    )
    assert export["message_count"] == 0


def test_the_chat_name_never_reaches_the_payload() -> None:
    """The operator's data-protection constraint, asserted rather than assumed."""
    export = build_export(
        chat_title=REAL_NAME,
        messages=[],
        complete=False,
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
        complete=False,
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
        complete=True,
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
        complete=False,
        stopped_reason="max_passes",
    )
    payload = json.loads(
        write_chat_export(export, data_dir=tmp_path).read_text(encoding="utf-8")
    )
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["complete"] is False
    assert payload["stopped_reason"] == "max_passes"
    assert payload["message_count"] == 0


# --- schema v4: every message states its medium (ADR-0003) ------------------


def test_the_schema_version_is_four() -> None:
    """v3 files carry no `kind`, so the version is what tells a reader apart."""
    assert SCHEMA_VERSION == 4


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
        complete=True,
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
        complete=False,
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
        complete=True,
        stopped_reason="chat_start",
    )
    path = write_chat_export(export, data_dir=tmp_path)
    raw = path.read_text(encoding="utf-8")
    assert "blob:" not in raw
    assert "data:image" not in raw
    assert "https://" not in raw
    assert REAL_NAME not in raw
