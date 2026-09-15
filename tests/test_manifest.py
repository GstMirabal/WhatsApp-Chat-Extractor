"""The run manifest and the operator's chat index.

Two properties matter more than the rest and both are pinned here: a failure is
never recorded without a reason, and no real name reaches the manifest. The
second is the one that cannot be fixed after the fact — a name written to disk
has already been written.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from whatsapp_chat_extractor import manifest as manifest_module
from whatsapp_chat_extractor.journal import (
    append_outcome,
    journal_path,
    open_journal,
    read_journal,
    write_header,
)
from whatsapp_chat_extractor.manifest import (
    MANIFEST_SCHEMA_VERSION,
    OUTCOME_EXPORTED,
    OUTCOME_FAILED,
    OUTCOME_SKIPPED,
    append_chat_index_entry,
    build_manifest,
    chat_index_path,
    exported,
    failed,
    manifest_from_journal,
    now,
    open_chat_index_journal,
    skipped,
    summarize,
    write_manifest,
)
from whatsapp_chat_extractor.writers import pseudonymous_chat_id

ANA = pseudonymous_chat_id("Ana")
BETO = pseudonymous_chat_id("Beto")
CARO = pseudonymous_chat_id("Caro")
DORA = pseudonymous_chat_id("Dora")

RUN_ID = "20260902T090000Z"


def a_journal(
    tmp_path: Path,
    outcomes: list[dict],
    *,
    chats_enumerated: int,
    run_id: str = RUN_ID,
) -> Path:
    """Write a header and `outcomes` to a real journal, following `test_journal.py`.

    `chats_enumerated` is a caller-supplied argument, not `len(outcomes)`, so a
    journal that stops short of the full enumeration can be built on purpose.
    """
    handle = open_journal(run_id, data_dir=tmp_path)
    try:
        write_header(
            handle, run_id=run_id, started_at="2026-09-02T09:00:00Z",
            chats_enumerated=chats_enumerated, enumeration="unconverged", sweeps=1,
        )
        for outcome in outcomes:
            append_outcome(handle, outcome)
    finally:
        handle.close()
    return journal_path(run_id, data_dir=tmp_path)


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
        a_run(), started_at=now(), chats_enumerated=70,
        enumeration="truncated", sweeps=1,
    )
    assert partial["enumeration"] == "truncated"
    assert partial["sweeps"] == 1
    assert partial["chats_enumerated"] == 70


def test_the_manifest_declares_its_schema() -> None:
    manifest = build_manifest(
        a_run(), started_at=now(), chats_enumerated=3, enumeration="converged", sweeps=3
    )
    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    # Compared to the literal as well, following tests/test_writers.py: against
    # the constant alone, changing the constant changes the test with it and the
    # bump goes unnoticed. Gap F-2, found by mutation at the Phase 7 gate.
    assert manifest["schema_version"] == 2


def test_written_manifest_round_trips(tmp_path: Path) -> None:
    manifest = build_manifest(
        a_run(), started_at=now(), chats_enumerated=3, enumeration="converged", sweeps=3
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
        a_run(), started_at=now(), chats_enumerated=3, enumeration="converged", sweeps=3
    )
    text = write_manifest(manifest, data_dir=tmp_path).read_text(encoding="utf-8")
    for name in ("Ana", "Beto", "Caro"):
        assert name not in text
    assert ANA in text


def test_the_manifest_filename_carries_no_name(tmp_path: Path) -> None:
    manifest = build_manifest([], started_at=now(), chats_enumerated=0,
                              enumeration="converged", sweeps=3)
    assert write_manifest(manifest, data_dir=tmp_path).name.startswith("run_manifest_")


# --- the chat index, the one file that holds names -------------------------
#
# §D5: this file used to be written once, in a single batched call, at the
# end of a run — so a crash any time before that call lost every title the
# run had gathered. It is now append-only, mirroring `journal.py`'s own
# durability exactly, and the tests below pin that property rather than only
# the two functions in isolation.


def an_index(
    tmp_path: Path, entries: list[tuple[str, str]], *, run_id: str = RUN_ID
) -> Path:
    """Write `entries` to a real chat index, following `test_journal.py`."""
    handle = open_chat_index_journal(run_id, data_dir=tmp_path)
    try:
        for chat_id, title in entries:
            append_chat_index_entry(handle, chat_id, title)
    finally:
        handle.close()
    return chat_index_path(run_id, data_dir=tmp_path)


def read_index_lines(path: Path) -> list[dict]:
    """Every line of a chat index, independently parsed as JSON."""
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_the_index_maps_digests_back_to_titles(tmp_path: Path) -> None:
    path = an_index(tmp_path, [(ANA, "Ana"), (BETO, "Beto")])
    entries = read_index_lines(path)
    assert {(e["chat_id"], e["title"]) for e in entries} == {
        (ANA, "Ana"), (BETO, "Beto"),
    }
    assert path.name.startswith("chat_index_")
    assert path.name.endswith(".ndjson")


def test_each_title_is_its_own_line_not_one_batched_object(tmp_path: Path) -> None:
    """The defect this item closes: one JSON object could not lose half of
    itself to a crash. One line per title can — and does not, because each
    line is written, flushed and synced before the next title is read."""
    path = an_index(tmp_path, [(ANA, "Ana"), (BETO, "Beto")])
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == 2
    for line in lines:
        assert isinstance(json.loads(line), dict)


def test_the_index_is_a_separate_file_from_the_manifest(tmp_path: Path) -> None:
    """Deleting the names must not cost the record of what the run did."""
    manifest = build_manifest(a_run(), started_at=now(), chats_enumerated=3,
                              enumeration="converged", sweeps=3)
    manifest_path = write_manifest(manifest, data_dir=tmp_path)
    index_path = an_index(tmp_path, [(ANA, "Ana")])
    assert manifest_path != index_path
    index_path.unlink()
    assert manifest_path.exists()
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["chats"]


def test_writing_no_index_is_the_default_path(tmp_path: Path) -> None:
    """Nothing in building or writing a manifest creates an index."""
    manifest = build_manifest(a_run(), started_at=now(), chats_enumerated=3,
                              enumeration="converged", sweeps=3)
    write_manifest(manifest, data_dir=tmp_path)
    assert not list(tmp_path.glob("chat_index_*.ndjson"))


def test_no_conversation_name_reaches_the_index_filename(tmp_path: Path) -> None:
    """The name is inside the file, gated by `--write-index`; the filename
    itself must not leak it into a directory listing or a log line."""
    path = an_index(tmp_path, [(ANA, "Ana")])
    assert "Ana" not in path.name


def test_appending_extends_an_existing_index_rather_than_erasing_it(
    tmp_path: Path,
) -> None:
    """Opened in append mode on purpose: resuming a run with `--write-index`
    must not destroy the titles an earlier pass already discovered — the file
    itself is the fold, with no merge step needed (`§D5`)."""
    an_index(tmp_path, [(ANA, "Ana")])
    handle = open_chat_index_journal(RUN_ID, data_dir=tmp_path)
    try:
        append_chat_index_entry(handle, BETO, "Beto")
    finally:
        handle.close()

    entries = read_index_lines(chat_index_path(RUN_ID, data_dir=tmp_path))

    assert {e["chat_id"] for e in entries} == {ANA, BETO}


def test_every_index_append_is_forced_to_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without `fsync` a power cut loses what a `kill -9` would have kept —
    exactly the argument `journal.py`'s own equivalent test makes."""
    synced: list[int] = []
    real_fsync = os.fsync
    monkeypatch.setattr(
        manifest_module.os, "fsync",
        lambda fd: (synced.append(fd), real_fsync(fd))[1],
    )

    an_index(tmp_path, [(ANA, "Ana"), (BETO, "Beto")])

    assert len(synced) == 2


