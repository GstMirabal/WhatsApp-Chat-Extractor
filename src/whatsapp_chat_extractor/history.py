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
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

from whatsapp_chat_extractor.session import DEFAULT_LOCALE
from whatsapp_chat_extractor.timestamps import parse_rendered
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

# ADR-0004: what the export reports when no beginning can be proven.
#
# `complete` was the whole answer until Sprint 006 measured it never becoming
# True — five conversations, two runs, zero `chat_start` stops — which left the
# field constant and therefore uninformative. These three name what the harvest
# actually knows, and `proven` is kept although it is currently unreachable: the
# day WhatsApp Web renders a start marker, the export must be able to say so.
COMPLETENESS_PROVEN = "proven"
COMPLETENESS_UNPROVEN = "unproven"
COMPLETENESS_TRUNCATED = "truncated"

# Evidence that the panel is still fetching, so a quiet pass is not a stall.
#
# Measured, not guessed: the Sprint 006 probe walked five conversations and one
# of them (175 passes) was declared `stalled` with `data-testid="loading-spinner"`
# still present in the panel chrome. The harvest gave up mid-fetch and reported
# a top it had not reached, which is the same class of error as the 217-message
# "complete" export above — an inference presented as an arrival.
LOADING_SELECTORS = (
    '#main [data-testid="loading-spinner"]',
    '#main [data-icon="loading-spinner"]',
)


class HarvestedRow(TypedDict):
    """One message row as read from the DOM, before ordering is decided."""

    message_id: str
    sender: str
    timestamp: str
    body: str
    kind: str


class HarvestResult(TypedDict):
    """Outcome of a harvest, including how far back it can prove it reached.

    `complete` is retained and derived from `completeness`, never set on its
    own: schema v4 exports already exist and a reader of the boolean must not
    break on a v5 file (ADR-0004).
    """

    messages: list[MessageRecord]
    complete: bool
    completeness: str
    stopped_reason: str
    passes_used: int


def fallback_message_id(
    sender: str, timestamp: str, body: str, kind: str = "text"
) -> str:
    """Stable identity for a row whose ``data-id`` attribute is absent.

    ``kind`` joins the key because media rows have an empty ``body``, so a
    captionless photo and a voice note from one speaker in the same minute would
    otherwise hash identically and the accumulator would drop the second as a
    duplicate.

    It does **not** separate two rows of the *same* kind in that minute — both
    voice notes still collapse. Nothing in the row's text can separate them, so
    the fix is upstream: ``export_one._row_id`` falls back to the
    ``conv-msg-<HEX>`` wrapper the W2 probe found on every row, and a row that
    reaches this function has no identity of its own left to use.

    Args:
        sender: Sender label as rendered.
        timestamp: Timestamp text as rendered.
        body: Message text; empty for a media message with no caption.
        kind: Medium the row carries, as ``export_one._row_kind`` reports it.

    Returns:
        str: Hex digest prefixed with ``sha1:`` so a fallback identity is
            distinguishable from a real WhatsApp ``data-id`` in the output.
    """
    raw = f"{sender}\x1f{timestamp}\x1f{body}\x1f{kind}".encode()
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

    def consolidate(self, *, locale: str = DEFAULT_LOCALE) -> list[MessageRecord]:
        """Flatten the blocks oldest-first and assign ``order``.

        ``message_id`` reaches the record from v6 on. It was always computed —
        it is the key `_seen` dedupes on, three lines above — and until now this
        method dropped it, so no message in the corpus was recognisable across
        two exports (ADR-0007).

        Args:
            locale: Locale the page was rendered under, used to read each row's
                timestamp. Defaults to the pinned one so a caller that does not
                know it still parses the format the harvest actually produces.

        Returns:
            list[MessageRecord]: Messages in conversation order.
        """
        records: list[MessageRecord] = []
        for block in reversed(self._blocks):
            for row in block:
                records.append(self._as_record(row, len(records), locale))
        return records

    @staticmethod
    def _as_record(row: HarvestedRow, order: int, locale: str) -> MessageRecord:
        """One harvested row as the record that gets written.

        Args:
            row: The row as read from the DOM.
            order: Its position in conversation order.
            locale: Locale the page was rendered under.

        Returns:
            MessageRecord: Schema v6 shape.
        """
        rendered = row["timestamp"]
        return {
            # Read directly, not defensively: `add_pass` indexes `message_id`
            # to deduplicate, so a row missing it raises there and can never
            # arrive here. `kind` below is different — nothing indexes it, so a
            # replayed v3 fixture does reach this line without one.
            "message_id": row["message_id"],
            "sender": row["sender"],
            "timestamp": rendered,
            "timestamp_iso": parse_rendered(rendered, locale=locale),
            "body": row["body"],
            # `text` for a row harvested before `kind` existed, so a
            # replayed v3 fixture consolidates without a KeyError.
            "kind": row.get("kind", "text"),
            "order": order,
        }

    def __len__(self) -> int:
        return len(self._seen)


