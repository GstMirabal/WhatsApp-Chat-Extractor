"""Sender and timestamp extraction from a message row (no browser).

These two functions shipped in #003 and were wrong in production for two
sprints: 214 of the 217 messages in the first full export carried a time of day
in `sender`, and `timestamp` carried message text. Nothing caught it because
nothing tested them — the row was a live Playwright handle and the export was
only ever checked by counting messages.

The stubs below stand in for that handle. What they cannot cover is the JS
expression inside `_row_sender`, which only a browser can evaluate; the stub
supplies its result, so what is under test here is the branching around it.
"""

from __future__ import annotations

import pytest

from whatsapp_chat_extractor.export_one import (
    _row_sender,
    _row_timestamp,
    is_load_earlier_label,
    sender_from_speaker_label,
)


class FakeNode:
    """A DOM node exposing only what the extractors ask of it."""

    def __init__(self, *, attributes: dict[str, str] | None = None, text: str = "") -> None:
        self._attributes = attributes or {}
        self._text = text

    def get_attribute(self, name: str) -> str | None:
        return self._attributes.get(name)

    def inner_text(self) -> str:
        return self._text


class FakeRow:
    """A message row.

    `data_id` defaults to empty because that is the interesting case: current WA
    Web builds put neither `.message-in` nor `.message-out` on an ancestor, so a
    row with no id is exactly the row that came out as `unknown` in production.
    """

    def __init__(
        self,
        *,
        side: str = "",
        data_id: str = "",
        aria_labels: tuple[str, ...] = (),
        nodes: dict[str, FakeNode] | None = None,
    ) -> None:
        self._side = side
        self._data_id = data_id
        self._aria = aria_labels
        self._nodes = nodes or {}

    def query_selector_all(self, selector: str) -> list[FakeNode]:
        if selector == "[aria-label]":
            return [FakeNode(attributes={"aria-label": v}) for v in self._aria]
        return []

    def get_attribute(self, name: str) -> str | None:
        return self._data_id if name == "data-id" else None

    def evaluate(self, script: str) -> str:
        if "data-id" in script:
            return self._data_id
        return self._side

    def query_selector(self, selector: str) -> FakeNode | None:
        return self._nodes.get(selector)


PRE_SELECTOR = "[data-pre-plain-text]"
META_SELECTOR = '[data-testid="msg-meta"] span'
CHECK_SELECTOR = '[data-testid="msg-dblcheck"], [data-testid="msg-check"]'


TITLE = "Ana Pérez García"
TAIL_OUT = '[data-testid="tail-out"], [data-icon="tail-out"]'
TAIL_IN = '[data-testid="tail-in"], [data-icon="tail-in"]'


def test_bubble_tail_out_is_me() -> None:
    row = FakeRow(nodes={TAIL_OUT: FakeNode()})
    assert _row_sender(row, chat_title=TITLE) == "me"


def test_bubble_tail_in_is_contact() -> None:
    row = FakeRow(nodes={TAIL_IN: FakeNode()})
    assert _row_sender(row, chat_title=TITLE) == "contact"


def test_media_row_without_a_tail_falls_back_to_the_aria_label() -> None:
    """A photo or voice note carries the label but no tail."""
    row = FakeRow(aria_labels=(f"{TITLE}:", "Abrir foto"))
    assert _row_sender(row, chat_title=TITLE) == "contact"
    own = FakeRow(aria_labels=("Tú:", "Reproducir mensaje de voz"))
    assert _row_sender(own, chat_title=TITLE) == "me"


def test_consecutive_message_without_tail_or_aria_uses_pre_plain_text() -> None:
    """WhatsApp draws the tail only on the first message of a run.

    Rows 9-11 of the live probe had neither tail nor aria-label, and every one
    of them came out `unknown` before this fallback existed.
    """
    row = FakeRow(
        nodes={
            PRE_SELECTOR: FakeNode(
                attributes={"data-pre-plain-text": f"[11:23, 27/8/2026] {TITLE}: "}
            )
        }
    )
    assert _row_sender(row, chat_title=TITLE) == "contact"


def test_a_row_with_no_signal_at_all_is_unknown() -> None:
    assert _row_sender(FakeRow(), chat_title=TITLE) == "unknown"


def test_sender_falls_back_to_delivery_checks_for_outgoing() -> None:
    row = FakeRow(nodes={CHECK_SELECTOR: FakeNode()})
    assert _row_sender(row, chat_title=TITLE) == "me"


def test_speaker_label_matching_the_title_is_the_contact() -> None:
    assert sender_from_speaker_label(TITLE, TITLE) == "contact"
    assert sender_from_speaker_label(TITLE.upper(), TITLE) == "contact"


def test_any_other_speaker_label_is_the_operator() -> None:
    assert sender_from_speaker_label("Tú", TITLE) == "me"
    assert sender_from_speaker_label("You", TITLE) == "me"


