"""Serialize one chat export to gitignored ``data/``."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path("data")
SCHEMA_VERSION = 4
CHAT_ID_LENGTH = 12


class MessageRecord(TypedDict):
    """One message in export order, whatever medium it carried.

    `kind` is mandatory rather than optional: a field present only on media
    messages would make a v3 file and a v4 file indistinguishable for text, and
    a reader could not tell an absent `kind` from a message predating the field.
    """

    sender: str
    timestamp: str
    body: str
    kind: str
    order: int


class ChatExport(TypedDict):
    """Export for one chat (ADR-0001, ADR-0003), schema v4.

    The consumer of this file is an agent learning from the conversation, so the
    payload states whether it holds the whole history. A truncated dump that is
    indistinguishable from a complete one is worse than an honest partial: v1
    had no way to say which it was.

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
    complete: bool
    stopped_reason: str
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


def build_export(
    *,
    chat_title: str,
    messages: list[MessageRecord],
    complete: bool,
    stopped_reason: str,
) -> ChatExport:
    """Build the export payload with a UTC stamp and completeness metadata.

    ``chat_title`` is consumed here and never stored: it is hashed into
    ``chat_id`` and dropped. Taking the title rather than a caller-supplied id
    is deliberate — an id parameter is a way for a name to be passed straight
    through into the file.

    Args:
        chat_title: Chat title from WhatsApp Web. Hashed, never written.
        messages: Ordered messages of every kind, so `message_count` counts the
            conversation rather than the text subset of it.
        complete: Whether the harvest reached the beginning of the chat.
        stopped_reason: Which stop condition ended the harvest, so a proven
            start stays distinguishable from an inferred one.

    Returns:
        ChatExport ready for JSON serialization.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "chat_id": pseudonymous_chat_id(chat_title),
        "exported_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "message_count": len(messages),
        "complete": complete,
        "stopped_reason": stopped_reason,
        "messages": messages,
    }


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
        "Wrote export to %s (%s messages, complete=%s, stopped=%s)",
        path,
        export["message_count"],
        export["complete"],
        export["stopped_reason"],
    )
    return path