def decide_stop(
    *,
    at_start: bool,
    stall_count: int,
    stall_threshold: int,
    passes_used: int,
    max_passes: int,
    panel_loading: bool = False,
) -> str | None:
    """Whether the harvest should stop, and why.

    ``panel_loading`` suppresses the stall verdict only. A spinner on screen is
    positive evidence that more history is on its way, and stopping on it
    reports a top that was never reached. ``max_passes`` is deliberately not
    suppressed, so a spinner that never resolves still terminates the run — as
    ``max_passes`` rather than as a top, which is the honest reason.

    Args:
        at_start: True when the beginning-of-chat marker is present.
        stall_count: Consecutive passes that produced no new rows.
        stall_threshold: How many stalled passes mean the top was reached.
        passes_used: Passes completed so far.
        max_passes: Hard cap that guarantees termination.
        panel_loading: True when the panel is visibly still fetching.

    Returns:
        str | None: A ``STOP_*`` reason, or None to keep scrolling.
    """
    if at_start:
        return STOP_CHAT_START
    if stall_count >= stall_threshold and not panel_loading:
        return STOP_STALLED
    if passes_used >= max_passes:
        return STOP_MAX_PASSES
    return None


def panel_is_loading(page: Page) -> bool:
    """Whether the conversation panel is visibly still fetching older messages.

    Args:
        page: Page with an open conversation.

    Returns:
        bool: True when a loading indicator is present in the panel.
    """
    for selector in LOADING_SELECTORS:
        if page.query_selector(selector):
            return True
    return False


def classify_completeness(stopped_reason: str, *, panel_loading: bool) -> str:
    """How far back this harvest can prove it reached (ADR-0004).

    Fails closed: a stop reason this function does not recognise is
    ``truncated``, never ``proven``. An unknown reason is not evidence of
    having arrived anywhere.

    The ``stalled``-while-loading pairing is defensive rather than reachable:
    ``decide_stop`` suppresses the stall verdict while the panel is fetching, so
    the harvest loop no longer produces it. It is what probe run 3 recorded
    before that fix, and classifying it as ``unproven`` would reinstate the
    error the fix removed.

    Args:
        stopped_reason: One of the ``STOP_*`` constants.
        panel_loading: Whether the panel was still fetching when the run ended.

    Returns:
        str: One of ``COMPLETENESS_PROVEN``, ``COMPLETENESS_UNPROVEN`` or
            ``COMPLETENESS_TRUNCATED``.
    """
    if stopped_reason in COMPLETE_REASONS:
        return COMPLETENESS_PROVEN
    if stopped_reason == STOP_STALLED and not panel_loading:
        return COMPLETENESS_UNPROVEN
    return COMPLETENESS_TRUNCATED


def build_result(
    accumulator: MessageAccumulator,
    *,
    stopped_reason: str,
    passes_used: int,
    panel_loading: bool = False,
) -> HarvestResult:
    """Assemble the harvest outcome from an accumulator and a stop reason.

    ``completeness`` carries the verdict and ``complete`` is derived from it, so
    the two can never disagree. ``stopped_reason`` still records which condition
    ended the run, so an inferred top stays legible in the exported file rather
    than being flattened into a boolean.

    Args:
        accumulator: The populated accumulator.
        stopped_reason: One of the ``STOP_*`` constants.
        passes_used: Passes completed.
        panel_loading: Whether the panel was still fetching on the final pass.
            Defaults to False, which is the honest reading for a caller that
            cannot observe it.

    Returns:
        HarvestResult: Messages plus completeness metadata.
    """
    completeness = classify_completeness(stopped_reason, panel_loading=panel_loading)
    return {
        "messages": accumulator.consolidate(),
        "complete": completeness == COMPLETENESS_PROVEN,
        "completeness": completeness,
        "stopped_reason": stopped_reason,
        "passes_used": passes_used,
    }


