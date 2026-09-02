"""What a whole-account export run did, chat by chat.

A dump of unknown completeness is not usable (`ADR-0002` P3). With 899
conversations measured in this account, a run is long enough that "it finished"
is not an answer: the manifest states the outcome of every conversation the
sweep found, including the ones that failed and why.

**Two files, deliberately.** The roadmap asks for an index the operator can map
back to real conversations, and mapping back means storing `title → chat_id`.
`ADR-0001` forbids names in `data/` by default, so the mapping is a separate
file behind an explicit flag rather than a column in the manifest:

===================================  ==========================================
`data/run_manifest_<stamp>.json`     Outcomes. **No titles.** Always written
`data/chat_index_<stamp>.json`       `chat_id` → title. The only file with names
===================================  ==========================================

Both live under gitignored `data/`. They are separate so the operator can delete
the index without losing the record of what the run did.

**Resume rebuilds the manifest from the journal; it is no longer unbuilt.**
`journal.py` records each conversation's outcome durably as a run goes, so a
run that dies before reaching this module's own output still leaves something
to rebuild from. `manifest_from_journal` replays a journal's header and
outcomes against the conversations a later enumeration found, and marks every
enumerated `chat_id` the journal never reached `skipped`, with reason `run
ended before this conversation` — distinguishable from a skip produced by
`--limit`, and honest about a run that was interrupted rather than finished.
`run_id`, minted once when a run starts, threads through `write_manifest` and
`write_chat_index` so every file one run produces shares that identity instead
of each deriving its own timestamp.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

from whatsapp_chat_extractor.writers import DEFAULT_DATA_DIR

if TYPE_CHECKING:
    from whatsapp_chat_extractor.chat_list import ChatRef
    from whatsapp_chat_extractor.journal import JournalHeader

logger = logging.getLogger(__name__)

MANIFEST_SCHEMA_VERSION = 2

OUTCOME_EXPORTED = "exported"
OUTCOME_FAILED = "failed"
# Enumerated, never attempted: the run ended before reaching it. Distinct from
# `failed`, because nothing was tried and nothing is known about it.
OUTCOME_SKIPPED = "skipped"


class ChatOutcome(TypedDict):
    """What happened to one conversation during a run."""

    chat_id: str
    index: int
    outcome: str
    reason: str
    completeness: str
    message_count: int
    file: str


class RunManifest(TypedDict):
    """The record of one whole-account export run."""

    schema_version: int
    started_at: str
    finished_at: str
    chats_enumerated: int
    enumeration: str
    sweeps: int
    counts: dict[str, int]
    chats: list[ChatOutcome]


def now() -> str:
    """UTC timestamp in the format the export payload already uses."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def exported(
    chat_id: str, *, index: int, completeness: str, message_count: int, file: str
) -> ChatOutcome:
    """Record a conversation that was exported.

    Args:
        chat_id: Pseudonymous identity of the conversation.
        index: Its position in the enumerated list.
        completeness: `proven`, `unproven` or `truncated` (ADR-0004).
        message_count: Messages written.
        file: Name of the export file, not its full path.

    Returns:
        ChatOutcome: The entry to add to the manifest.
    """
    return {
        "chat_id": chat_id, "index": index, "outcome": OUTCOME_EXPORTED,
        "reason": "", "completeness": completeness,
        "message_count": message_count, "file": file,
    }


def failed(chat_id: str, *, index: int, reason: str) -> ChatOutcome:
    """Record a conversation that was attempted and did not export.

    Args:
        chat_id: Pseudonymous identity of the conversation.
        index: Its position in the enumerated list.
        reason: What went wrong, in one line. Never empty — a failure with no
            reason is the thing this manifest exists to prevent.

    Returns:
        ChatOutcome: The entry to add to the manifest.
    """
    return {
        "chat_id": chat_id, "index": index, "outcome": OUTCOME_FAILED,
        "reason": reason or "no reason recorded", "completeness": "",
        "message_count": 0, "file": "",
    }


