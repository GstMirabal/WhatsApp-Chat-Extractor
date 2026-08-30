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

from whatsapp_chat_extractor.export_one import _row_sender, _row_timestamp


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
    """A message row: a JS side verdict plus a fixed selector-to-node map."""

    def __init__(
        self,
        *,
        side: str = "",
        nodes: dict[str, FakeNode] | None = None,
    ) -> None:
        self._side = side
        self._nodes = nodes or {}

    def evaluate(self, script: str) -> str:
        return self._side

    def query_selector(self, selector: str) -> FakeNode | None:
        return self._nodes.get(selector)


PRE_SELECTOR = "[data-pre-plain-text]"
META_SELECTOR = '[data-testid="msg-meta"] span'
CHECK_SELECTOR = '[data-testid="msg-dblcheck"], [data-testid="msg-check"]'


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
