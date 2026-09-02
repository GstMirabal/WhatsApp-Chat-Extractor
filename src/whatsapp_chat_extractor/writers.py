"""Serialize one chat export to gitignored ``data/``."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

from whatsapp_chat_extractor.timestamps import undated_count

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path("data")
SCHEMA_VERSION = 6
CHAT_ID_LENGTH = 12

# Mirrored from `history.COMPLETENESS_PROVEN`. Duplicated rather than imported
# because `history` imports `MessageRecord` from this module, and importing back
# would make the pair circular. One string, defined where each side needs it.
COMPLETENESS_PROVEN = "proven"


class MessageRecord(TypedDict):
    """One message in export order, whatever medium it carried.

    `kind` is mandatory rather than optional: a field present only on media
    messages would make a v3 file and a v4 file indistinguishable for text, and
    a reader could not tell an absent `kind` from a message predating the field.

    v6 adds `message_id` and `timestamp_iso` (ADR-0007), both additive.

    `message_id` was already being computed — `history.HarvestedRow` carries it
    and the accumulator dedupes on it — and then dropped at this boundary. A
    corpus without it cannot recognise the same message across two exports, so
    no export can be repeated, merged, or corrected incrementally.

    `timestamp_iso` sits **beside** `timestamp`, never in place of it. The
    rendered string is the evidence: if the parse is ever found wrong it can be
    redone against files already written. It is `""` for a row WhatsApp rendered
    with a clock and no date; `ChatExport.undated_messages` counts those.
    """

    message_id: str
    sender: str
    timestamp: str
    timestamp_iso: str
    body: str
    kind: str
    order: int


class ChatExport(TypedDict):
    """Export for one chat (ADR-0001, ADR-0003, ADR-0004, ADR-0007), schema v6.

    The consumer of this file is an agent learning from the conversation, so the
    payload states whether it holds the whole history. A truncated dump that is
    indistinguishable from a complete one is worse than an honest partial: v1
    had no way to say which it was.

    v6 adds what the corpus needed to be analysed rather than only read
    (ADR-0007). Every addition is additive; no v5 field changes meaning.

    `source_locale` and `source_timezone` say how the timestamps in this file
    were rendered. Without them the message clocks have no frame at all: the
    day/month order followed the operator's machine and nothing recorded which
    it was, so files written before v6 cannot be repaired — the evidence of
    their own format was never stored. `session.py` now pins the locale and
    reads the zone so this stops being true going forward.

    `undated_messages` counts the rows WhatsApp rendered with a clock and no
    date. That fraction has never been measured; carrying the count means the
    first whole-account run under v6 measures it without a live probe.

    `passes_used` was already in `history.HarvestResult` and stopped at the CLI.
    It is the context `completeness` is read in: `unproven` after 12 passes and
    `unproven` after 255 are not the same claim.

    v5 replaces that statement with `completeness` — `proven`, `unproven` or
    `truncated` (ADR-0004). The v4 boolean answered the question with a constant:
    it was True only for a start-of-conversation marker, and Sprint 006 measured
    that marker never appearing across five conversations and two runs, so every
    export ever written said `false`. A field that cannot vary cannot distinguish
    a whole history from a cut-off one, which is the only thing it is for.
    `complete` survives, derived from `completeness == "proven"`, because v4
    files exist and a reader of the boolean must not break on a v5 file.

    v4 adds `kind` to every message and stops dropping messages that carry no
    text (ADR-0003). Under v3 a photo or a voice note left no record at all, so
    `message_count` counted text messages while presenting itself as a message
    count, and the conversation read as question → next question. No media
    content is downloaded or referenced; only the fact that a medium was sent.

    v3 removes `title` and replaces the name-derived `chat_id` with a
    pseudonymous digest. v2 wrote the contact's full name into the payload *and*
    into the filename, which put a real person's identity in plain text on disk,
    visible in a directory listing without opening anything.
    """

    schema_version: int
    chat_id: str
    exported_at: str
    message_count: int
    undated_messages: int
    complete: bool
    completeness: str
    stopped_reason: str
    passes_used: int
    source_locale: str
    source_timezone: str
    messages: list[MessageRecord]


def pseudonymous_chat_id(title: str) -> str:
    """A stable, name-free identifier for a chat.

    Deterministic, so repeated exports of one conversation share an id and can
    be recognised as the same chat without storing who it is.

    This is pseudonymization, not anonymization, and the difference matters: the
    digest is unsalted, so anyone holding a candidate name can confirm a match
    by hashing it. It removes names from disk and from casual view; it does not
    defeat an attacker who already has the contact list. Message bodies are
    untouched and may name people on their own.

    Args:
        title: The chat title as WhatsApp renders it. Never stored.

    Returns:
        str: ``chat_`` followed by a hex digest prefix.
    """
    digest = hashlib.sha256(title.strip().encode("utf-8")).hexdigest()
    return f"chat_{digest[:CHAT_ID_LENGTH]}"


def _derive_computed_fields(
    messages: list[MessageRecord], completeness: str
) -> tuple[int, bool]:
    """Derive the fields ``build_export`` never accepts as arguments.

    Kept separate from payload assembly so the derivation rule for each field
    lives in exactly one place: ``undated_messages`` from the messages
    themselves (ADR-0007), ``complete`` from ``completeness`` (ADR-0004).
    Neither field may be supplied independently by a caller of either
    function — a count or a boolean passed in could disagree with the data
    beside it.

    Args:
        messages: Ordered messages, whose ``timestamp_iso`` values decide how
            many rows WhatsApp rendered with a clock and no date.
        completeness: ``proven``, ``unproven`` or ``truncated``, as
            ``history.classify_completeness`` decided it.

    Returns:
        tuple[int, bool]: ``undated_messages`` and ``complete``, in that
        order.
    """
    undated_messages = undated_count(
        [message.get("timestamp_iso", "") for message in messages]
    )
    complete = completeness == COMPLETENESS_PROVEN
    return undated_messages, complete


def _assemble_export_payload(
    *,
    chat_title: str,
    messages: list[MessageRecord],
    completeness: str,
    stopped_reason: str,
    passes_used: int,
    source_locale: str,
    source_timezone: str,
    undated_messages: int,
    complete: bool,
) -> ChatExport:
    """Assemble the payload dict from fields already validated or derived.

    Private to this module: ``undated_messages`` and ``complete`` are only
    ever supplied here by ``build_export``, right after deriving them via
    ``_derive_computed_fields``. Nothing else calls this helper, so
    ``build_export`` — whose signature has no ``complete`` or
    ``undated_messages`` parameter — is still the only public entry point
    (ADR-0004, ADR-0007).

    Args:
        chat_title: Chat title from WhatsApp Web. Hashed, never written.
        messages: Ordered messages of every kind.
        completeness: ``proven``, ``unproven`` or ``truncated``.
        stopped_reason: Which stop condition ended the harvest.
        passes_used: Scroll passes the harvest spent.
        source_locale: Locale the page rendered under.
        source_timezone: IANA zone the clocks were rendered in.
        undated_messages: Count from ``_derive_computed_fields``.
        complete: Boolean from ``_derive_computed_fields``.

    Returns:
        ChatExport ready for JSON serialization.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "chat_id": pseudonymous_chat_id(chat_title),
        "exported_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "message_count": len(messages),
        "undated_messages": undated_messages,
        "complete": complete,
        "completeness": completeness,
        "stopped_reason": stopped_reason,
        "passes_used": passes_used,
        "source_locale": source_locale,
        "source_timezone": source_timezone,
        "messages": messages,
    }


