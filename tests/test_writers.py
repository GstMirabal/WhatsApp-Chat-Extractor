"""Offline tests for JSON writers (no live WhatsApp)."""

from __future__ import annotations

import json
from pathlib import Path

from whatsapp_chat_extractor.writers import (
    SCHEMA_VERSION,
    MessageRecord,
    build_export,
    write_chat_export,
)


def test_build_export_sets_fields() -> None:
    messages: list[MessageRecord] = [
        {"sender": "me", "timestamp": "10:00", "body": "hola", "order": 0},
        {"sender": "contact", "timestamp": "10:01", "body": "hi", "order": 1},
    ]
    export = build_export(
        chat_id="c1",
        title="Cliente Demo",
        messages=messages,
        complete=True,
        stopped_reason="chat_start",
    )
    assert export["chat_id"] == "c1"
    assert export["title"] == "Cliente Demo"
    assert export["exported_at"].endswith("Z")
    assert len(export["messages"]) == 2
    assert export["messages"][1]["body"] == "hi"


def test_build_export_declares_schema_and_completeness() -> None:
    """A learning corpus must be able to say whether it holds the whole chat."""
    export = build_export(
        chat_id="c1",
        title="Cliente Demo",
        messages=[
            {"sender": "me", "timestamp": "10:00", "body": "hola", "order": 0},
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
        chat_id="c1",
        title="Cliente Demo",
        messages=[],
        complete=True,
        stopped_reason="stalled",
    )
    assert export["message_count"] == 0


def test_write_chat_export_creates_json(tmp_path: Path) -> None:
    export = build_export(
        chat_id="c1",
        title="Cliente Demo",
        messages=[
            {"sender": "me", "timestamp": "10:00", "body": "hola", "order": 0},
        ],
        complete=True,
        stopped_reason="chat_start",
    )
    path = write_chat_export(export, data_dir=tmp_path)
    assert path.is_file()
    assert path.parent == tmp_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["chat_id"] == "c1"
    assert payload["messages"][0]["body"] == "hola"


def test_written_json_carries_the_completeness_fields(tmp_path: Path) -> None:
    """The consumer reads the file, not the process that produced it."""
    export = build_export(
        chat_id="c1",
        title="Cliente Demo",
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


def test_build_export_slugs_empty_chat_id() -> None:
    export = build_export(
        chat_id="",
        title="Ana Pérez",
        messages=[],
        complete=True,
        stopped_reason="chat_start",
    )
    assert "Ana" in export["chat_id"] or "ana" in export["chat_id"].lower()