def test_speaker_label_yields_nothing_without_both_sides() -> None:
    assert sender_from_speaker_label("", TITLE) == ""
    assert sender_from_speaker_label(TITLE, "") == ""


def test_the_speaker_name_is_never_returned() -> None:
    """The label is read to compare, then discarded — the constraint asserted."""
    row = FakeRow(aria_labels=(f"{TITLE}:",))
    assert _row_sender(row, chat_title=TITLE) in {"me", "contact", "unknown"}
    assert "Ana" not in _row_sender(row, chat_title=TITLE)


def test_unattributable_row_reports_unknown_rather_than_guessing() -> None:
    assert _row_sender(FakeRow(side="")) == "unknown"


def test_sender_is_never_a_clock() -> None:
    """The original production defect: a time of day recorded as the sender."""
    row = FakeRow(
        nodes={
            PRE_SELECTOR: FakeNode(
                attributes={"data-pre-plain-text": f"[11:23, 27/8/2026] {TITLE}: "}
            )
        },
    )
    role = _row_sender(row, chat_title=TITLE)
    assert role not in {"11:23", "27/8/2026"}
    assert role == "contact"


def test_sender_is_never_a_personal_name() -> None:
    """Even when the DOM offers the name, the role is what gets recorded."""
    row = FakeRow(
        nodes={
            PRE_SELECTOR: FakeNode(
                attributes={"data-pre-plain-text": f"[11:23, 27/8/2026] {TITLE}: "}
            )
        },
    )
    role = _row_sender(row, chat_title=TITLE)
    assert "Ana" not in role
    assert "Pérez" not in role


def test_timestamp_comes_from_the_descendant_attribute() -> None:
    row = FakeRow(
        nodes={
            PRE_SELECTOR: FakeNode(
                attributes={"data-pre-plain-text": "[11:23, 27/8/2026] Ana Pérez: "}
            )
        }
    )
    assert _row_timestamp(row) == "11:23, 27/8/2026"


def test_timestamp_discards_the_name_that_follows_it() -> None:
    row = FakeRow(
        nodes={
            PRE_SELECTOR: FakeNode(
                attributes={"data-pre-plain-text": "[11:23, 27/8/2026] Ana Pérez: "}
            )
        }
    )
    assert "Ana" not in _row_timestamp(row)


def test_timestamp_never_returns_message_body() -> None:
    """The old fallback read `div.copyable-text`, whose inner text is the body."""
    row = FakeRow(nodes={META_SELECTOR: FakeNode(text="Importante apúntalo, trampa")})
    assert _row_timestamp(row) == ""


def test_timestamp_accepts_a_clock_shaped_meta_fallback() -> None:
    row = FakeRow(nodes={META_SELECTOR: FakeNode(text="11:23")})
    assert _row_timestamp(row) == "11:23"


def test_timestamp_is_empty_when_the_row_offers_nothing() -> None:
    assert _row_timestamp(FakeRow()) == ""


@pytest.mark.parametrize(
    "label",
    [
        "Cargar mensajes anteriores",
        "CARGAR MENSAJES ANTERIORES",
        "HAZ CLIC AQUÍ PARA VER LOS MENSAJES MÁS ANTIGUOS DE TU TELÉFONO",
        "Haz clic aquí para obtener mensajes más antiguos de tu teléfono",
        "Mensajes mas antiguos",
        "Load earlier messages",
        "CLICK HERE TO GET OLDER MESSAGES FROM YOUR PHONE",
        "Older messages",
    ],
)
def test_load_earlier_labels_are_recognised(label: str) -> None:
    """The operator had to click this by hand: the matcher missed every form."""
    assert is_load_earlier_label(label)


@pytest.mark.parametrize(
    "label",
    ["Enviar", "Send", "Adjuntar", "", "Buscar", "Ok!", "Mensaje"],
)
def test_ordinary_controls_are_not_mistaken_for_the_loader(label: str) -> None:
    assert not is_load_earlier_label(label)


@pytest.mark.parametrize(
    "body",
    [
        "Haz clic aquí para ver la oferta",
        "haz clic aqui y te lo mando",
        "Click here to see the photos",
        "Te reenvío esto, haz clic aquí: https://example.com/promo",
    ],
)
def test_message_text_that_says_click_here_is_not_the_loader(body: str) -> None:
    """The harvester clicked links inside the conversation because of this.

    `haz clic aquí` was an alternative in the pattern on its own, and it is
    ordinary message content. Every alternative requires the noun now.
    """
    assert not is_load_earlier_label(body)


def test_a_long_message_quoting_the_control_is_not_the_loader() -> None:
    """A bubble can quote the wording; a control's own label stays short."""
    quoted = (
        "Oye, cuando abras el chat en el ordenador te sale un aviso arriba que "
        "pone cargar mensajes anteriores, dale ahí y te aparece todo lo que "
        "hablamos el mes pasado, que si no no lo vas a encontrar nunca"
    )
    assert len(quoted) > 120
    assert not is_load_earlier_label(quoted)
