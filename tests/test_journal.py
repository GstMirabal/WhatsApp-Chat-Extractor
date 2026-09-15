"""What survives a run that does not finish.

The journal exists for the crash `cmd_export_all` cannot currently survive: a
~15-hour run whose manifest is written only at the end. So the cases that matter
here are the damaged ones — a line cut mid-write, a file that never got past
being created — not the happy path.

No browser, no `data/`: every case writes into `tmp_path`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from whatsapp_chat_extractor import journal
from whatsapp_chat_extractor.journal import (
    JOURNAL_SCHEMA_VERSION,
    append_outcome,
    exported_chat_ids,
    journal_path,
    open_journal,
    read_journal,
    write_header,
)
from whatsapp_chat_extractor.manifest import exported, failed, skipped

RUN_ID = "20260902T090000Z"


def a_journal(tmp_path: Path, outcomes: list[dict]) -> Path:
    """Write a header and `outcomes`, and return the journal path."""
    handle = open_journal(RUN_ID, data_dir=tmp_path)
    try:
        write_header(
            handle, run_id=RUN_ID, started_at="2026-09-02T09:00:00Z",
            chats_enumerated=len(outcomes), enumeration="converged", sweeps=3,
        )
        for outcome in outcomes:
            append_outcome(handle, outcome)
    finally:
        handle.close()
    return journal_path(RUN_ID, data_dir=tmp_path)


def three_outcomes() -> list[dict]:
    return [
        exported("chat_aaa", index=0, completeness="unproven",
                 message_count=3, file="chat_aaa_x.json"),
        failed("chat_bbb", index=1, reason="was not found in the chat list"),
        skipped("chat_ccc", index=2, reason="beyond --limit"),
    ]


def test_a_header_and_its_outcomes_replay_in_the_order_written(
    tmp_path: Path,
) -> None:
    path = a_journal(tmp_path, three_outcomes())
    header, outcomes = read_journal(path)

    assert header is not None
    assert header["run_id"] == RUN_ID
    assert header["schema_version"] == JOURNAL_SCHEMA_VERSION
    assert header["chats_enumerated"] == 3
    assert header["enumeration"] == "converged"
    assert [o["chat_id"] for o in outcomes] == ["chat_aaa", "chat_bbb", "chat_ccc"]
    assert [o["outcome"] for o in outcomes] == ["exported", "failed", "skipped"]


def test_the_record_discriminator_does_not_leak_into_the_outcome(
    tmp_path: Path,
) -> None:
    """A replayed outcome must be what `manifest` produced, field for field."""
    original = three_outcomes()
    path = a_journal(tmp_path, original)
    _, outcomes = read_journal(path)

    assert outcomes[0] == original[0]
    assert "record" not in outcomes[0]


def test_a_journal_with_two_resume_headers_keeps_the_first(
    tmp_path: Path,
) -> None:
    """`--resume` writes a new header on each restart (T-8).

    `read_journal` must reconstruct the run's true start from the first
    header written, not the most recent resume's.
    """
    handle = open_journal(RUN_ID, data_dir=tmp_path)
    try:
        write_header(
            handle, run_id=RUN_ID, started_at="2026-09-02T09:00:00Z",
            chats_enumerated=3, enumeration="converged", sweeps=3,
        )
        append_outcome(handle, three_outcomes()[0])
    finally:
        handle.close()

    # A `--resume` pass reopens the journal in append mode and writes a
    # second header with a later `started_at`.
    resumed = open_journal(RUN_ID, data_dir=tmp_path)
    try:
        write_header(
            resumed, run_id=RUN_ID, started_at="2026-09-03T11:00:00Z",
            chats_enumerated=3, enumeration="converged", sweeps=1,
        )
        for outcome in three_outcomes()[1:]:
            append_outcome(resumed, outcome)
    finally:
        resumed.close()

    path = journal_path(RUN_ID, data_dir=tmp_path)
    header, outcomes = read_journal(path)

    assert header is not None
    assert header["started_at"] == "2026-09-02T09:00:00Z"
    assert [o["chat_id"] for o in outcomes] == ["chat_aaa", "chat_bbb", "chat_ccc"]


def test_a_final_line_torn_mid_character_is_discarded_not_fatal(
    tmp_path: Path,
) -> None:
    """The crash this module exists for: the process died mid-write.

    The tear is inside a multi-byte character, so decoding the file as one
    string would raise and lose every intact record before it.
    """
    path = a_journal(tmp_path, three_outcomes())
    torn = json.dumps(
        {"record": "outcome", "chat_id": "chat_ddd", "reason": "café"},
        ensure_ascii=False,
    ).encode("utf-8")
    # Cut inside the two-byte `é`, leaving a lone continuation byte.
    with path.open("ab") as handle:
        handle.write(torn[: torn.rindex(b"caf") + 4])

    header, outcomes = read_journal(path)

    assert header is not None
    assert [o["chat_id"] for o in outcomes] == ["chat_aaa", "chat_bbb", "chat_ccc"]


def test_a_final_line_cut_mid_json_is_discarded_too(tmp_path: Path) -> None:
    path = a_journal(tmp_path, three_outcomes())
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"record": "outcome", "chat_id": "chat_dd')

    _, outcomes = read_journal(path)

    assert len(outcomes) == 3


def test_a_broken_line_before_the_end_raises_rather_than_shortening_the_record(
    tmp_path: Path,
) -> None:
    """Damage after the write is a different failure from a crash during it.

    Silently returning the first two entries would report a run that stopped
    where it did not.
    """
    path = a_journal(tmp_path, three_outcomes())
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[2] = '{"record": "outcome", broken'
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="line 3 of 4"):
        read_journal(path)


def test_an_empty_file_reads_as_nothing_rather_than_raising(tmp_path: Path) -> None:
    """`open_journal` creates the file; a crash before the header leaves it empty."""
    handle = open_journal(RUN_ID, data_dir=tmp_path)
    handle.close()

    header, outcomes = read_journal(journal_path(RUN_ID, data_dir=tmp_path))

    assert header is None
    assert outcomes == []


def test_a_journal_that_was_never_created_reads_as_nothing(tmp_path: Path) -> None:
    header, outcomes = read_journal(journal_path("no-such-run", data_dir=tmp_path))

    assert header is None
    assert outcomes == []


def test_every_append_is_forced_to_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without `fsync` a power cut loses what a `kill -9` would have kept."""
    synced: list[int] = []
    real_fsync = os.fsync
    monkeypatch.setattr(
        journal.os, "fsync",
        lambda fd: (synced.append(fd), real_fsync(fd))[1],
    )

    a_journal(tmp_path, three_outcomes())

    # One header plus three outcomes.
    assert len(synced) == 4


