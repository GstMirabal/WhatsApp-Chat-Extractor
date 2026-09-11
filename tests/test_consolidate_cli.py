"""CLI orchestration of `consolidate`, driven through the real argument parser.

No browser: `consolidate` opens none (`__main__.py` `_add_consolidate`
docstring, `§D4`), so this file follows the `monkeypatch`-and-no-browser idiom
of `tests/test_resume.py` and drives the command the way
`tests/test_export_all.py` drives `export-all` — through
`cli.build_parser().parse_args([...])` and the resulting `args.func`, never a
hand-built `argparse.Namespace`, so a flag-name typo in `_add_consolidate`
would fail here too.

The fixtures below mirror `tests/test_consolidate.py`'s `a_chat` and
`write_chat_file` idiom rather than importing them, keeping this file's setup
independent of that module's internals.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import pytest

from whatsapp_chat_extractor import __main__ as cli
from whatsapp_chat_extractor.writers import MessageRecord, build_export


def _synthetic_chat(title: str) -> dict:
    """Build one real schema v6 export for `title`, via `writers.build_export`.

    Args:
        title: Synthetic chat title (`ADR-0001`), hashed into `chat_id` and
            never stored.

    Returns:
        dict: The export payload as `build_export` produces it.
    """
    messages: list[MessageRecord] = [
        {
            "message_id": "m1",
            "sender": "contact",
            "timestamp": "10:00, 1/1/2026",
            "timestamp_iso": "2026-01-01T10:00:00",
            "body": "hola",
            "kind": "text",
            "order": 0,
        }
    ]
    return build_export(
        chat_title=title,
        messages=messages,
        completeness="proven",
        stopped_reason="chat_start",
    )


def _write_chat_file(data_dir: Path, filename: str, chat: dict) -> Path:
    """Write `chat` as a `chat_*.json` file the CLI's `consolidate` can read.

    Args:
        data_dir: Directory to write under.
        filename: Exact filename, chosen by the caller to control read order.
        chat: The parsed export payload to serialize.

    Returns:
        Path: The written file.
    """
    path = data_dir / filename
    path.write_text(json.dumps(chat, ensure_ascii=False), encoding="utf-8")
    return path


def _consolidate_args(data_dir: Path, extra: list[str] | None = None) -> argparse.Namespace:
    """Parse a real `consolidate` command line the way the CLI itself would.

    Args:
        data_dir: Value passed to `--data-dir`.
        extra: Additional argv tokens appended after `--data-dir`.

    Returns:
        argparse.Namespace: The parsed arguments, with `func` set by
            `_add_consolidate`.
    """
    argv = ["consolidate", "--data-dir", str(data_dir), *(extra or [])]
    return cli.build_parser().parse_args(argv)


def test_two_v6_files_produce_a_three_line_corpus_and_exit_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A regression in `read_chat_files`, `build_header` or `write_corpus`
    wiring inside `cmd_consolidate` would change the line count or the exit
    code; both are asserted here, not just one.
    """
    _write_chat_file(tmp_path, "chat_1.json", _synthetic_chat("Ana"))
    _write_chat_file(tmp_path, "chat_2.json", _synthetic_chat("Beto"))
    args = _consolidate_args(tmp_path)

    exit_code = args.func(args)

    assert exit_code == 0
    out_path = tmp_path / "corpus_unknown.ndjson"
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert capsys.readouterr().out.strip() == str(out_path)


def test_duplicate_chat_id_exits_two_and_writes_no_corpus_file(tmp_path: Path) -> None:
    """A regression that swallowed `ValueError` or wrote before validating
    would either exit `0` or leave a corpus file behind; both are checked.
    """
    chat = _synthetic_chat("Ana")
    _write_chat_file(tmp_path, "chat_dup_1.json", chat)
    _write_chat_file(tmp_path, "chat_dup_2.json", dict(chat))
    args = _consolidate_args(tmp_path)

    exit_code = args.func(args)

    assert exit_code == 2
    assert list(tmp_path.glob("corpus_*.ndjson")) == []


def test_explicit_out_overrides_the_default_corpus_path(tmp_path: Path) -> None:
    """A regression that ignored `args.out` in favor of the default name would
    leave the custom path missing and write the default one instead.
    """
    _write_chat_file(tmp_path, "chat_1.json", _synthetic_chat("Ana"))
    _write_chat_file(tmp_path, "chat_2.json", _synthetic_chat("Beto"))
    custom_out = tmp_path / "custom" / "picked.ndjson"
    args = _consolidate_args(tmp_path, ["--out", str(custom_out)])

    exit_code = args.func(args)

    assert exit_code == 0
    assert custom_out.is_file()
    assert not (tmp_path / "corpus_unknown.ndjson").exists()


def test_consolidate_runs_with_playwright_unimportable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A regression that made `cmd_consolidate` import `playwright` at call
    time — even indirectly through a new import at module load — would raise
    `ImportError` here instead of returning `0`, proving `§D4` by execution
    rather than by reading `_add_consolidate`'s docstring.

    Neither `tests/test_export_all.py` nor `tests/test_resume.py` installs a
    `sys.meta_path` import blocker, so this follows the plan's `monkeypatch`
    fallback: poisoning `sys.modules["playwright"]` makes `import playwright`
    raise `ImportError`, confirmed below before `consolidate` is run.
    """
    monkeypatch.setitem(sys.modules, "playwright", None)
    with pytest.raises(ImportError):
        importlib.import_module("playwright")
    _write_chat_file(tmp_path, "chat_1.json", _synthetic_chat("Ana"))
    args = _consolidate_args(tmp_path)

    exit_code = args.func(args)

    assert exit_code == 0
