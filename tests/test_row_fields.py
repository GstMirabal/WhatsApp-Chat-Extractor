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
    sender_from_message_id,
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
        nodes: dict[str, FakeNode] | None = None,
    ) -> None:
        self._side = side
        self._data_id = data_id
        self._nodes = nodes or {}

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


def test_direction_comes_from_the_message_id() -> None:
    """The signal that actually survives WA Web rewrites.

    A 513-message live export had every sender set to `unknown`: the rows carry
    no `.message-in`/`.message-out` ancestor any more. The `data-id` states the
    direction in its first component and did so all along.
    """
    assert sender_from_message_id("true_34600111222@c.us_3EB0ABC") == "me"
    assert sender_from_message_id("false_34600111222@c.us_3EB0ABC") == "contact"
    assert sender_from_message_id("sha1:deadbeef") == ""
    assert sender_from_message_id("") == ""


def test_row_with_an_outgoing_id_is_attributed_to_me() -> None:
    row = FakeRow(data_id="true_34600111222@c.us_3EB0ABC")
    assert _row_sender(row) == "me"


def test_row_with_an_incoming_id_is_attributed_to_contact() -> None:
    row = FakeRow(data_id="false_34600111222@c.us_3EB0ABC")
    assert _row_sender(row) == "contact"


def test_the_id_wins_over_a_stale_class_ancestor() -> None:
    row = FakeRow(side="contact", data_id="true_34600111222@c.us_3EB0ABC")
    assert _row_sender(row) == "me"


def test_a_precomputed_id_is_used_without_touching_the_dom() -> None:
    """`collect_visible_rows` reads the id once and hands it on."""
    row = FakeRow()
    assert _row_sender(row, "true_34600111222@c.us_3EB0ABC") == "me"


def test_outgoing_row_is_attributed_to_me() -> None:
    assert _row_sender(FakeRow(side="me")) == "me"


def test_incoming_row_is_attributed_to_contact() -> None:
    assert _row_sender(FakeRow(side="contact")) == "contact"


def test_sender_falls_back_to_delivery_checks_for_outgoing() -> None:
    row = FakeRow(side="", nodes={CHECK_SELECTOR: FakeNode()})
    assert _row_sender(row) == "me"


def test_unattributable_row_reports_unknown_rather_than_guessing() -> None:
    assert _row_sender(FakeRow(side="")) == "unknown"


def test_sender_is_never_a_clock() -> None:
    """The exact production defect: a time of day recorded as the sender."""
    row = FakeRow(
        side="contact",
        nodes={
            PRE_SELECTOR: FakeNode(
                attributes={"data-pre-plain-text": "[11:23, 27/8/2026] Ana Pérez: "}
            )
        },
    )
    assert _row_sender(row) not in {"11:23", "27/8/2026"}
    assert _row_sender(row) == "contact"


def test_sender_is_never_a_personal_name() -> None:
    """Even when the DOM offers the name, the role is what gets recorded."""
    row = FakeRow(
        side="contact",
        nodes={
            PRE_SELECTOR: FakeNode(
                attributes={"data-pre-plain-text": "[11:23, 27/8/2026] Ana Pérez: "}
            )
        },
    )
    assert "Ana" not in _row_sender(row)
    assert "Pérez" not in _row_sender(row)


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
