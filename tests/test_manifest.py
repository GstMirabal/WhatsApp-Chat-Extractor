"""The run manifest and the operator's chat index.

Two properties matter more than the rest and both are pinned here: a failure is
never recorded without a reason, and no real name reaches the manifest. The
second is the one that cannot be fixed after the fact — a name written to disk
has already been written.
"""

from __future__ import annotations

import json
from pathlib import Path

from whatsapp_chat_extractor.manifest import (
    MANIFEST_SCHEMA_VERSION,
    OUTCOME_EXPORTED,
    OUTCOME_FAILED,
    OUTCOME_SKIPPED,
    build_manifest,
    exported,
    failed,
    now,
    skipped,
    summarize,
    write_chat_index,
    write_manifest,
)
from whatsapp_chat_extractor.writers import pseudonymous_chat_id

ANA = pseudonymous_chat_id("Ana")
BETO = pseudonymous_chat_id("Beto")
CARO = pseudonymous_chat_id("Caro")


def a_run() -> list[dict]:
    return [
        exported(ANA, index=0, completeness="unproven", message_count=513, file="a.json"),
        failed(BETO, index=1, reason="Row 1 did not accept a click"),
        skipped(CARO, index=2, reason="Run aborted: session lost"),
    ]


# --- entries --------------------------------------------------------------


def test_an_exported_chat_records_its_completeness_and_file() -> None:
    entry = exported(ANA, index=0, completeness="truncated", message_count=7, file="a.json")
    assert entry["outcome"] == OUTCOME_EXPORTED
    assert entry["completeness"] == "truncated"
    assert entry["message_count"] == 7
    assert entry["file"] == "a.json"
    assert entry["reason"] == ""


def test_a_failure_always_carries_a_reason() -> None:
    """A failure with no reason is what the manifest exists to prevent."""
    assert failed(BETO, index=1, reason="")["reason"] == "no reason recorded"
    assert failed(BETO, index=1, reason="timed out")["reason"] == "timed out"


def test_a_skip_always_carries_a_reason() -> None:
    assert skipped(CARO, index=2, reason="")["reason"] == "not attempted"


def test_a_failed_chat_claims_no_completeness() -> None:
    """`unproven` on a chat that never exported would be a fabricated reading."""
    entry = failed(BETO, index=1, reason="timed out")
    assert entry["completeness"] == ""
    assert entry["message_count"] == 0
    assert entry["file"] == ""


def test_skipped_is_not_failed() -> None:
    """Nothing was tried, so nothing is known — a different statement."""
    assert skipped(CARO, index=2, reason="aborted")["outcome"] == OUTCOME_SKIPPED
    assert skipped(CARO, index=2, reason="aborted")["outcome"] != OUTCOME_FAILED


# --- summary --------------------------------------------------------------


def test_counts_cover_every_outcome_and_completeness() -> None:
    counts = summarize(a_run())
    assert counts[OUTCOME_EXPORTED] == 1
    assert counts[OUTCOME_FAILED] == 1
    assert counts[OUTCOME_SKIPPED] == 1
    assert counts["unproven"] == 1
    assert counts["messages"] == 513


def test_every_key_is_present_even_at_zero() -> None:
    """An absent key and a zero read the same to a person, differently to code."""
    counts = summarize([])
    for key in (OUTCOME_EXPORTED, OUTCOME_FAILED, OUTCOME_SKIPPED,
                "proven", "unproven", "truncated", "messages"):
        assert counts[key] == 0


# --- manifest -------------------------------------------------------------


def test_a_partial_enumeration_is_visible_in_the_manifest() -> None:
    """899 of 899 and 70 of 899 must not produce the same-looking record."""
    partial = build_manifest(
        a_run(), started_at=now(), chats_enumerated=70, enumeration_complete=False
    )
    assert partial["enumeration_complete"] is False
    assert partial["chats_enumerated"] == 70


def test_the_manifest_declares_its_schema() -> None:
    manifest = build_manifest(
        a_run(), started_at=now(), chats_enumerated=3, enumeration_complete=True
    )
    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION


def test_written_manifest_round_trips(tmp_path: Path) -> None:
    manifest = build_manifest(
        a_run(), started_at=now(), chats_enumerated=3, enumeration_complete=True
    )
    payload = json.loads(
        write_manifest(manifest, data_dir=tmp_path).read_text(encoding="utf-8")
    )
    assert payload["counts"][OUTCOME_EXPORTED] == 1
    assert len(payload["chats"]) == 3
    assert payload["chats"][1]["reason"] == "Row 1 did not accept a click"


def test_no_conversation_name_reaches_the_manifest(tmp_path: Path) -> None:
    """ADR-0001. The manifest is written on every run, including unattended ones."""
    manifest = build_manifest(
        a_run(), started_at=now(), chats_enumerated=3, enumeration_complete=True
    )
    text = write_manifest(manifest, data_dir=tmp_path).read_text(encoding="utf-8")
    for name in ("Ana", "Beto", "Caro"):
        assert name not in text
    assert ANA in text


def test_the_manifest_filename_carries_no_name(tmp_path: Path) -> None:
    manifest = build_manifest([], started_at=now(), chats_enumerated=0,
                              enumeration_complete=True)
    assert write_manifest(manifest, data_dir=tmp_path).name.startswith("run_manifest_")


# --- the chat index, the one file that holds names -------------------------


def test_the_index_maps_digests_back_to_titles(tmp_path: Path) -> None:
    path = write_chat_index({ANA: "Ana", BETO: "Beto"}, data_dir=tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload[ANA] == "Ana"
    assert path.name.startswith("chat_index_")


def test_the_index_is_a_separate_file_from_the_manifest(tmp_path: Path) -> None:
    """Deleting the names must not cost the record of what the run did."""
    manifest = build_manifest(a_run(), started_at=now(), chats_enumerated=3,
                              enumeration_complete=True)
    manifest_path = write_manifest(manifest, data_dir=tmp_path)
    index_path = write_chat_index({ANA: "Ana"}, data_dir=tmp_path)
    assert manifest_path != index_path
    index_path.unlink()
    assert manifest_path.exists()
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["chats"]


def test_writing_no_index_is_the_default_path(tmp_path: Path) -> None:
    """Nothing in building or writing a manifest creates an index."""
    manifest = build_manifest(a_run(), started_at=now(), chats_enumerated=3,
                              enumeration_complete=True)
    write_manifest(manifest, data_dir=tmp_path)
    assert not list(tmp_path.glob("chat_index_*.json"))
