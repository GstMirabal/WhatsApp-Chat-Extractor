"""Consolidation of per-conversation exports into one NDJSON corpus.

No browser: `read_chat_files`, `build_header` and `write_corpus` are pure
filesystem work over real files under `tmp_path`, following the idiom in
`tests/test_manifest.py` and `tests/test_journal.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from whatsapp_chat_extractor.consolidate import (
    build_header,
    read_chat_files,
    write_corpus,
)
from whatsapp_chat_extractor.writers import (
    SCHEMA_VERSION,
    MessageRecord,
    build_export,
    pseudonymous_chat_id,
)


def a_chat(title: str) -> dict:
    """Build one real schema v6 export for `title`, via `writers.build_export`.

    Args:
        title: Synthetic chat title, hashed into `chat_id` and never stored.

    Returns:
        dict: The export payload as `build_export` produces it.
    """
    messages: list[MessageRecord] = [
        {
            "message_id": "m1",
            "sender": "contact",
            "timestamp": "10:00, 1/1/2026",
            "timestamp_iso": "2026-01-01T10:00:00",
            "body": "hola",
            "kind": "text",
            "order": 0,
        }
    ]
    return build_export(
        chat_title=title,
        messages=messages,
        completeness="proven",
        stopped_reason="chat_start",
    )


def write_chat_file(tmp_path: Path, filename: str, chat: dict) -> Path:
    """Write `chat` as a `chat_*.json` file `read_chat_files` can load.

    Args:
        tmp_path: Directory to write under.
        filename: Exact filename, chosen by the caller to control read order.
        chat: The parsed export payload to serialize.

    Returns:
        Path: The written file.
    """
    path = tmp_path / filename
    path.write_text(json.dumps(chat, ensure_ascii=False), encoding="utf-8")
    return path


def test_three_synthetic_files_produce_a_four_line_corpus(tmp_path: Path) -> None:
    """The header carries the true count and schema; each body line round-trips."""
    paths = [
        write_chat_file(tmp_path, f"chat_{index}.json", a_chat(title))
        for index, title in enumerate(("Ana", "Beto", "Caro"), start=1)
    ]
    sources = [json.loads(path.read_text(encoding="utf-8")) for path in paths]

    chats = read_chat_files(tmp_path)
    header = build_header(chats, "run-1")
    out_path = write_corpus(chats, header, tmp_path / "corpus.ndjson")
    lines = out_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 4
    written_header = json.loads(lines[0])
    assert written_header["chat_count"] == 3
    assert written_header["chat_schema"] == SCHEMA_VERSION
    for line, source in zip(lines[1:], sources):
        assert json.loads(line) == source


def test_duplicate_chat_id_names_both_files(tmp_path: Path) -> None:
    """Two files sharing a `chat_id` are a conflict, not a silent de-duplication."""
    chat = a_chat("Ana")
    write_chat_file(tmp_path, "chat_dup_1.json", chat)
    write_chat_file(tmp_path, "chat_dup_2.json", dict(chat))

    with pytest.raises(ValueError) as excinfo:
        read_chat_files(tmp_path)

    message = str(excinfo.value)
    assert "chat_dup_1.json" in message
    assert "chat_dup_2.json" in message


def test_a_non_v6_file_names_itself_and_its_schema(tmp_path: Path) -> None:
    """A stale schema aborts with the filename and the number found, not v6."""
    stale = {"schema_version": 5, "chat_id": pseudonymous_chat_id("Ana")}
    write_chat_file(tmp_path, "chat_stale.json", stale)

    with pytest.raises(ValueError) as excinfo:
        read_chat_files(tmp_path)

    message = str(excinfo.value)
    assert "chat_stale.json" in message
    assert "5" in message


def test_chat_count_is_derived_from_an_empty_body(tmp_path: Path) -> None:
    """`chat_count` reads the actual list; it is not hardcoded or stale."""
    chats = read_chat_files(tmp_path)
    assert chats == []

    header = build_header(chats, "run-empty")
    assert header["chat_count"] == 0

    out_path = write_corpus(chats, header, tmp_path / "corpus.ndjson")
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["chat_count"] == 0


def test_read_order_is_stable_and_ascending_by_filename(tmp_path: Path) -> None:
    """Two reads of the same directory agree, and the order is by filename."""
    write_chat_file(tmp_path, "chat_c.json", a_chat("Caro"))
    write_chat_file(tmp_path, "chat_a.json", a_chat("Ana"))
    write_chat_file(tmp_path, "chat_b.json", a_chat("Beto"))

    first_pass = [chat["chat_id"] for chat in read_chat_files(tmp_path)]
    second_pass = [chat["chat_id"] for chat in read_chat_files(tmp_path)]

    expected = [
        pseudonymous_chat_id("Ana"),
        pseudonymous_chat_id("Beto"),
        pseudonymous_chat_id("Caro"),
    ]
    assert first_pass == expected
    assert second_pass == expected
