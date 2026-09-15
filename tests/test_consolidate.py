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
    CORPUS_SCHEMA_VERSION,
    RECORD_HEADER,
    build_header,
    read_chat_files,
    resolve_source_run,
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
    lines = out_path.read_text(encoding="utf-8").rstrip("\n").split("\n")

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
    lines = out_path.read_text(encoding="utf-8").rstrip("\n").split("\n")
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


def test_write_corpus_recomputes_chat_count_rather_than_trusting_the_header(
    tmp_path: Path,
) -> None:
    """A header built from a shorter list than the one actually written must
    not reach disk unreconciled (`§D2`) — `write_corpus` is authoritative on
    the count of what it writes, not the header's own claim.
    """
    stale_header = build_header([a_chat("Ana")], "run-1")
    assert stale_header["chat_count"] == 1
    real_body = [a_chat("Ana"), a_chat("Beto")]

    out_path = write_corpus(real_body, stale_header, tmp_path / "corpus.ndjson")
    lines = out_path.read_text(encoding="utf-8").rstrip("\n").split("\n")

    assert len(lines) == 3
    assert json.loads(lines[0])["chat_count"] == 2
    assert stale_header["chat_count"] == 1


def test_a_file_with_no_chat_id_raises_value_error_not_key_error(
    tmp_path: Path,
) -> None:
    """A malformed v6 file missing `chat_id` must hit this module's own
    `ValueError` abort contract — the only exception `cmd_consolidate`
    catches — not an uncaught `KeyError` from deeper in the read path.
    """
    write_chat_file(tmp_path, "chat_broken.json", {"schema_version": SCHEMA_VERSION})

    with pytest.raises(ValueError, match="chat_broken.json has no chat_id"):
        read_chat_files(tmp_path)


def test_build_header_carries_all_six_provenance_fields(tmp_path: Path) -> None:
    """Sprint 010 `T-2`: only `chat_count` and `chat_schema` were ever pinned
    by a test; the other four (`record`, `corpus_schema`, `source_run`,
    `generated_at`) were deletable from `build_header` with nothing noticing.
    """
    chats = [a_chat("Ana")]

    header = build_header(chats, "run-42")

    assert header["record"] == RECORD_HEADER
    assert header["corpus_schema"] == CORPUS_SCHEMA_VERSION
    assert header["chat_schema"] == SCHEMA_VERSION
    assert header["source_run"] == "run-42"
    assert header["chat_count"] == 1
    assert isinstance(header["generated_at"], str)
    assert header["generated_at"].endswith("Z")


def test_resolve_source_run_picks_the_lexicographically_newest_manifest(
    tmp_path: Path,
) -> None:
    """Sprint 010 `T-3`: `resolve_source_run` reads `manifests[-1]` after an
    ascending-name sort. Picking `manifests[0]` instead — the oldest — would
    have survived the suite before this test existed. Two manifest names are
    chosen so their sort order is unambiguous.
    """
    (tmp_path / "run_manifest_2026-01-01T000000Z-aaa.json").write_text("{}")
    (tmp_path / "run_manifest_2026-06-01T000000Z-zzz.json").write_text("{}")

    source_run = resolve_source_run(tmp_path, None)

    assert source_run == "2026-06-01T000000Z-zzz"


def test_resolve_source_run_from_manifest_accepts_a_path_never_written(
    tmp_path: Path,
) -> None:
    """Sprint 010 `T-7`: `resolve_source_run` never checks that `from_manifest`
    names a file that exists — it only parses the filename. A path to a run
    that never happened is accepted exactly like a real one, silently.
    """
    fabricated = tmp_path / "run_manifest_never-existed.json"
    assert not fabricated.exists()

    source_run = resolve_source_run(tmp_path, fabricated)

    assert source_run == "never-existed"


def test_a_legacy_chat_index_json_file_is_swept_by_the_unpinned_glob(
    tmp_path: Path,
) -> None:
    """Sprint 010 `T-4`: `CHAT_FILE_GLOB` (`chat_*.json`) has never been
    pinned against a filename that merely starts with `chat_` and ends
    `.json` without being a per-conversation export. Before Sprint 011 Block D
    moved the chat index to `chat_index_<run_id>.ndjson`, its predecessor
    wrote exactly that shape (`chat_index_<stamp>.json`) into the very
    directory `read_chat_files` scans. A file left over from a run made
    before that migration reproduces the collision: the glob matches it and
    `read_chat_files` aborts trying to read it as an export — loud, not
    silent, but never proven by a test until now.
    """
    write_chat_file(tmp_path, "chat_1.json", a_chat("Ana"))
    legacy_index = tmp_path / "chat_index_20260101T000000Z.json"
    legacy_index.write_text(
        json.dumps({"digest-1": "Ana"}, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="chat_index_20260101T000000Z.json"):
        read_chat_files(tmp_path)


def test_message_body_with_unicode_line_separators_does_not_corrupt_line_count(
    tmp_path: Path,
) -> None:
    """Regression pin for `F-1` (Sprint 010, `0e333b8`): the fix itself had no
    test of its own (Sprint 010 `T-6`). A body carrying U+2028/U+2029/U+0085
    is written unescaped because `write_corpus` serializes with
    `ensure_ascii=False`; counting the corpus with `str.splitlines()` — the
    self-inflicted defect `F-1` fixed — disagrees with the true
    `\\n`-delimited line count that `header["chat_count"]` promises.
    """
    tricky = a_chat("Ana")
    tricky["messages"][0]["body"] = "line1 line2 line3line4"
    write_chat_file(tmp_path, "chat_1.json", tricky)

    chats = read_chat_files(tmp_path)
    header = build_header(chats, "run-1")
    out_path = write_corpus(chats, header, tmp_path / "corpus.ndjson")
    raw = out_path.read_text(encoding="utf-8")
    correct_lines = raw.rstrip("\n").split("\n")

    assert len(correct_lines) == 2
    assert json.loads(correct_lines[0])["chat_count"] == 1
    assert len(raw.splitlines()) != len(correct_lines)