def test_only_exported_chats_are_skipped_on_resume(tmp_path: Path) -> None:
    """A failure wrote no file, so it is retried; a skip was never attempted."""
    path = a_journal(tmp_path, three_outcomes())

    assert exported_chat_ids(path) == {"chat_aaa"}


def test_resuming_against_a_missing_journal_is_a_full_run_not_an_error(
    tmp_path: Path,
) -> None:
    assert exported_chat_ids(journal_path("no-such-run", data_dir=tmp_path)) == set()


def test_appending_extends_an_existing_journal_rather_than_erasing_it(
    tmp_path: Path,
) -> None:
    """Opened in append mode on purpose: a resume must not destroy the record."""
    a_journal(tmp_path, three_outcomes())
    handle = open_journal(RUN_ID, data_dir=tmp_path)
    try:
        append_outcome(
            handle,
            exported("chat_ddd", index=3, completeness="proven",
                     message_count=7, file="chat_ddd_x.json"),
        )
    finally:
        handle.close()

    _, outcomes = read_journal(journal_path(RUN_ID, data_dir=tmp_path))

    assert [o["chat_id"] for o in outcomes] == [
        "chat_aaa", "chat_bbb", "chat_ccc", "chat_ddd"
    ]


def test_the_journal_carries_no_conversation_title(tmp_path: Path) -> None:
    """`ADR-0001`: the only file allowed to hold real names is the chat index."""
    path = a_journal(tmp_path, three_outcomes())

    assert "Ana" not in path.read_text(encoding="utf-8")
    for outcome in read_journal(path)[1]:
        assert "title" not in outcome
