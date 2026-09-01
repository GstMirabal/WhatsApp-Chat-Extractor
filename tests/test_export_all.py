"""The per-chat failure policy of a whole-account run.

`IMPLEMENTATION_PLAN.md` §D3: one conversation failing must not end the run. A
run of hundreds that dies on the third wastes the manual login and the exports
already made, and the operator cannot tell how far it got. The manifest carries
the outcome of every conversation instead.

No browser. `sweep_chat_list`, `open_chat_by_digest` and the per-chat export are
replaced, because what is under test is the orchestration between them.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from whatsapp_chat_extractor import __main__ as cli
from whatsapp_chat_extractor.manifest import (
    OUTCOME_EXPORTED,
    OUTCOME_FAILED,
    OUTCOME_SKIPPED,
)
from whatsapp_chat_extractor.writers import pseudonymous_chat_id


def refs_for(titles: list[str]) -> list[dict]:
    return [
        {"chat_id": pseudonymous_chat_id(title), "index": index}
        for index, title in enumerate(titles)
    ]


def an_args(**overrides: object) -> argparse.Namespace:
    defaults = {
        "settle_ms": 0, "limit": 0, "data_dir": Path("data"),
        "max_passes": 10, "stall_threshold": 3, "load_wait_ms": 0,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


@pytest.fixture
def three_chats(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    titles = ["Ana", "Beto", "Caro"]
    monkeypatch.setattr(cli, "sweep_chat_list", lambda page, **kw: refs_for(titles))
    monkeypatch.setattr(cli, "sweep_reached_bottom", lambda page: True)
    monkeypatch.setattr(
        cli, "_export_open_chat",
        lambda page, title, args: (
            {"completeness": "unproven", "messages": [1, 2, 3]},
            Path(f"{pseudonymous_chat_id(title)}.json"),
        ),
    )
    return titles


def open_all(page: object, ref: dict, **kw: object) -> str:
    return {pseudonymous_chat_id(t): t for t in ("Ana", "Beto", "Caro")}[ref["chat_id"]]


def test_every_chat_is_exported_when_nothing_fails(
    three_chats: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "open_chat_by_digest", open_all)
    outcomes, refs, complete, index = cli._export_every_chat(object(), an_args())
    assert [o["outcome"] for o in outcomes] == [OUTCOME_EXPORTED] * 3
    assert len(refs) == 3
    assert complete is True
    assert index[pseudonymous_chat_id("Beto")] == "Beto"


def test_one_failure_does_not_end_the_run(
    three_chats: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rule §D3 exists for: the two healthy conversations still export."""
    def flaky(page: object, ref: dict, **kw: object) -> str:
        if ref["chat_id"] == pseudonymous_chat_id("Beto"):
            raise LookupError("was not found in the chat list")
        return open_all(page, ref, **kw)

    monkeypatch.setattr(cli, "open_chat_by_digest", flaky)
    outcomes, _, _, index = cli._export_every_chat(object(), an_args())
    assert [o["outcome"] for o in outcomes] == [
        OUTCOME_EXPORTED, OUTCOME_FAILED, OUTCOME_EXPORTED
    ]
    assert "was not found" in outcomes[1]["reason"]
    assert pseudonymous_chat_id("Beto") not in index


def test_a_wrong_chat_refusal_is_recorded_not_swallowed(
    three_chats: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """H-001's refusal must reach the manifest, not vanish into a warning."""
    def wrong(page: object, ref: dict, **kw: object) -> str:
        raise RuntimeError("Opened the wrong conversation")

    monkeypatch.setattr(cli, "open_chat_by_digest", wrong)
    outcomes, _, _, index = cli._export_every_chat(object(), an_args())
    assert all(o["outcome"] == OUTCOME_FAILED for o in outcomes)
    assert all("wrong conversation" in o["reason"] for o in outcomes)
    assert index == {}


def test_a_limit_records_the_rest_as_skipped_rather_than_omitting_them(
    three_chats: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An omitted conversation is indistinguishable from one that never existed."""
    monkeypatch.setattr(cli, "open_chat_by_digest", open_all)
    outcomes, refs, _, _ = cli._export_every_chat(object(), an_args(limit=1))
    assert len(outcomes) == 3
    assert outcomes[0]["outcome"] == OUTCOME_EXPORTED
    assert [o["outcome"] for o in outcomes[1:]] == [OUTCOME_SKIPPED] * 2
    assert all(o["reason"] == "beyond --limit" for o in outcomes[1:])
    assert len(refs) == 3


def test_a_failed_chat_contributes_no_messages_to_the_counts(
    three_chats: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def flaky(page: object, ref: dict, **kw: object) -> str:
        if ref["chat_id"] == pseudonymous_chat_id("Ana"):
            raise LookupError("gone")
        return open_all(page, ref, **kw)

    monkeypatch.setattr(cli, "open_chat_by_digest", flaky)
    outcomes, _, _, _ = cli._export_every_chat(object(), an_args())
    assert sum(o["message_count"] for o in outcomes) == 6


def test_a_partial_enumeration_is_carried_out_of_the_run(
    three_chats: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sweep that stopped short is not a whole-account export."""
    monkeypatch.setattr(cli, "sweep_reached_bottom", lambda page: False)
    monkeypatch.setattr(cli, "open_chat_by_digest", open_all)
    _, _, complete, _ = cli._export_every_chat(object(), an_args())
    assert complete is False
