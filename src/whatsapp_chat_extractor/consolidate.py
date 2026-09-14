"""Join the per-conversation ``data/chat_*.json`` files into one NDJSON corpus.

The export run leaves one file per conversation (`writers.write_chat_export`).
A consumer of the corpus — the `ADR-0001 §2` "external AI / learning systems
read the JSON" case — otherwise has to open every one of them and union the set
by hand. This module produces the single artefact instead: a provenance header
line followed by one line per conversation, each carrying the schema v6 export
verbatim.

Consolidation is a union, never a transform (`ADR-0007` D3): no field is
flattened, dropped or recomputed, and the pseudonymous `chat_id` is passed
through untouched (`ADR-0001`). A `chat_id` that appears in two input files is a
conflict the operator must resolve, so it aborts with a named error rather than
being silently de-duplicated (`§D5`). An input that is not schema v6 aborts the
same way (`§D6`).

The module imports no browser: reading JSON files and writing one is work a
machine without Chromium must still be able to do (`§D4`).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from whatsapp_chat_extractor.writers import SCHEMA_VERSION

logger = logging.getLogger(__name__)

CORPUS_SCHEMA_VERSION = 1

# Glob for the per-conversation export files this module consolidates.
CHAT_FILE_GLOB = "chat_*.json"
# Glob for the run manifests `resolve_source_run` reads a run id from.
MANIFEST_FILE_GLOB = "run_manifest_*.json"
MANIFEST_FILE_PREFIX = "run_manifest_"
# Returned by `resolve_source_run` when no manifest identifies the run.
UNKNOWN_SOURCE_RUN = "unknown"

# Discriminator on the corpus header line, matching `journal.RECORD_HEADER`.
RECORD_HEADER = "header"


def _utc_now_iso() -> str:
    """The current UTC instant as an ISO 8601 string with a ``Z`` suffix.

    Returns:
        str: A stamp such as ``2026-09-10T12:00:00Z``, in the exact format the
        export payload and the run manifest already use.
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_chat_file(path: Path) -> dict:
    """Load one ``chat_*.json`` file and reject it when it is not schema v6.

    Args:
        path: The export file to read.

    Returns:
        dict: The parsed export, with every field the file carried.

    Raises:
        ValueError: If the file's ``schema_version`` is not
            ``writers.SCHEMA_VERSION``, or if the file has no ``chat_id``.
        OSError: If the file cannot be read.
    """
    with path.open(encoding="utf-8") as handle:
        chat = json.load(handle)
    schema = chat.get("schema_version")
    if schema != SCHEMA_VERSION:
        raise ValueError(
            f"{path.name} is schema {schema}, expected {SCHEMA_VERSION}"
        )
    if "chat_id" not in chat:
        raise ValueError(f"{path.name} has no chat_id")
    return chat


def _register_chat_id(chat_id: str, filename: str, seen: dict[str, str]) -> None:
    """Record ``chat_id`` as seen, aborting when another file already carried it.

    Args:
        chat_id: The pseudonymous identifier read from the current file.
        filename: The current file's name, for the error message.
        seen: Map of already-seen ``chat_id`` to the file it first appeared in.
            Mutated in place.

    Raises:
        ValueError: If ``chat_id`` is already in ``seen`` — the conflict the
            operator has to resolve by deleting the wrong file (`§D5`).
    """
    if chat_id in seen:
        raise ValueError(
            f"duplicate chat_id {chat_id} in {seen[chat_id]} and {filename}"
        )
    seen[chat_id] = filename


def read_chat_files(data_dir: Path) -> list[dict]:
    """Load every ``chat_*.json`` under ``data_dir`` in a stable order.

    Files are read in ascending filename order so the corpus body is
    reproducible between runs.

    Args:
        data_dir: Directory holding the per-conversation export files.

    Returns:
        list[dict]: One parsed export per file, in filename order, each with
        every field the file carried.

    Raises:
        ValueError: If two files carry the same ``chat_id`` (`§D5`), or if a
            file's ``schema_version`` is not ``writers.SCHEMA_VERSION`` (`§D6`).
        OSError: If ``data_dir`` or one of its files cannot be read.
    """
    paths = sorted(data_dir.glob(CHAT_FILE_GLOB), key=lambda path: path.name)
    chats: list[dict] = []
    seen: dict[str, str] = {}
    for path in paths:
        chat = _load_chat_file(path)
        _register_chat_id(chat["chat_id"], path.name, seen)
        chats.append(chat)
    return chats


