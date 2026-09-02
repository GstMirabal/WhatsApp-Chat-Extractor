"""The `--resume` orchestration of a whole-account run.

`IMPLEMENTATION_PLAN.md` §D3: a resume re-enumerates the chat list rather than
trusting the journal for what still exists — the journal states what was done,
never what the chat list currently holds. This module drives `cmd_export_all`
itself, not `_export_every_chat` in isolation, because the property under test
is what `--resume` wires together: a journal already on disk from an earlier
pass, a fresh sweep over the same three conversations, and a manifest rebuilt
from the journal file (`_manifest_from_journal_file`) rather than assembled
only from what this pass attempted.

No browser. `_export_all_session` is replaced with a stand-in that calls
`_export_every_chat` directly, following the `monkeypatch` pattern of
`tests/test_export_all.py`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from whatsapp_chat_extractor import __main__ as cli
from whatsapp_chat_extractor.journal import (
    append_outcome,
    journal_path,
    open_journal,
    write_header,
)
from whatsapp_chat_extractor.manifest import exported, now
from whatsapp_chat_extractor.writers import pseudonymous_chat_id

RUN_ID = "20260101T000000Z"


def refs_for(titles: list[str]) -> list[dict]:
    """Build `ChatRef`-shaped entries the way `sweep_until_stable` would."""
    return [
        {"chat_id": pseudonymous_chat_id(title), "index": index}
        for index, title in enumerate(titles)
    ]


def an_args(**overrides: object) -> argparse.Namespace:
    """A parsed `export-all` command line, minimal enough to drive the walk."""
    defaults = {
        "settle_ms": 0, "limit": 0, "data_dir": Path("data"),
        "max_passes": 10, "stall_threshold": 3, "load_wait_ms": 0,
        "resume": "", "write_index": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def write_prior_pass(tmp_path: Path, titles: list[str]) -> Path:
    """Write a journal as if an earlier pass had already exported the first two.

    Args:
        tmp_path: Where the journal lives.
        titles: The three conversations, in enumeration order. Only the first
            two are recorded as `exported`; the third was never reached, as if
            the process had died before opening it.

    Returns:
        Path: The journal file written.
    """
    handle = open_journal(RUN_ID, data_dir=tmp_path)
    try:
        write_header(
            handle, run_id=RUN_ID, started_at=now(),
            chats_enumerated=len(titles), enumeration="converged", sweeps=1,
        )
        for position, title in enumerate(titles[:2]):
            append_outcome(handle, exported(
                pseudonymous_chat_id(title), index=position,
                completeness="unproven", message_count=3, file=f"{title}.json",
            ))
    finally:
        handle.close()
    return journal_path(RUN_ID, data_dir=tmp_path)


def test_resume_reopens_only_the_unexported_chat_and_the_manifest_carries_all_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C3: 2 of 3 already `exported` on disk; the resumed pass must not re-open them.

    `open_chat_by_digest` is called exactly once — for the third conversation —
    and the rebuilt manifest still names all three, because it is read back
    from the journal file rather than assembled only from what this pass
    attempted. The sweep still runs and still finds all three (`§D3`): the
    resume skips *opening* two chats, never the re-enumeration itself.
    """
    titles = ["Ana", "Beto", "Caro"]
    write_prior_pass(tmp_path, titles)

    monkeypatch.setattr(
        cli, "sweep_until_stable",
        lambda page, **kw: {
            "refs": refs_for(titles), "enumeration": "converged", "sweeps": 3,
        },
    )
    monkeypatch.setattr(
        cli, "_export_open_chat",
        lambda page, title, args: (
            {"completeness": "unproven", "messages": [1, 2, 3]},
            Path(f"{pseudonymous_chat_id(title)}.json"),
        ),
    )
    opened: list[str] = []

    def counting_open(page: object, ref: dict, **kw: object) -> str:
        opened.append(ref["chat_id"])
        return {pseudonymous_chat_id(t): t for t in titles}[ref["chat_id"]]

    monkeypatch.setattr(cli, "open_chat_by_digest", counting_open)
    monkeypatch.setattr(
        cli, "_export_all_session",
        lambda args, journal: cli._export_every_chat(object(), args, journal=journal),
    )

    exit_code = cli.cmd_export_all(an_args(resume=RUN_ID, data_dir=tmp_path))

    assert opened == [pseudonymous_chat_id("Caro")]
    manifest_files = list(tmp_path.glob("run_manifest_*.json"))
    assert len(manifest_files) == 1
    manifest = json.loads(manifest_files[0].read_text(encoding="utf-8"))
    assert {chat["chat_id"] for chat in manifest["chats"]} == {
        pseudonymous_chat_id(title) for title in titles
    }
    assert manifest["counts"]["exported"] == 3
    assert manifest["chats_enumerated"] == 3
    assert exit_code == 0
