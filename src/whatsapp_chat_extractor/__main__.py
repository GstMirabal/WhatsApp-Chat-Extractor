"""CLI entrypoints: ``login``, ``export-one``, ``export-all`` and ``recover``.

Playwright is imported inside the three browser-driven entrypoints, never at
module level, so ``recover`` runs on a machine that cannot launch Chromium
(`IMPLEMENTATION_PLAN.md` §D4). Rebuilding the record of a dead run is forensic
work and must not require the browser the dead run needed.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple, TextIO

from whatsapp_chat_extractor.chat_list import (
    DEFAULT_SETTLE_MS as CHAT_LIST_SETTLE_MS,
)
from whatsapp_chat_extractor.chat_list import (
    ENUMERATION_CONVERGED,
    open_chat_by_digest,
    sweep_until_stable,
)
from whatsapp_chat_extractor.consolidate import (
    build_header,
    read_chat_files,
    resolve_source_run,
    write_corpus,
)
from whatsapp_chat_extractor.export_one import open_chat_by_query
from whatsapp_chat_extractor.history import (
    COMPLETENESS_TRUNCATED,
    COMPLETENESS_UNPROVEN,
    DEFAULT_LOAD_WAIT_MS,
    DEFAULT_MAX_PASSES,
    DEFAULT_STALL_THRESHOLD,
    harvest_history,
)
from whatsapp_chat_extractor.journal import (
    append_outcome,
    exported_chat_ids,
    journal_path,
    open_journal,
    read_journal,
    write_header,
)
from whatsapp_chat_extractor.manifest import (
    OUTCOME_FAILED,
    exported,
    failed,
    manifest_from_journal,
    now,
    skipped,
    write_chat_index,
    write_manifest,
)
from whatsapp_chat_extractor.session import (
    DEFAULT_LOCALE,
    DEFAULT_PROFILE_DIR,
    launch_context,
    open_whatsapp,
    qr_visible,
    resolve_timezone,
    wait_until_ready,
)
from whatsapp_chat_extractor.writers import (
    DEFAULT_DATA_DIR,
    build_export,
    write_chat_export,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("wa-extract")

EXIT_INCOMPLETE = 3


class RunJournal(NamedTuple):
    """The open journal of one run, plus what a resume already found in it.

    Bundled rather than passed as four separate arguments so that the export
    walk carries one optional parameter: it is driven in tests with no journal
    at all, and a single ``None`` says that far more clearly than four.
    """

    handle: TextIO
    run_id: str
    started_at: str
    already_exported: frozenset[str]


def _add_shared_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile-dir",
        type=Path,
        default=DEFAULT_PROFILE_DIR,
        help="Persistent Chromium profile (default: data/browser_profile)",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=300_000,
        help="Max wait for ready state / QR (milliseconds)",
    )


def mint_run_id() -> str:
    """Coin the identity of a run, once, before anything is written.

    Minted at the start of the run rather than at the moment each file is
    written: `write_manifest`, `write_chat_index` and the journal each used to
    derive their own timestamp, so the three files of one run could carry three
    different stamps and none of them named the run (`§D2`).

    Returns:
        str: A UTC stamp in the same shape those writers used as their
            fallback, so filenames keep the form readers already expect.
    """
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def cmd_login(args: argparse.Namespace) -> int:
    """Open WhatsApp Web and wait until the chat list is ready."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        context = launch_context(
            playwright,
            profile_dir=args.profile_dir,
            headless=False,
        )
        try:
            page = open_whatsapp(context)
            if qr_visible(page):
                logger.info("QR visible — scan with the business phone")
            ready = wait_until_ready(page, timeout_ms=args.timeout_ms)
            logger.info("Session ready (%s). Profile kept at %s", ready, args.profile_dir)
            if args.keep_open:
                logger.info("Keeping browser open until Enter…")
                input()
        finally:
            context.close()
    return 0