def _run_id_from_manifest_name(path: Path) -> str:
    """Extract the run id a manifest filename carries.

    The run id is not stored inside the manifest JSON; it is the variable part
    of the ``run_manifest_<run_id>.json`` name (`manifest.write_manifest`).

    Args:
        path: A ``run_manifest_*.json`` path.

    Returns:
        str: The run id, or the whole stem if the name lacks the expected
        prefix.
    """
    stem = path.stem
    if stem.startswith(MANIFEST_FILE_PREFIX):
        return stem[len(MANIFEST_FILE_PREFIX):]
    return stem


def resolve_source_run(data_dir: Path, from_manifest: Path | None) -> str:
    """Decide which run id the corpus header should credit as its source.

    Args:
        data_dir: Directory scanned for ``run_manifest_*.json`` when
            ``from_manifest`` is not given.
        from_manifest: An explicit manifest path. When provided, its filename
            supplies the run id and ``data_dir`` is not scanned.

    Returns:
        str: The run id from ``from_manifest`` if given; otherwise the run id
        of the most recent ``run_manifest_*.json`` under ``data_dir`` by
        filename; otherwise ``"unknown"``.
    """
    if from_manifest is not None:
        return _run_id_from_manifest_name(from_manifest)
    manifests = sorted(
        data_dir.glob(MANIFEST_FILE_GLOB), key=lambda path: path.name
    )
    if manifests:
        return _run_id_from_manifest_name(manifests[-1])
    return UNKNOWN_SOURCE_RUN


def build_header(chats: list[dict], source_run: str) -> dict:
    """Build the provenance header that precedes the conversation lines.

    ``chat_count`` is taken from ``chats`` here for convenience, but this
    value is not authoritative on its own: :func:`write_corpus` recomputes
    ``chat_count`` from the ``chats`` list it actually writes and overwrites
    whatever this function returned, so a header built from a different list
    than the one later passed to :func:`write_corpus` never reaches disk
    unreconciled (`§D2`).

    Args:
        chats: The conversations that will form the corpus body.
        source_run: The run id from :func:`resolve_source_run`.

    Returns:
        dict: ``record``, ``corpus_schema`` (``CORPUS_SCHEMA_VERSION``),
        ``chat_schema`` (``writers.SCHEMA_VERSION``), ``source_run``,
        ``generated_at`` (UTC ISO 8601) and ``chat_count`` (``len(chats)``).
    """
    return {
        "record": RECORD_HEADER,
        "corpus_schema": CORPUS_SCHEMA_VERSION,
        "chat_schema": SCHEMA_VERSION,
        "source_run": source_run,
        "generated_at": _utc_now_iso(),
        "chat_count": len(chats),
    }


def write_corpus(chats: list[dict], header: dict, out_path: Path) -> Path:
    """Write ``header`` then one line per conversation to ``out_path``.

    The header is written first, then the conversations in the order given,
    each as ``json.dumps(..., ensure_ascii=False)`` on its own line. The
    conversation dicts are written verbatim — nothing is flattened, trimmed or
    recomputed (`§D3`). Before serializing, ``header["chat_count"]`` is
    overwritten with ``len(chats)`` — the count of the lines actually written
    below it — so the header cannot disagree with the body it precedes,
    regardless of what ``chat_count`` the passed-in ``header`` already carried
    (`§D2`). ``header`` itself is not mutated; a corrected copy is written.

    A written line is delimited strictly by ``\\n``. A reader that counts
    lines with something other than iterating the open file (or splitting the
    text on ``\\n`` alone) can disagree with ``chat_count``: Python's
    ``str.splitlines()`` also breaks on U+2028/U+2029/U+0085, which
    ``ensure_ascii=False`` leaves unescaped inside a JSON string value and
    which a genuine WhatsApp message body can carry. Iterating the file
    object, or ``text.rstrip("\\n").split("\\n")``, is the correct read.

    Args:
        chats: The conversations to write, one per line, in order.
        header: The provenance header from :func:`build_header`. Its
            ``chat_count`` is not trusted; it is replaced with ``len(chats)``.
        out_path: Destination file. Its parent directory is created if absent.

    Returns:
        Path: ``out_path``.

    Raises:
        OSError: If the directory or file cannot be written.
    """
    corrected_header = {**header, "chat_count": len(chats)}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    parts = [json.dumps(corrected_header, ensure_ascii=False) + "\n"]
    for chat in chats:
        parts.append(json.dumps(chat, ensure_ascii=False) + "\n")
    out_path.write_text("".join(parts), encoding="utf-8")
    logger.info(
        "Wrote corpus to %s (1 header + %s conversation line(s), source_run=%s)",
        out_path,
        len(chats),
        corrected_header.get("source_run"),
    )
    return out_path