def test_a_mid_run_crash_leaves_every_title_written_so_far_intact(
    tmp_path: Path,
) -> None:
    """`§D5`'s actual property, not just the two functions in isolation: a run
    that dies partway through must not lose the titles it had already
    discovered.

    Only two of three conversations' titles are ever appended — the third is
    never reached, as if the process died right after the second and before
    the third chat opened. The handle is never closed cleanly either, because
    a `kill -9` would not run a `finally` block. Nothing simulates a batched
    final write here, because the property under test is that no such write
    is needed: both titles already reached disk when they were discovered.
    """
    handle = open_chat_index_journal(RUN_ID, data_dir=tmp_path)
    append_chat_index_entry(handle, ANA, "Ana")
    append_chat_index_entry(handle, BETO, "Beto")

    entries = read_index_lines(chat_index_path(RUN_ID, data_dir=tmp_path))

    assert {(e["chat_id"], e["title"]) for e in entries} == {
        (ANA, "Ana"), (BETO, "Beto"),
    }
    assert CARO not in {e["chat_id"] for e in entries}


# --- reconstruction from a partial journal ---------------------------------


def test_manifest_from_journal_marks_unreached_conversations_skipped(
    tmp_path: Path,
) -> None:
    """A journal that stops before the enumeration finished must not drop the rest."""
    path = a_journal(
        tmp_path,
        [
            exported(ANA, index=0, completeness="unproven", message_count=5, file="a.json"),
            failed(BETO, index=1, reason="Row 1 did not accept a click"),
        ],
        chats_enumerated=3,
    )
    header, outcomes = read_journal(path)
    enumerated_refs = [
        {"chat_id": ANA, "index": 0},
        {"chat_id": BETO, "index": 1},
        {"chat_id": CARO, "index": 2},
    ]

    manifest = manifest_from_journal(header, outcomes, enumerated_refs)

    # The two recorded outcomes are carried over untouched and in order.
    assert manifest["chats"][0] == outcomes[0]
    assert manifest["chats"][1] == outcomes[1]
    reconstructed = manifest["chats"][2]
    assert reconstructed["chat_id"] == CARO
    assert reconstructed["outcome"] == OUTCOME_SKIPPED
    assert reconstructed["reason"] == "run ended before this conversation"
    assert reconstructed["index"] == 2


