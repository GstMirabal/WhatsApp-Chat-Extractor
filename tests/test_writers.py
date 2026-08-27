"""Offline tests for JSON writers (no live WhatsApp)."""

from __future__ import annotations

import json
from pathlib import Path

from whatsapp_chat_extractor.writers import (
    MessageRecord,
    build_export,
    write_chat_export,
)


def test_build_export_sets_fields() -> None:
    messages: list[MessageRecord] = [
        {"sender": "me", "timestamp": "10:00", "body": "hola", "order": 0},
        {"sender": "contact", "timestamp": "10:01", "body": "hi", "order": 1},
    ]
    export = build_export(chat_id="c1", title="Cliente Demo", messages=messages)
    assert export["chat_id"] == "c1"
    assert export["title"] == "Cliente Demo"
    assert export["exported_at"].endswith("Z")
    assert len(export["messages"]) == 2
    assert export["messages"][1]["body"] == "hi"


def test_write_chat_export_creates_json(tmp_path: Path) -> None:
    export = build_export(
        chat_id="c1",
        title="Cliente Demo",
        messages=[
            {"sender": "me", "timestamp": "10:00", "body": "hola", "order": 0},
        ],
    )
    path = write_chat_export(export, data_dir=tmp_path)
    assert path.is_file()
    assert path.parent == tmp_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["chat_id"] == "c1"
    assert payload["messages"][0]["body"] == "hola"


def test_build_export_slugs_empty_chat_id() -> None:
    export = build_export(chat_id="", title="Ana Pérez", messages=[])
    assert "Ana" in export["chat_id"] or "ana" in export["chat_id"].lower()