def skipped(chat_id: str, *, index: int, reason: str) -> ChatOutcome:
    """Record a conversation the run never attempted.

    Args:
        chat_id: Pseudonymous identity of the conversation.
        index: Its position in the enumerated list.
        reason: Why it was not attempted — the run aborted, or a limit was hit.

    Returns:
        ChatOutcome: The entry to add to the manifest.
    """
    return {
        "chat_id": chat_id, "index": index, "outcome": OUTCOME_SKIPPED,
        "reason": reason or "not attempted", "completeness": "",
        "message_count": 0, "file": "",
    }


def summarize(chats: list[ChatOutcome]) -> dict[str, int]:
    """Counts per outcome and per completeness value.

    Every key is present with a zero rather than omitted: an absent key and a
    zero read the same to a person and differently to a program.

    Args:
        chats: Every entry in the run.

    Returns:
        dict[str, int]: Outcome counts, then completeness counts for the
            conversations that were exported.
    """
    counts = {
        OUTCOME_EXPORTED: 0, OUTCOME_FAILED: 0, OUTCOME_SKIPPED: 0,
        "proven": 0, "unproven": 0, "truncated": 0, "messages": 0,
    }
    for chat in chats:
        counts[chat["outcome"]] = counts.get(chat["outcome"], 0) + 1
        counts["messages"] += chat["message_count"]
        if chat["completeness"]:
            counts[chat["completeness"]] = counts.get(chat["completeness"], 0) + 1
    return counts


def build_manifest(
    chats: list[ChatOutcome],
    *,
    started_at: str,
    chats_enumerated: int,
    enumeration: str,
    sweeps: int,
) -> RunManifest:
    """Assemble the run record.

    Args:
        chats: One entry per conversation the run knows about.
        started_at: When the run began, from :func:`now`.
        chats_enumerated: How many conversations the enumeration found.
        enumeration: `ADR-0005`'s verdict — `converged`, `unconverged` or
            `truncated`. It replaces a boolean that reported success for a run
            which had lost 43 of 899 conversations, because the pane foot was
            reached while the list moved underneath the sweep.
        sweeps: How many full sweeps ran. It makes `converged` auditable from
            the file rather than taken on trust.

    Returns:
        RunManifest: Ready for JSON serialization.
    """
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "started_at": started_at,
        "finished_at": now(),
        "chats_enumerated": chats_enumerated,
        "enumeration": enumeration,
        "sweeps": sweeps,
        "counts": summarize(chats),
        "chats": chats,
    }


def _with_reconstructed_skips(
    outcomes: list[ChatOutcome],
    enumerated_refs: list[ChatRef],
) -> list[ChatOutcome]:
    """Append a `skipped` entry for every enumerated chat the journal missed.

    The journal's own `outcomes` come first, unchanged and in the order they
    were written. Reconstructed skips are appended after them, in
    `enumerated_refs` enumeration order — not interleaved at each gap's
    position. That ordering is a deliberate, recorded caveat (`KI-009-F`),
    not an oversight: changing it is a behaviour change, not a cleanup.

    Args:
        outcomes: Outcomes already in the journal, in the order they were
            written.
        enumerated_refs: Every conversation the run's enumeration found, in
            enumeration order.

    Returns:
        list[ChatOutcome]: The journal's outcomes followed by a `skipped`
            entry, reason `run ended before this conversation`, for every
            enumerated `chat_id` absent from `outcomes`.
    """
    recorded_ids = {outcome["chat_id"] for outcome in outcomes}
    reconstructed = list(outcomes)
    for ref in enumerated_refs:
        if ref["chat_id"] not in recorded_ids:
            reconstructed.append(
                skipped(
                    ref["chat_id"],
                    index=ref["index"],
                    reason="run ended before this conversation",
                )
            )
    return reconstructed