def test_reconstructed_skip_reason_is_distinct_from_a_limit_skip(
    tmp_path: Path,
) -> None:
    """A `--limit` skip and an interrupted-run skip must stay tellable apart."""
    path = a_journal(
        tmp_path,
        [skipped(ANA, index=0, reason="beyond --limit")],
        chats_enumerated=2,
    )
    header, outcomes = read_journal(path)
    enumerated_refs = [
        {"chat_id": ANA, "index": 0},
        {"chat_id": BETO, "index": 1},
    ]

    manifest = manifest_from_journal(header, outcomes, enumerated_refs)

    reasons = {chat["chat_id"]: chat["reason"] for chat in manifest["chats"]}
    assert reasons[ANA] == "beyond --limit"
    assert reasons[BETO] == "run ended before this conversation"


def test_manifest_from_journal_carries_the_header_fields_through(
    tmp_path: Path,
) -> None:
    """The reconstructed manifest reports the run the journal actually recorded."""
    path = a_journal(tmp_path, [], chats_enumerated=1)
    header, outcomes = read_journal(path)

    manifest = manifest_from_journal(header, outcomes, [{"chat_id": ANA, "index": 0}])

    assert manifest["started_at"] == "2026-09-02T09:00:00Z"
    assert manifest["chats_enumerated"] == 1
    assert manifest["enumeration"] == "unconverged"
    assert manifest["sweeps"] == 1


def test_manifest_from_journal_refuses_a_missing_header() -> None:
    """Without a header, `started_at`/`enumeration`/`sweeps` cannot be fabricated."""
    with pytest.raises(ValueError, match="journal header"):
        manifest_from_journal(None, [], [])


# --- run_id names the written files -----------------------------------------


def test_explicit_run_id_names_the_manifest_file(tmp_path: Path) -> None:
    manifest = build_manifest(a_run(), started_at=now(), chats_enumerated=3,
                              enumeration="converged", sweeps=3)

    path = write_manifest(manifest, data_dir=tmp_path, run_id=RUN_ID)

    assert path.name == f"run_manifest_{RUN_ID}.json"


def test_explicit_run_id_names_the_chat_index_file(tmp_path: Path) -> None:
    path = an_index(tmp_path, [(ANA, "Ana")], run_id=RUN_ID)

    assert path.name == f"chat_index_{RUN_ID}.ndjson"


def test_run_id_ties_the_manifest_and_the_index_to_the_same_run(
    tmp_path: Path,
) -> None:
    """Both files one run produces must share the identity, not derive their own."""
    manifest = build_manifest(a_run(), started_at=now(), chats_enumerated=3,
                              enumeration="converged", sweeps=3)

    manifest_path = write_manifest(manifest, data_dir=tmp_path, run_id=RUN_ID)
    index_path = an_index(tmp_path, [(ANA, "Ana")], run_id=RUN_ID)

    assert manifest_path.stem == f"run_manifest_{RUN_ID}"
    assert index_path.stem == f"chat_index_{RUN_ID}"


# --- summarize sees the reconstructed skips ---------------------------------


def test_summarize_counts_the_reconstructed_skips(tmp_path: Path) -> None:
    """A reconstructed skip must be visible in the summary, not silently dropped."""
    path = a_journal(
        tmp_path,
        [exported(ANA, index=0, completeness="proven", message_count=5, file="a.json")],
        chats_enumerated=3,
    )
    header, outcomes = read_journal(path)
    enumerated_refs = [
        {"chat_id": ANA, "index": 0},
        {"chat_id": BETO, "index": 1},
        {"chat_id": CARO, "index": 2},
    ]

    manifest = manifest_from_journal(header, outcomes, enumerated_refs)

    assert manifest["counts"][OUTCOME_SKIPPED] == 2
    assert manifest["counts"][OUTCOME_EXPORTED] == 1
    # Independently, from the raw entries — not just trusting `build_manifest`'s
    # own call to `summarize`.
    assert summarize(manifest["chats"])[OUTCOME_SKIPPED] == 2


def test_a_fully_reached_journal_reconstructs_no_skips(tmp_path: Path) -> None:
    """When the journal already covers every enumerated chat, nothing is invented."""
    path = a_journal(
        tmp_path,
        [
            exported(ANA, index=0, completeness="proven", message_count=5, file="a.json"),
            exported(DORA, index=1, completeness="proven", message_count=2, file="d.json"),
        ],
        chats_enumerated=2,
    )
    header, outcomes = read_journal(path)
    enumerated_refs = [{"chat_id": ANA, "index": 0}, {"chat_id": DORA, "index": 1}]

    manifest = manifest_from_journal(header, outcomes, enumerated_refs)

    assert manifest["counts"][OUTCOME_SKIPPED] == 0
    assert len(manifest["chats"]) == 2
