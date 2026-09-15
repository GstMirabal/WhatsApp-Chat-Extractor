"""Append-only record of a run, written while the run is still going.

`manifest.py` writes the outcome of every conversation, but only once the whole
sweep has returned. A run over 910 conversations takes ~15 hours, so "once it
returns" is a promise the process may not live to keep: a crash at hour 12
leaves the exported files on disk with nothing saying which conversation each
one is, which failed, or how many were never attempted.

This module is the record that survives that. One line per conversation, written
as it happens.

**NDJSON rather than rewriting the manifest.** Rewriting the whole manifest after
each conversation costs 414.505 entry-writes over a run
(`python3 -c "print(sum(range(1, 911)))"`), and — the part that actually matters
— `Path.write_text` truncates before it writes, so a crash during rewrite 700
empties the one file holding the record. An append cannot destroy what is
already on disk, and a crash mid-line leaves a partial final line that
:func:`read_journal` discards while keeping the 699 before it.

**`fsync` on every append.** Without it a `kill -9` still keeps the data — the
bytes are in the operating system's buffer — but a power cut or a kernel panic
does not. At ~60 seconds per conversation, 910 `fsync` calls are free.

The journal carries no conversation titles. `ADR-0001` keeps real names out of
`data/` by default, and the `chat_id` → title index stays the separate,
flag-gated file `manifest.write_chat_index` already writes.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO, TypedDict

from whatsapp_chat_extractor.writers import DEFAULT_DATA_DIR

if TYPE_CHECKING:
    from whatsapp_chat_extractor.manifest import ChatOutcome

logger = logging.getLogger(__name__)

JOURNAL_SCHEMA_VERSION = 1

# Every line carries this key, so a reader never has to infer a record's kind
# from which fields happen to be present.
RECORD_HEADER = "header"
RECORD_OUTCOME = "outcome"


class JournalHeader(TypedDict):
    """What the run knew about itself before it opened the first conversation."""

    record: str
    schema_version: int
    run_id: str
    started_at: str
    chats_enumerated: int
    enumeration: str
    sweeps: int


def journal_path(run_id: str, data_dir: Path | None = None) -> Path:
    """Where the journal for one run lives.

    Args:
        run_id: Identity minted once at the start of the run.
        data_dir: Destination root (default ``data/``).

    Returns:
        Path: The journal file, which may not exist yet.
    """
    root = data_dir or DEFAULT_DATA_DIR
    return root / f"run_journal_{run_id}.ndjson"


def open_journal(run_id: str, data_dir: Path | None = None) -> TextIO:
    """Open the run's journal for appending, creating the directory if needed.

    Opened in append mode rather than write mode so that resuming a run against
    an existing journal extends the record instead of erasing it.

    Args:
        run_id: Identity minted once at the start of the run.
        data_dir: Destination root (default ``data/``).

    Returns:
        TextIO: Handle the caller must close.

    Raises:
        OSError: If the directory or file cannot be opened.
    """
    root = data_dir or DEFAULT_DATA_DIR
    root.mkdir(parents=True, exist_ok=True)
    path = journal_path(run_id, data_dir)
    logger.info("Journal at %s", path)
    return path.open("a", encoding="utf-8")


def _append_record(handle: TextIO, payload: dict[str, Any]) -> None:
    """Write one JSON record as a line and force it to disk.

    Args:
        handle: Journal handle from :func:`open_journal`.
        payload: The record. Serialized on a single line — a newline inside it
            would split one record into two unparseable ones.

    Raises:
        OSError: If the write or the sync fails.
    """
    handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    handle.flush()
    os.fsync(handle.fileno())


def write_header(
    handle: TextIO,
    *,
    run_id: str,
    started_at: str,
    chats_enumerated: int,
    enumeration: str,
    sweeps: int,
) -> None:
    """Record what the enumeration found, before the first conversation opens.

    Written at that exact point on purpose: `chats_enumerated` is what makes a
    reconstructed manifest able to say how many conversations were never
    attempted, and a header written at the end would never exist for the runs
    this module is for.

    Args:
        handle: Journal handle from :func:`open_journal`.
        run_id: Identity minted once at the start of the run.
        started_at: When the run began, from ``manifest.now``.
        chats_enumerated: How many conversations the sweep found.
        enumeration: `ADR-0005`'s verdict — `converged`, `unconverged` or
            `truncated`.
        sweeps: How many full sweeps ran.

    Raises:
        OSError: If the write or the sync fails.
    """
    header: JournalHeader = {
        "record": RECORD_HEADER,
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "run_id": run_id,
        "started_at": started_at,
        "chats_enumerated": chats_enumerated,
        "enumeration": enumeration,
        "sweeps": sweeps,
    }
    _append_record(handle, dict(header))


def append_outcome(handle: TextIO, outcome: ChatOutcome) -> None:
    """Record the outcome of one conversation, durably, before the next opens.

    Args:
        handle: Journal handle from :func:`open_journal`.
        outcome: Entry from ``manifest.exported``, ``failed`` or ``skipped``.

    Raises:
        OSError: If the write or the sync fails.
    """
    payload: dict[str, Any] = {"record": RECORD_OUTCOME, **outcome}
    _append_record(handle, payload)


def _decode_line(chunk: bytes) -> dict[str, Any] | None:
    """One journal line as a record, or None when it is not one.

    Decoding is per line rather than over the whole file because a crash can cut
    a line mid-character: `bytes.decode` over the file would raise and lose
    every valid line before the break.

    Args:
        chunk: The raw line, without its newline.

    Returns:
        dict[str, Any] | None: The record, or None if the bytes are not valid
            UTF-8, not valid JSON, or not a JSON object.
    """
    try:
        text = chunk.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not text.strip():
        return None
    try:
        record = json.loads(text)
    except json.JSONDecodeError:
        return None
    return record if isinstance(record, dict) else None


def read_journal(path: Path) -> tuple[JournalHeader | None, list[ChatOutcome]]:
    """Replay a journal, tolerating a crash in its final line and nothing else.

    A partial last line is the expected shape of an interrupted run, so it is
    dropped with a warning. A broken line anywhere *else* is corruption of a
    different kind — it means a record was damaged after it was written — and
    raises rather than silently shortening the record of the run.

    Args:
        path: Journal file, from :func:`journal_path`.

    Returns:
        tuple: The header (None when the file is absent or empty) and the
            outcomes in the order they were written.

    Raises:
        ValueError: If a line other than the last one cannot be read as a
            record.
        OSError: If the file cannot be read.
    """
    if not path.is_file():
        return None, []
    chunks = [chunk for chunk in path.read_bytes().split(b"\n") if chunk.strip()]
    header: JournalHeader | None = None
    outcomes: list[ChatOutcome] = []
    for number, chunk in enumerate(chunks, start=1):
        record = _decode_line(chunk)
        if record is None:
            _reject_or_warn(path, number, len(chunks))
            break
        if record.get("record") == RECORD_HEADER:
            header = header if header is not None else record  # type: ignore[assignment]
            continue
        outcomes.append(_as_outcome(record))
    return header, outcomes


def _reject_or_warn(path: Path, number: int, total: int) -> None:
    """Warn on a torn final line; raise on a broken one anywhere else.

    Args:
        path: The journal being read, named in both messages.
        number: 1-based line number that failed to decode.
        total: How many non-blank lines the file holds.

    Raises:
        ValueError: When the failing line is not the last one.
    """
    if number != total:
        raise ValueError(
            f"{path}: line {number} of {total} is not a readable record. Only a "
            "torn final line is tolerated; a broken line before the end means "
            "the journal was damaged after it was written."
        )
    logger.warning(
        "%s: discarding torn final line %s — the run was interrupted mid-write. "
        "The %s record(s) before it are intact.", path, number, number - 1,
    )


def _as_outcome(record: dict[str, Any]) -> ChatOutcome:
    """Strip the record discriminator, leaving the outcome as the manifest wants it.

    Args:
        record: A decoded outcome line.

    Returns:
        ChatOutcome: The same entry ``manifest.exported`` and friends produced.
    """
    outcome = {key: value for key, value in record.items() if key != "record"}
    return outcome  # type: ignore[return-value]


def exported_chat_ids(path: Path) -> set[str]:
    """Which conversations a previous run finished, so a resume can skip them.

    Only `exported` counts. A `failed` conversation is retried because nothing
    was written for it, and a `skipped` one was never attempted at all.

    Args:
        path: Journal file, from :func:`journal_path`.

    Returns:
        set[str]: Pseudonymous ids already exported. Empty when the journal is
            absent, which makes a resume against a missing journal a full run
            rather than an error.

    Raises:
        ValueError: If the journal is damaged before its final line.
    """
    _, outcomes = read_journal(path)
    return {
        outcome["chat_id"] for outcome in outcomes if outcome["outcome"] == "exported"
    }