def build_export(
    *,
    chat_title: str,
    messages: list[MessageRecord],
    completeness: str,
    stopped_reason: str,
    passes_used: int = 0,
    source_locale: str = "",
    source_timezone: str = "",
) -> ChatExport:
    """Build the export payload with a UTC stamp and completeness metadata.

    ``chat_title`` is consumed here and never stored: it is hashed into
    ``chat_id`` and dropped. Taking the title rather than a caller-supplied id
    is deliberate — an id parameter is a way for a name to be passed straight
    through into the file.

    ``complete`` and ``undated_messages`` are derived by
    ``_derive_computed_fields`` rather than accepted as arguments, so neither
    can be given a value that disagrees with the data it is derived from
    (ADR-0004, ADR-0007). See that helper and ``_assemble_export_payload`` for
    per-field documentation.

    Args:
        chat_title: Chat title from WhatsApp Web. Hashed, never written.
        messages: Ordered messages of every kind.
        completeness: ``proven``, ``unproven`` or ``truncated``.
        stopped_reason: Which stop condition ended the harvest.
        passes_used: Scroll passes the harvest spent.
        source_locale: Locale the page rendered under.
        source_timezone: IANA zone the clocks were rendered in.

    Returns:
        ChatExport ready for JSON serialization.
    """
    undated_messages, complete = _derive_computed_fields(messages, completeness)
    return _assemble_export_payload(
        chat_title=chat_title,
        messages=messages,
        completeness=completeness,
        stopped_reason=stopped_reason,
        passes_used=passes_used,
        source_locale=source_locale,
        source_timezone=source_timezone,
        undated_messages=undated_messages,
        complete=complete,
    )


def write_chat_export(
    export: ChatExport,
    data_dir: Path | None = None,
) -> Path:
    """Write ``export`` under ``data_dir`` and return the output path.

    Args:
        export: Payload from ``build_export``.
        data_dir: Destination root (default ``data/``).

    Returns:
        Path to the written ``.json`` file.

    Raises:
        OSError: If the directory or file cannot be written.
    """
    root = data_dir or DEFAULT_DATA_DIR
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    # The filename carries the pseudonymous id, never the title: a directory
    # listing is the one place a name is read without opening a file.
    path = root / f"{export['chat_id']}_{stamp}.json"
    payload: dict[str, Any] = dict(export)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info(
        "Wrote export to %s (%s messages, completeness=%s, stopped=%s)",
        path,
        export["message_count"],
        export["completeness"],
        export["stopped_reason"],
    )
    return path