def manifest_from_journal(
    header: JournalHeader | None,
    outcomes: list[ChatOutcome],
    enumerated_refs: list[ChatRef],
) -> RunManifest:
    """Rebuild a run manifest from its journal, without rerunning the export.

    Every conversation `enumerated_refs` names that the journal's own
    `outcomes` never reached is recorded as `skipped`, with reason `run ended
    before this conversation` — distinct from a skip produced by `--limit`,
    which the journal would already carry as an outcome.

    Args:
        header: The journal's header record, from :func:`journal.read_journal`.
        outcomes: Outcomes already in the journal, in the order they were
            written.
        enumerated_refs: Every conversation the run's enumeration found, in
            enumeration order.

    Returns:
        RunManifest: Reconstructed from the journal's own `started_at`,
            `chats_enumerated`, `enumeration` and `sweeps`, with the journal's
            outcomes followed by a `skipped` entry for every enumerated
            `chat_id` the journal has no outcome for.

    Raises:
        ValueError: If `header` is `None`. Without it, `started_at`,
            `chats_enumerated`, `enumeration` and `sweeps` are unknown, and
            fabricating them would misstate a run this module has no record
            of ever starting.
    """
    if header is None:
        raise ValueError(
            "cannot reconstruct a manifest without a journal header: "
            "started_at, enumeration and sweeps are unknown"
        )
    reconstructed = _with_reconstructed_skips(outcomes, enumerated_refs)
    return build_manifest(
        reconstructed,
        started_at=header["started_at"],
        chats_enumerated=header["chats_enumerated"],
        enumeration=header["enumeration"],
        sweeps=header["sweeps"],
    )


def write_manifest(
    manifest: RunManifest, data_dir: Path | None = None, *, run_id: str | None = None
) -> Path:
    """Write the run manifest and return its path.

    Args:
        manifest: Payload from :func:`build_manifest`.
        data_dir: Destination root (default ``data/``).
        run_id: Identity minted once at the start of the run (`journal.py`),
            so this file's name matches the journal it was built from. Falls
            back to a fresh UTC timestamp when the caller has none.

    Returns:
        Path: The file written.

    Raises:
        OSError: If the directory or file cannot be written.
    """
    root = data_dir or DEFAULT_DATA_DIR
    root.mkdir(parents=True, exist_ok=True)
    stamp = run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = root / f"run_manifest_{stamp}.json"
    payload: dict[str, Any] = dict(manifest)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    counts = manifest["counts"]
    logger.info(
        "Manifest at %s — %s exported, %s failed, %s skipped of %s enumerated",
        path, counts[OUTCOME_EXPORTED], counts[OUTCOME_FAILED],
        counts[OUTCOME_SKIPPED], manifest["chats_enumerated"],
    )
    return path


def write_chat_index(
    index: dict[str, str], data_dir: Path | None = None, *, run_id: str | None = None
) -> Path:
    """Write the `chat_id` → title map and return its path.

    **This is the only file this project writes that contains real names.** It
    exists because a pseudonymous corpus the operator cannot map back to a
    conversation is not usable for review, and it is a separate file — never a
    column in the manifest — so deleting it costs nothing else.

    Callers must not invoke this unless the operator asked for it explicitly.

    Args:
        index: Digest to title, as read during the run.
        data_dir: Destination root (default ``data/``).
        run_id: Identity minted once at the start of the run (`journal.py`),
            so this file's name matches the run's manifest. Falls back to a
            fresh UTC timestamp when the caller has none.

    Returns:
        Path: The file written.

    Raises:
        OSError: If the directory or file cannot be written.
    """
    root = data_dir or DEFAULT_DATA_DIR
    root.mkdir(parents=True, exist_ok=True)
    stamp = run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = root / f"chat_index_{stamp}.json"
    path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # The count, never the names: this log line reaches terminals and CI output.
    logger.warning(
        "Wrote %s with %s real conversation names to %s. Delete it when the "
        "mapping is no longer needed.", path.name, len(index), root,
    )
    return path
