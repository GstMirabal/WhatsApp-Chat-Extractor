"""Full-history harvest: scroll upward, collect, deduplicate, repeat.

WhatsApp Web virtualizes the message list: rows scrolled out of the viewport are
removed from the DOM. Scrolling to the top and reading the DOM once — the P1
spike strategy — therefore loses the *recent* end of the conversation, and
raising the scroll count makes the loss worse rather than smaller.

The correction is to read the DOM on every pass and merge by message identity.
Everything in this module except :func:`harvest_history` is pure, so the merge
and termination rules are tested against synthetic pass sequences with no
browser involved (`tests/test_history.py`).
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, TypedDict

from whatsapp_chat_extractor.writers import MessageRecord

if TYPE_CHECKING:  # pragma: no cover - typing only
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)

DEFAULT_MAX_PASSES = 2000
DEFAULT_STALL_THRESHOLD = 3
# Pulling older history from the phone is a network round trip, not a render.
DEFAULT_LOAD_WAIT_MS = 15_000

STOP_CHAT_START = "chat_start"
STOP_STALLED = "stalled"
STOP_MAX_PASSES = "max_passes"

# Only a start-of-conversation marker proves the whole history was read.
#
# `STOP_STALLED` was in this tuple until the first live run, where it produced a
# `complete: true` export of 217 messages from a conversation the operator knew
# to be far longer: the panel had simply not finished loading within the fixed
# 400 ms wait, three passes in a row. The scroll now waits on evidence of
# loading rather than on a clock, which makes a stall much stronger evidence —
# but it remains an inference, and this file is a training corpus. An inference
# is not allowed to be recorded as proof.
COMPLETE_REASONS = (STOP_CHAT_START,)


class HarvestedRow(TypedDict):
    """One message row as read from the DOM, before ordering is decided."""

    message_id: str
    sender: str
    timestamp: str
    body: str


class HarvestResult(TypedDict):
    """Outcome of a harvest, including whether it reached the chat start."""

    messages: list[MessageRecord]
    complete: bool
    stopped_reason: str
    passes_used: int


def fallback_message_id(sender: str, timestamp: str, body: str) -> str:
    """Stable identity for a row whose ``data-id`` attribute is absent.

    Args:
        sender: Sender label as rendered.
        timestamp: Timestamp text as rendered.
        body: Message text.

    Returns:
        str: Hex digest prefixed with ``sha1:`` so a fallback identity is
            distinguishable from a real WhatsApp ``data-id`` in the output.
    """
    raw = f"{sender}\x1f{timestamp}\x1f{body}".encode()
    return f"sha1:{hashlib.sha1(raw).hexdigest()}"


class MessageAccumulator:
    """Ordered, deduplicated store of rows discovered while scrolling upward.

    Each pass sees an older window than the one before it, so the rows a pass
    contributes for the first time are older than everything already stored.
    Blocks are therefore consolidated in reverse discovery order, and ``order``
    is assigned once at the end — never during the harvest, where an older
    prefix can still appear.

    Messages that arrive *during* a long export are appended to whichever block
    first observes them, which places them with that block rather than at the
    true end. The export stamp bounds the affected window.
    """

    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._blocks: list[list[HarvestedRow]] = []

    def add_pass(self, rows: list[HarvestedRow]) -> int:
        """Store the rows of one pass that were not seen before.

        Args:
            rows: Rows read from the DOM in document order (oldest first).

        Returns:
            int: How many rows were new. Zero means the pass revealed nothing.
        """
        block = [row for row in rows if row["message_id"] not in self._seen]
        self._seen.update(row["message_id"] for row in block)
        if block:
            self._blocks.append(block)
        return len(block)

    def consolidate(self) -> list[MessageRecord]:
        """Flatten the blocks oldest-first and assign ``order``.

        Returns:
            list[MessageRecord]: Messages in conversation order.
        """
        records: list[MessageRecord] = []
        for block in reversed(self._blocks):
            for row in block:
                records.append(
                    {
                        "sender": row["sender"],
                        "timestamp": row["timestamp"],
                        "body": row["body"],
                        "order": len(records),
                    }
                )
        return records

    def __len__(self) -> int:
        return len(self._seen)


def decide_stop(
    *,
    at_start: bool,
    stall_count: int,
    stall_threshold: int,
    passes_used: int,
    max_passes: int,
) -> str | None:
    """Whether the harvest should stop, and why.

    Args:
        at_start: True when the beginning-of-chat marker is present.
        stall_count: Consecutive passes that produced no new rows.
        stall_threshold: How many stalled passes mean the top was reached.
        passes_used: Passes completed so far.
        max_passes: Hard cap that guarantees termination.

    Returns:
        str | None: A ``STOP_*`` reason, or None to keep scrolling.
    """
    if at_start:
        return STOP_CHAT_START
    if stall_count >= stall_threshold:
        return STOP_STALLED
    if passes_used >= max_passes:
        return STOP_MAX_PASSES
    return None


def build_result(
    accumulator: MessageAccumulator,
    *,
    stopped_reason: str,
    passes_used: int,
) -> HarvestResult:
    """Assemble the harvest outcome from an accumulator and a stop reason.

    ``complete`` is True only for the chat-start marker, the one stop that
    proves the whole history was read. ``stopped_reason`` records which
    condition ended the run, so an inferred top (`stalled`) stays legible in the
    exported file rather than being flattened into a boolean.

    Args:
        accumulator: The populated accumulator.
        stopped_reason: One of the ``STOP_*`` constants.
        passes_used: Passes completed.

    Returns:
        HarvestResult: Messages plus completeness metadata.
    """
    return {
        "messages": accumulator.consolidate(),
        "complete": stopped_reason in COMPLETE_REASONS,
        "stopped_reason": stopped_reason,
        "passes_used": passes_used,
    }


def harvest_history(
    page: Page,
    *,
    max_passes: int = DEFAULT_MAX_PASSES,
    stall_threshold: int = DEFAULT_STALL_THRESHOLD,
    load_wait_ms: int = DEFAULT_LOAD_WAIT_MS,
) -> HarvestResult:
    """Collect a whole conversation by scrolling upward and merging each pass.

    Args:
        page: Page with an open conversation.
        max_passes: Hard cap on scroll passes; guarantees termination.
        stall_threshold: Consecutive passes without new rows that end the run.
        load_wait_ms: How long one pass waits for older messages to arrive.

    Returns:
        HarvestResult: Ordered messages plus completeness metadata.
    """
    from whatsapp_chat_extractor.export_one import (
        at_chat_start,
        collect_visible_rows,
        scroll_one_pass,
    )

    accumulator = MessageAccumulator()
    stall_count = 0
    passes_used = 0
    reason: str | None = None

    while reason is None:
        added = accumulator.add_pass(collect_visible_rows(page))
        passes_used += 1
        if added:
            stall_count = 0
        logger.info(
            "Pass %s: +%s new, %s total (stall %s/%s)",
            passes_used, added, len(accumulator), stall_count, stall_threshold,
        )
        reason = decide_stop(
            at_start=at_chat_start(page),
            stall_count=stall_count,
            stall_threshold=stall_threshold,
            passes_used=passes_used,
            max_passes=max_passes,
        )
        if reason is None and not scroll_one_pass(page, max_wait_ms=load_wait_ms):
            # The scroll waited for older messages and none arrived. That is the
            # stall signal, not "the collect found nothing" — a pass can legibly
            # add zero rows while the panel is still loading beneath it.
            stall_count += 1

    logger.info("Harvest stopped (%s) after %s passes", reason, passes_used)
    return build_result(accumulator, stopped_reason=reason, passes_used=passes_used)