def cmd_export_one(args: argparse.Namespace) -> int:
    """Export one human-selected chat's full history to JSON under ``data/``.

    Returns:
        int: ``0`` when the harvest reached the start of the chat, ``3`` when it
            stopped at the pass cap, so a caller can tell a complete corpus from
            a truncated one without parsing the file.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        context = launch_context(
            playwright,
            profile_dir=args.profile_dir,
            headless=False,
        )
        try:
            page = open_whatsapp(context)
            wait_until_ready(page, timeout_ms=args.timeout_ms)
            title = open_chat_by_query(page, args.query, timeout_ms=60_000)
            harvest = harvest_history(
                page,
                chat_title=title,
                max_passes=args.max_passes,
                stall_threshold=args.stall_threshold,
                load_wait_ms=args.load_wait_ms,
                deadline_seconds=args.deadline_seconds,
            )
            export = build_export(
                chat_title=title,
                messages=harvest["messages"],
                completeness=harvest["completeness"],
                stopped_reason=harvest["stopped_reason"],
                passes_used=harvest["passes_used"],
                source_locale=DEFAULT_LOCALE,
                source_timezone=resolve_timezone(page),
            )
            path = write_chat_export(export, data_dir=args.data_dir)
            print(path)
        finally:
            context.close()

    return report_completeness(harvest)


def report_completeness(harvest: dict) -> int:
    """Tell the operator what the harvest reached, and pick the exit code.

    Only `truncated` is a failure. Under the v4 boolean this branch fired on
    every single export ever produced, because `complete` was never True
    (ADR-0004): the operator was told each run had failed and to raise a cap
    that was not the cause. `unproven` is the expected outcome and exits 0.

    Args:
        harvest: A ``HarvestResult``.

    Returns:
        int: ``0`` unless the harvest was truncated.
    """
    if harvest["completeness"] == COMPLETENESS_TRUNCATED:
        logger.error(
            "Truncated export: the harvest ended at %s passes (%s) before the "
            "conversation did. Re-run with a higher --max-passes.",
            harvest["passes_used"],
            harvest["stopped_reason"],
        )
        return EXIT_INCOMPLETE
    if harvest["completeness"] == COMPLETENESS_UNPROVEN:
        logger.info(
            "Export complete as far as can be shown: the panel stopped "
            "producing history after %s passes, but no start-of-chat marker "
            "was observed, so the beginning is not proven.",
            harvest["passes_used"],
        )
    return 0


def _export_open_chat(page: object, title: str, args: argparse.Namespace) -> tuple:
    """Harvest and write the conversation currently on screen.

    Args:
        page: Page with the conversation open.
        title: Verified title of that conversation. Hashed, never stored.
        args: Parsed command line, carrying the run's resolved timezone in
            ``source_timezone``.

    Returns:
        tuple: The harvest result and the path written.
    """
    harvest = harvest_history(
        page,
        chat_title=title,
        max_passes=args.max_passes,
        stall_threshold=args.stall_threshold,
        load_wait_ms=args.load_wait_ms,
        deadline_seconds=args.deadline_seconds,
    )
    export = build_export(
        chat_title=title,
        messages=harvest["messages"],
        completeness=harvest["completeness"],
        stopped_reason=harvest["stopped_reason"],
        passes_used=harvest["passes_used"],
        source_locale=DEFAULT_LOCALE,
        source_timezone=args.source_timezone,
    )
    return harvest, write_chat_export(export, data_dir=args.data_dir)


def _export_one_ref(
    page: object, ref: dict, args: argparse.Namespace, *, total: int
) -> tuple:
    """Open, harvest and write one enumerated conversation.

    A failure is returned as an outcome rather than raised, because a run of
    hundreds must not end on the third (`§D3`); the caller decides what to do
    with it.

    Args:
        page: Ready WhatsApp Web page showing the chat list.
        ref: The enumerated `ChatRef` to open.
        args: Parsed command line.
        total: How many conversations the enumeration found, for the log line.

    Returns:
        tuple: The outcome to record, and the conversation's title — ``""``
            when it failed, so no real name is carried out of an attempt that
            wrote no file.
    """
    try:
        title = open_chat_by_digest(page, ref, total=total, settle_ms=args.settle_ms)
        harvest, path = _export_open_chat(page, title, args)
    except (LookupError, RuntimeError) as exc:
        logger.warning("Chat %s failed: %s", ref["chat_id"], exc)
        return failed(ref["chat_id"], index=ref["index"], reason=str(exc)), ""
    return exported(
        ref["chat_id"], index=ref["index"],
        completeness=harvest["completeness"],
        message_count=len(harvest["messages"]), file=path.name,
    ), title


def _record_header(journal: RunJournal | None, enumerated: dict) -> None:
    """Write the run header the moment the sweep returns, and not before.

    Before the sweep the header would carry no `chats_enumerated`, which is the
    field that lets a rebuilt manifest say how many conversations were never
    attempted. After the first conversation it would not exist at all for a run
    that died on that conversation.

    Args:
        journal: The run's open journal, or ``None`` when the walk is driven
            without one.
        enumerated: The `sweep_until_stable` result.
    """
    if journal is None:
        return
    write_header(
        journal.handle,
        run_id=journal.run_id,
        started_at=journal.started_at,
        chats_enumerated=len(enumerated["refs"]),
        enumeration=enumerated["enumeration"],
        sweeps=enumerated["sweeps"],
    )


def _record_outcome(journal: RunJournal | None, outcome: dict) -> None:
    """Append one conversation's outcome as the run makes it.

    Written inside the walk rather than batched at the end: the record exists
    for the run that does not reach the end.

    Args:
        journal: The run's open journal, or ``None``.
        outcome: Entry from ``manifest.exported``, ``failed`` or ``skipped``.
            It carries no title (`ADR-0001`, `§D5`).
    """
    if journal is not None:
        append_outcome(journal.handle, outcome)


def _export_every_chat(
    page: object, args: argparse.Namespace, *, journal: RunJournal | None = None
) -> tuple:
    """Walk the enumerated list, exporting each conversation in turn.

    A failure on one conversation does not end the run (`§D3`). Losing the
    WhatsApp session does end it, because every later attempt would fail
    identically. Conversations a resumed run already exported are stepped over
    rather than re-recorded: the journal already holds their outcome.

    Args:
        page: Ready WhatsApp Web page showing the chat list.
        args: Parsed command line.
        journal: The run's open journal. ``None`` drives the walk with no
            durable record, which is what the browserless tests do.

    Returns:
        tuple: The outcomes this pass produced, the `ADR-0005` enumeration
            result, and the digest-to-title index.
    """
    enumerated = sweep_until_stable(page, settle_ms=args.settle_ms)
    _record_header(journal, enumerated)
    refs = enumerated["refs"]
    targets = refs[: args.limit] if args.limit else refs
    done = journal.already_exported if journal else frozenset()
    outcomes: list[dict] = []
    index: dict[str, str] = {}
    for position, ref in enumerate(targets, start=1):
        logger.info("Chat %s of %s (%s)", position, len(targets), ref["chat_id"])
        if ref["chat_id"] in done:
            logger.info("Already exported by this run id; not re-opened")
            continue
        outcome, title = _export_one_ref(page, ref, args, total=len(refs))
        if title:
            index[ref["chat_id"]] = title
        outcomes.append(outcome)
        _record_outcome(journal, outcome)
    for ref in refs[len(targets):]:
        beyond = skipped(ref["chat_id"], index=ref["index"], reason="beyond --limit")
        outcomes.append(beyond)
        _record_outcome(journal, beyond)
    return outcomes, enumerated, index


def _request_timezone(requested: str) -> None:
    """Ask the browser process to render its clocks in ``requested``.

    Made through the environment Chromium inherits at launch because
    ``session.launch_context`` takes no ``timezone_id``. It is a request, not a
    guarantee, and nothing is recorded from it: every export states the zone the
    page itself resolved (:func:`_confirm_timezone`). Without the flag nothing
    is decided and the machine's own zone stands (`§D7`).

    Args:
        requested: IANA zone such as ``Europe/Madrid``, or ``""`` for none.
    """
    if not requested:
        return
    os.environ["TZ"] = requested
    logger.info("Asking the browser to render its clocks in %s", requested)


def _confirm_timezone(page: object, requested: str) -> str:
    """Read back the zone the page actually rendered its clocks in.

    Args:
        page: Ready WhatsApp Web page.
        requested: What ``--timezone`` asked for, or ``""``.

    Returns:
        str: The zone ``session.resolve_timezone`` read, or ``""`` when the page
            could not answer. Never the requested value — recording a zone the
            page did not use would put a false frame on every timestamp in the
            corpus, which is the defect `ADR-0007` exists to close.
    """
    resolved = resolve_timezone(page)
    if requested and resolved != requested:
        logger.warning(
            "Asked for timezone %s but the page resolved %r. The export records "
            "what the page resolved.", requested, resolved,
        )
    return resolved


def _export_all_session(args: argparse.Namespace, journal: RunJournal) -> tuple:
    """Drive one browser session for a whole-account run.

    Args:
        args: Parsed command line. The resolved timezone is recorded onto it as
            ``source_timezone``, beside the other per-run settings it carries,
            so every conversation is written under the one value read once when
            the session became ready.
        journal: The run's open journal.

    Returns:
        tuple: What :func:`_export_every_chat` returned.
    """
    from playwright.sync_api import sync_playwright

    _request_timezone(args.timezone)
    with sync_playwright() as playwright:
        context = launch_context(
            playwright, profile_dir=args.profile_dir, headless=False
        )
        try:
            page = open_whatsapp(context)
            wait_until_ready(page, timeout_ms=args.timeout_ms)
            args.source_timezone = _confirm_timezone(page, args.timezone)
            return _export_every_chat(page, args, journal=journal)
        finally:
            context.close()


def _latest_per_chat(outcomes: list[dict]) -> list[dict]:
    """The last outcome recorded for each conversation, in first-seen order.

    A journal is append-only and a resumed run appends to the journal of the
    run it resumes, so one conversation can hold a `failed` line from the first
    attempt and an `exported` line from the retry. Both are true of the run's
    history; only the last is true of its result, and counting both would report
    one conversation as failed and exported at the same time.

    Args:
        outcomes: Every outcome the journal holds, in write order.

    Returns:
        list[dict]: One entry per `chat_id`.
    """
    latest: dict[str, dict] = {}
    for outcome in outcomes:
        latest[outcome["chat_id"]] = outcome
    return list(latest.values())


def _manifest_from_journal_file(path: Path, enumerated_refs: list) -> dict:
    """Rebuild a run manifest from the journal on disk.

    Read back from the file rather than assembled from memory, so the manifest
    states what was durably recorded and a resumed run's manifest carries the
    conversations its earlier pass exported.

    Args:
        path: The run's journal, from ``journal.journal_path``.
        enumerated_refs: Conversations a live enumeration found, so the ones the
            journal never reached are recorded as `skipped`. Empty when there
            was no enumeration — `recover` has no browser to make one with.

    Returns:
        dict: A ``RunManifest``.

    Raises:
        RuntimeError: If the journal holds no header, which means the run it
            belongs to never got past enumeration and there is nothing to state
            about it that would not be invented.
    """
    header, outcomes = read_journal(path)
    if header is None:
        raise RuntimeError(
            f"{path} holds no header record, so started_at, chats_enumerated, "
            "enumeration and sweeps are unknown and the manifest cannot be "
            "rebuilt from it"
        )
    return manifest_from_journal(header, _latest_per_chat(outcomes), enumerated_refs)


def _titles_for_index(index: dict, data_dir: Path, run_id: str) -> dict:
    """Fold this pass's titles into any index an earlier pass of the run wrote.

    ``write_chat_index`` truncates, and every pass of one run now writes the
    same filename because the name carries the `run_id`. Without this fold,
    resuming a run with `--write-index` would replace the mapping of every
    conversation the earlier pass exported with the mapping of the few this pass
    opened, and the operator would have no way to tell that names went missing.

    Args:
        index: `chat_id` to title, as this pass read them.
        data_dir: Where the run writes.
        run_id: Identity of the run. The filename is `manifest.write_chat_index`'s
            convention, mirrored here to read back what that function wrote.

    Returns:
        dict: The earlier mapping updated with this pass's. This pass's titles
            win, because they were read from the chat list more recently.
    """
    path = data_dir / f"chat_index_{run_id}.json"
    if not path.is_file():
        return index
    try:
        earlier = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Could not read %s; writing only this pass's titles", path)
        return index
    if not isinstance(earlier, dict):
        logger.warning("%s is not an object; writing only this pass's titles", path)
        return index
    return {**earlier, **index}


def _run_exit_code(manifest: dict) -> int:
    """Pick the process exit code from the run's own record.

    Args:
        manifest: A ``RunManifest``.

    Returns:
        int: ``0`` only when the enumeration converged, nothing failed, and
            every enumerated conversation has an entry. ``3`` otherwise — a run
            that recorded fewer conversations than it enumerated stopped early,
            and reporting success for it is what the journal exists to prevent.
    """
    if manifest["enumeration"] != ENUMERATION_CONVERGED:
        return EXIT_INCOMPLETE
    if manifest["counts"][OUTCOME_FAILED]:
        return EXIT_INCOMPLETE
    if len(manifest["chats"]) < manifest["chats_enumerated"]:
        return EXIT_INCOMPLETE
    return 0


def _warn_on_partial_enumeration(enumerated: dict) -> None:
    """Say plainly when a run was not a whole-account export.

    Args:
        enumerated: The `sweep_until_stable` result.
    """
    if enumerated["enumeration"] == ENUMERATION_CONVERGED:
        return
    logger.error(
        "Enumeration is %s over %s sweeps, so this is not a whole-account "
        "export. `truncated` means the sweep never reached the foot of the "
        "chat list: raise --max-passes. `unconverged` means the list was "
        "still yielding new conversations when the sweep budget ran out.",
        enumerated["enumeration"], enumerated["sweeps"],
    )


def cmd_export_all(args: argparse.Namespace) -> int:
    """Export every conversation in the chat list, and record what happened.

    Returns:
        int: ``0`` when the enumeration converged and every enumerated
            conversation is accounted for, ``3`` otherwise. The manifest and the
            journal carry the detail either way.
    """
    run_id = args.resume or mint_run_id()
    path = journal_path(run_id, args.data_dir)
    resumed = frozenset(exported_chat_ids(path)) if args.resume else frozenset()
    logger.info(
        "Run %s (%s already exported, re-enumerating the chat list either way)",
        run_id, len(resumed),
    )
    with open_journal(run_id, data_dir=args.data_dir) as handle:
        journal = RunJournal(handle, run_id, now(), resumed)
        _, enumerated, index = _export_all_session(args, journal)

    manifest = _manifest_from_journal_file(path, enumerated["refs"])
    print(write_manifest(manifest, data_dir=args.data_dir, run_id=run_id))
    if args.write_index and index:
        write_chat_index(_titles_for_index(index, args.data_dir, run_id),
                         data_dir=args.data_dir, run_id=run_id)
    _warn_on_partial_enumeration(enumerated)
    return _run_exit_code(manifest)


def cmd_recover(args: argparse.Namespace) -> int:
    """Rebuild a dead run's manifest from its journal, with no browser.

    Returns:
        int: The same code the run itself would have returned, from the same
            rule (:func:`_run_exit_code`).

    Raises:
        RuntimeError: If the journal is absent or holds no header record.
    """
    path = journal_path(args.run_id, args.data_dir)
    manifest = _manifest_from_journal_file(path, [])
    print(write_manifest(manifest, data_dir=args.data_dir, run_id=args.run_id))
    unrecorded = manifest["chats_enumerated"] - len(manifest["chats"])
    if unrecorded > 0:
        logger.warning(
            "%s of the %s conversations this run enumerated have no line in the "
            "journal and cannot be named: the journal records what was done, "
            "never what the chat list held. Re-run export-all --resume %s to "
            "reach them.", unrecorded, manifest["chats_enumerated"], args.run_id,
        )
    return _run_exit_code(manifest)


def cmd_consolidate(args: argparse.Namespace) -> int:
    """Join every per-conversation export under ``data_dir`` into one NDJSON.

    Opens no browser: reading the export files and writing one corpus is work
    a machine without Chromium must still be able to do (`§D4`).

    Returns:
        int: ``0`` on success, ``2`` if `consolidate` rejected the input
            (duplicate ``chat_id``, or a file that is not schema v6).
    """
    try:
        chats = read_chat_files(args.data_dir)
        source_run = resolve_source_run(args.data_dir, args.from_manifest)
        out_path = args.out or args.data_dir / f"corpus_{source_run}.ndjson"
        header = build_header(chats, source_run)
        write_corpus(chats, header, out_path)
    except ValueError as exc:
        logger.error("%s", exc)
        return 2
    print(out_path)
    return 0


def _add_harvest_args(parser: argparse.ArgumentParser) -> None:
    """Scroll-and-wait knobs shared by both export subcommands.

    Args:
        parser: The subcommand parser to extend.
    """
    parser.add_argument(
        "--max-passes", type=int, default=DEFAULT_MAX_PASSES,
        help=f"Hard cap on scroll passes per chat (default: {DEFAULT_MAX_PASSES})",
    )
    parser.add_argument(
        "--stall-threshold", type=int, default=DEFAULT_STALL_THRESHOLD,
        help="Consecutive passes without new messages that end one harvest "
             f"(default: {DEFAULT_STALL_THRESHOLD})",
    )
    parser.add_argument(
        "--load-wait-ms", type=int, default=DEFAULT_LOAD_WAIT_MS,
        help="How long one pass waits for older messages from the phone "
             f"(default: {DEFAULT_LOAD_WAIT_MS})",
    )
    parser.add_argument(
        "--deadline-seconds", type=float, default=None,
        help="Wall-clock budget for the whole harvest of one chat, in "
             "seconds (KI-009-H). Unbounded by default: only --max-passes "
             "guarantees termination unless this is set",
    )


def _add_login(sub: argparse._SubParsersAction) -> None:
    """Register the `login` subcommand.

    Args:
        sub: The subparser registry.
    """
    login = sub.add_parser("login", help="Open WA Web; wait for QR / chat list")
    _add_shared_args(login)
    login.add_argument(
        "--keep-open",
        action="store_true",
        help="Wait for Enter before closing the browser",
    )
    login.set_defaults(func=cmd_login)



def _add_export_one(sub: argparse._SubParsersAction) -> None:
    """Register the `export-one` subcommand.

    Args:
        sub: The subparser registry.
    """
    export_one = sub.add_parser(
        "export-one",
        help="Open one chat by search query and write its full history to data/",
    )
    _add_shared_args(export_one)
    export_one.add_argument(
        "--query",
        required=True,
        help="Chat title / contact fragment (human-chosen)",
    )
    export_one.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Output directory (default: data/)",
    )
    # No --chat-id: the export is pseudonymous, and a caller-supplied id is a
    # way to put a real name back into the filename and the payload.
    _add_harvest_args(export_one)
    export_one.set_defaults(func=cmd_export_one)



def _add_export_all(sub: argparse._SubParsersAction) -> None:
    """Register the `export-all` subcommand.

    Args:
        sub: The subparser registry.
    """
    export_all = sub.add_parser(
        "export-all",
        help="Enumerate every chat and export each, writing a run manifest",
    )
    _add_shared_args(export_all)
    export_all.add_argument(
        "--data-dir", type=Path, default=DEFAULT_DATA_DIR,
        help="Output directory (default: data/)",
    )
    export_all.add_argument(
        "--limit", type=int, default=0,
        help="Export only the first N enumerated chats (0 = all). The rest are "
             "recorded as skipped rather than omitted",
    )
    export_all.add_argument(
        "--settle-ms", type=int, default=CHAT_LIST_SETTLE_MS,
        help=f"Wait after each chat-list scroll (default: {CHAT_LIST_SETTLE_MS})",
    )
    export_all.add_argument(
        "--resume", default="", metavar="RUN_ID",
        help="Continue the run with this id: append to its journal and step "
             "over the chats it already exported. The chat list is enumerated "
             "again from scratch, never taken from the journal",
    )
    export_all.add_argument(
        "--timezone", default="", metavar="IANA_ZONE",
        help="Ask the browser to render its clocks in this zone, e.g. "
             "Europe/Madrid. Each export records the zone the page actually "
             "resolved, never this request",
    )
    # Off by default and named for what it does. This is the only flag in the
    # project that causes real conversation names to be written to disk
    # (ADR-0001); the manifest never carries them.
    export_all.add_argument(
        "--write-index", action="store_true",
        help="Also write data/chat_index_<run_id>.json mapping chat_id to the "
             "REAL conversation name. Off by default; delete it when done",
    )
    _add_harvest_args(export_all)
    # Filled in once the session is ready, so it is always present to read.
    export_all.set_defaults(func=cmd_export_all, source_timezone="")



def _add_recover(sub: argparse._SubParsersAction) -> None:
    """Register the `recover` subcommand.

    It takes no browser arguments, because it drives no browser: answering
    "what did that run manage to do?" must not require opening WhatsApp Web
    (`§D4`).

    Args:
        sub: The subparser registry.
    """
    recover = sub.add_parser(
        "recover",
        help="Rebuild a run's manifest from its journal. Opens no browser",
    )
    recover.add_argument(
        "--run-id", required=True,
        help="Identity of the run to rebuild, as it appears in "
             "data/run_journal_<run-id>.ndjson",
    )
    recover.add_argument(
        "--data-dir", type=Path, default=DEFAULT_DATA_DIR,
        help="Directory holding the journal, and where the manifest is written "
             "(default: data/)",
    )
    recover.set_defaults(func=cmd_recover)


def _add_consolidate(sub: argparse._SubParsersAction) -> None:
    """Register the `consolidate` subcommand.

    It takes no browser arguments, because it drives no browser: joining the
    per-conversation export files into one corpus must not require opening
    WhatsApp Web (`§D4`).

    Args:
        sub: The subparser registry.
    """
    consolidate = sub.add_parser(
        "consolidate",
        help="Join data/chat_*.json into one NDJSON corpus. Opens no browser",
    )
    consolidate.add_argument(
        "--data-dir", type=Path, default=DEFAULT_DATA_DIR,
        help="Directory holding the per-conversation export files and, unless "
             "--from-manifest is given, the run manifests (default: data/)",
    )
    consolidate.add_argument(
        "--from-manifest", type=Path, default=None,
        help="Name the source run from this manifest path explicitly, instead "
             "of picking the newest run_manifest_*.json under --data-dir",
    )
    consolidate.add_argument(
        "--out", type=Path, default=None,
        help="Output file (default: <data-dir>/corpus_<source-run>.ndjson)",
    )
    consolidate.set_defaults(func=cmd_consolidate)


def build_parser() -> argparse.ArgumentParser:
    """The `wa-extract` command line.

    Returns:
        argparse.ArgumentParser: Parser with every subcommand registered.
    """
    parser = argparse.ArgumentParser(
        prog="wa-extract",
        description="WhatsApp Web text export (one chat, or every chat).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _add_login(sub)
    _add_export_one(sub)
    _add_export_all(sub)
    _add_recover(sub)
    _add_consolidate(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI main. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except TimeoutError as exc:
        logger.error("%s", exc)
        return 2
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
