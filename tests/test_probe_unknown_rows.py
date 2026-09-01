"""What the unknown-row probe records, and what it must never record.

No browser: rows are fakes exposing the two surfaces the probe uses,
`query_selector` and `evaluate`.

The failure this file exists to prevent is a privacy one. The probe reads
`aria-label` and `data-pre-plain-text` — the two attributes that carry the
sender's real name — to decide whether they are *present*. A signature that
leaked either value would put names into a file, which `ADR-0001` forbids by
default and which no amount of gitignoring makes acceptable.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "probe_unknown_rows", Path(__file__).resolve().parents[1] / "scripts"
    / "probe_unknown_rows.py",
)
assert _SPEC and _SPEC.loader
probe = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(probe)


REAL_NAME = "Ana Martinez"


class FakeNode:
    """A descendant carrying one attribute and, optionally, text."""

    def __init__(self, attribute: str, value: str, text: str = "") -> None:
        self._attribute = attribute
        self._value = value
        self._text = text

    def get_attribute(self, name: str) -> str | None:
        return self._value if name == self._attribute else None

    def inner_text(self) -> str:
        return self._text


class FakeRow:
    """A message row: a set of matching selectors and a structural shape."""

    BODY_SELECTOR = (
        'span.selectable-text, span[data-testid="msg-text"], div.copyable-text'
    )

    def __init__(
        self,
        matching: tuple[str, ...] = (),
        *,
        body: str = "",
        attributes: tuple[str, ...] = ("class",),
        aria_label: str = "",
    ) -> None:
        self._matching = matching
        self._body = body
        self._attributes = attributes
        self._aria_label = aria_label

    def query_selector(self, selector: str) -> object | None:
        if selector == self.BODY_SELECTOR:
            return FakeNode("", "", self._body) if self._body else None
        if selector == "[data-pre-plain-text]":
            if "data-pre-plain-text" not in self._attributes:
                return None
            return FakeNode("data-pre-plain-text", f"[10:30, 1/1/2026] {REAL_NAME}: ")
        return object() if selector in self._matching else None

    def query_selector_all(self, selector: str) -> list[FakeNode]:
        if selector == "[aria-label]" and self._aria_label:
            return [FakeNode("aria-label", self._aria_label)]
        return []

    def evaluate(self, js: str) -> dict[str, object]:
        return {
            "attributes": sorted(self._attributes),
            "classes": ["message"],
            "has_aria_label": bool(self._aria_label),
            "has_pre_plain_text": "data-pre-plain-text" in self._attributes,
            "aria_label_ends_with_colon": self._aria_label.strip().endswith(":"),
            "child_count": 2,
        }

    def inner_text(self) -> str:
        return self._body


# --- selector reporting -----------------------------------------------------


def test_a_row_reports_which_known_selectors_matched() -> None:
    row = FakeRow((probe.SENDER_SELECTORS["tail_out"],))
    hits = probe.selector_hits(row, probe.SENDER_SELECTORS)
    assert hits["tail_out"] is True
    assert hits["tail_in"] is False


def test_every_selector_is_reported_even_when_none_match() -> None:
    """A row where the classifier had nothing to go on is the interesting case."""
    hits = probe.selector_hits(FakeRow(), probe.SENDER_SELECTORS)
    assert set(hits) == set(probe.SENDER_SELECTORS)
    assert not any(hits.values())


def test_a_selector_that_raises_does_not_end_the_probe() -> None:
    """One bad selector must not lose the other four rows' worth of evidence."""
    class Exploding(FakeRow):
        def query_selector(self, selector: str) -> object | None:
            raise RuntimeError("detached node")

    hits = probe.selector_hits(Exploding(), probe.SENDER_SELECTORS)
    assert hits == dict.fromkeys(probe.SENDER_SELECTORS, False)


# --- what a signature carries -----------------------------------------------


def test_a_row_both_classifiers_resolve_yields_no_signature() -> None:
    """The probe characterises failures; a readable row is not evidence."""
    row = FakeRow((probe.SENDER_SELECTORS["tail_out"], probe.KIND_SELECTORS["voice"]))
    assert probe.signature_for(row, chat_title=REAL_NAME) is None


def test_an_unreadable_row_yields_a_signature() -> None:
    signature = probe.signature_for(FakeRow(), chat_title=REAL_NAME)
    assert signature is not None
    assert signature["sender"] == probe.UNKNOWN
    assert signature["kind"] == probe.UNKNOWN
    assert signature["sender_selectors"] and signature["kind_selectors"]


def test_a_known_sender_with_an_unknown_kind_is_still_captured() -> None:
    """Either field failing is enough: the two rates are measured together."""
    row = FakeRow((probe.SENDER_SELECTORS["tail_in"],))
    signature = probe.signature_for(row, chat_title=REAL_NAME)
    assert signature is not None
    assert signature["sender"] == "contact"
    assert signature["kind"] == probe.UNKNOWN


# --- privacy ----------------------------------------------------------------


def test_no_attribute_value_reaches_a_signature() -> None:
    """Names live in `aria-label` and `data-pre-plain-text`. Only names of
    attributes may be recorded, never their contents."""
    row = FakeRow(
        attributes=("class", "aria-label", "data-pre-plain-text"),
        aria_label=f"{REAL_NAME}:",
    )
    signature = probe.signature_for(row, chat_title=REAL_NAME)
    assert signature is not None
    serialized = json.dumps(signature)
    assert REAL_NAME not in serialized
    assert "Ana" not in serialized
    assert signature["shape"]["has_aria_label"] is True
    assert signature["shape"]["aria_label_ends_with_colon"] is True


def test_no_message_body_reaches_a_signature() -> None:
    row = FakeRow(body="my bank card is 4111 1111 1111 1111")
    signature = probe.signature_for(row, chat_title=REAL_NAME)
    assert signature is not None
    assert "4111" not in json.dumps(signature)
    assert signature["has_body"] is True


# --- summary ----------------------------------------------------------------


def a_chat(examined: int, sender: int, kind: int) -> dict[str, object]:
    return {
        "chat_id": "chat_abc", "rows_examined": examined,
        "unknown_sender": sender, "unknown_kind": kind, "signatures": [],
    }


def test_the_summary_reports_both_rates_over_every_chat() -> None:
    summary = probe.summarize([a_chat(100, 4, 10), a_chat(100, 6, 8)])
    assert summary["rows_examined"] == 200
    assert summary["unknown_sender_rate"] == 0.05
    assert summary["unknown_kind_rate"] == 0.09


def test_a_run_that_examined_nothing_reports_zero_rather_than_dividing() -> None:
    """A run that saw nothing must be visible, not absent and not a crash."""
    summary = probe.summarize([])
    assert summary["rows_examined"] == 0
    assert summary["unknown_sender_rate"] == 0.0
    assert summary["chats"] == 0


# --- report --------------------------------------------------------------


def test_the_report_is_written_where_it_was_asked_for(tmp_path: Path) -> None:
    path = probe._write_report({"probe": "unknown_rows"}, tmp_path)
    assert path.parent == tmp_path
    assert path.name.startswith("unknown_rows_probe_")
    assert json.loads(path.read_text())["probe"] == "unknown_rows"


@pytest.mark.parametrize("argv", [[], ["--chats", "3"], ["--max-signatures", "20"]])
def test_the_command_line_parses_without_a_browser(argv: list[str]) -> None:
    """`--help` and argument parsing must work with no WhatsApp session."""
    args = probe._build_parser().parse_args(argv)
    assert args.chats >= 1
    assert args.out_dir == Path("data")