@dataclass
class _HarvestState:
    """Mutable position of one harvest, carried between passes.

    A dataclass rather than four locals because :func:`_one_pass` has to advance
    all of them and `agents.md §1` caps a function at 50 lines; passing and
    returning a tuple of four would move the complexity rather than remove it.
    """

    stall_count: int = 0
    passes_used: int = 0
    reason: str | None = None
    panel_loading: bool = False


def _one_pass(
    page: Page,
    accumulator: MessageAccumulator,
    state: _HarvestState,
    *,
    chat_title: str,
    max_passes: int,
    stall_threshold: int,
    load_wait_ms: int,
) -> None:
    """Read the panel once, decide whether to stop, and scroll if not.

    Args:
        page: Page with an open conversation.
        accumulator: Rows discovered so far; mutated.
        state: Harvest position; mutated.
        chat_title: Forwarded to row collection for direction detection only.
        max_passes: Hard cap on scroll passes.
        stall_threshold: Quiet passes that end the run.
        load_wait_ms: How long this pass waits for older messages.
    """
    from whatsapp_chat_extractor.export_one import (
        at_chat_start,
        collect_visible_rows,
        scroll_one_pass,
    )

    added = accumulator.add_pass(collect_visible_rows(page, chat_title=chat_title))
    state.passes_used += 1
    if added:
        state.stall_count = 0
    logger.info("Pass %s: +%s new, %s total (stall %s/%s)", state.passes_used,
                added, len(accumulator), state.stall_count, stall_threshold)
    # Read once and reuse: the same observation decides whether to stop and how
    # to classify the stop. Sampling it twice could report a spinner to one and
    # not the other, which is a disagreement no reader could resolve.
    state.panel_loading = panel_is_loading(page)
    state.reason = decide_stop(
        at_start=at_chat_start(page),
        stall_count=state.stall_count,
        stall_threshold=stall_threshold,
        passes_used=state.passes_used,
        max_passes=max_passes,
        panel_loading=state.panel_loading,
    )
    if state.reason is None and not scroll_one_pass(page, max_wait_ms=load_wait_ms):
        # The scroll waited for older messages and none arrived. That is the
        # stall signal, not "the collect found nothing" — a pass can legibly add
        # zero rows while the panel is still loading beneath it.
        state.stall_count += 1


def harvest_history(
    page: Page,
    *,
    chat_title: str = "",
    max_passes: int = DEFAULT_MAX_PASSES,
    stall_threshold: int = DEFAULT_STALL_THRESHOLD,
    load_wait_ms: int = DEFAULT_LOAD_WAIT_MS,
) -> HarvestResult:
    """Collect a whole conversation by scrolling upward and merging each pass.

    Args:
        page: Page with an open conversation.
        chat_title: Forwarded to row collection for direction detection only;
            it is compared against speaker labels and never stored.
        max_passes: Hard cap on scroll passes; guarantees termination.
        stall_threshold: Consecutive passes without new rows that end the run.
        load_wait_ms: How long one pass waits for older messages to arrive.

    Returns:
        HarvestResult: Ordered messages plus completeness metadata.
    """
    accumulator = MessageAccumulator()
    state = _HarvestState()

    while state.reason is None:
        _one_pass(
            page, accumulator, state,
            chat_title=chat_title, max_passes=max_passes,
            stall_threshold=stall_threshold, load_wait_ms=load_wait_ms,
        )

    logger.info("Harvest stopped (%s) after %s passes", state.reason, state.passes_used)
    return build_result(
        accumulator,
        stopped_reason=state.reason,
        passes_used=state.passes_used,
        panel_loading=state.panel_loading,
    )
