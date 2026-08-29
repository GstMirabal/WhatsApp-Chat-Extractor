"""Serialize one chat export to gitignored ``data/``."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path("data")
SCHEMA_VERSION = 2


class MessageRecord(TypedDict):
    """One text message in export order."""

    sender: str
    timestamp: str
    body: str
    order: int


class ChatExport(TypedDict):
    """Text export for one chat (ADR-0001), schema v2.

    The consumer of this file is an agent learning from the conversation, so the
    payload states whether it holds the whole history. A truncated dump that is
    indistinguishable from a complete one is worse than an honest partial: v1
    had no way to say which it was.
    """

    schema_version: int
    chat_id: str
    title: str
    exported_at: str
    message_count: int
    complete: bool
    stopped_reason: str
    messages: list[MessageRecord]


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", value.strip(), flags=re.UNICODE)
    return cleaned.strip("_")[:80] or "chat"


def build_export(
    *,
    chat_id: str,
    title: str,
    messages: list[MessageRecord],
    complete: bool,
    stopped_reason: str,
) -> ChatExport:
    """Build the export payload with a UTC stamp and completeness metadata.

    Args:
        chat_id: Stable id when available; otherwise a slug of the title.
        title: Human-visible chat title from WhatsApp Web.
        messages: Ordered text messages.
        complete: Whether the harvest reached the beginning of the chat.
        stopped_reason: Which stop condition ended the harvest, so a proven
            start stays distinguishable from an inferred one.

    Returns:
        ChatExport ready for JSON serialization.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "chat_id": chat_id or _slugify(title),
        "title": title,
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
    filename = f"{_slugify(export['title'])}_{stamp}.json"
    path = root / filename
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
