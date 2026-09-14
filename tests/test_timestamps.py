"""Whether a rendered timestamp becomes a comparable one, or honestly nothing.

Two failure modes are worse here than returning nothing, and most of these cases
exist to pin them:

1. **Reading the date in the wrong order.** `3/9` is a valid date under both
   readings and silently becomes the wrong day. Only `13/9` and above prove
   which order was used, so those are the cases that can actually fail.
2. **Inventing a date** for a row that carried only a clock. That would place a
   message from months ago on the day of the export.
"""

from __future__ import annotations

import pytest

from whatsapp_chat_extractor.timestamps import (
    DAY_FIRST,
    MONTH_FIRST,
    date_order,
    parse_rendered,
    undated_count,
)

ES = "es-ES"


def test_the_rendered_stamp_becomes_iso_to_the_minute() -> None:
    assert parse_rendered("14:32, 3/9/2026", locale=ES) == "2026-09-03T14:32"


def test_a_day_above_twelve_proves_the_order_is_day_first() -> None:
    """The only shape that can distinguish `D/M` from `M/D`.

    Under `es-ES` this must be 13 September. A `month_first` reading would ask
    for month 13 and be rejected as unreal, so a regression here shows up as
    `""` rather than as a plausible wrong date.
    """
    assert parse_rendered("09:05, 13/9/2026", locale=ES) == "2026-09-13T09:05"


def test_the_same_string_is_unreadable_under_a_month_first_locale() -> None:
    """`13` is not a month, so `en-US` correctly refuses it rather than guessing."""
    assert parse_rendered("09:05, 13/9/2026", locale="en-US") == ""


def test_a_month_first_locale_reads_its_own_order() -> None:
    assert parse_rendered("09:05, 9/13/2026", locale="en-US") == "2026-09-13T09:05"


def test_a_clock_without_a_date_yields_nothing_not_todays_date() -> None:
    """The `msg-meta` fallback in `_row_timestamp` returns exactly this shape."""
    assert parse_rendered("14:32", locale=ES) == ""


def test_an_empty_stamp_yields_nothing() -> None:
    assert parse_rendered("", locale=ES) == ""


def test_message_body_text_is_never_mistaken_for_a_timestamp() -> None:
    """`_row_timestamp` once fell back to `div.copyable-text`, whose text is the body."""
    assert parse_rendered("Hola, te confirmo el pedido", locale=ES) == ""
    assert parse_rendered("13/9/2026 nos vemos", locale=ES) == ""


def test_an_unobserved_locale_refuses_rather_than_assuming_an_order() -> None:
    """`KI-004-A`: a locale nobody has seen rendered is not evidence of a format."""
    assert parse_rendered("14:32, 3/9/2026", locale="ja-JP") == ""
    assert date_order("ja-JP") is None


def test_a_bare_language_tag_resolves_to_its_order() -> None:
    assert date_order("es") == DAY_FIRST
    assert date_order("en-US") == MONTH_FIRST


@pytest.mark.parametrize(
    "raw",
    ["14:32, 31/2/2026", "14:32, 32/1/2026", "25:00, 3/9/2026", "14:99, 3/9/2026"],
)
def test_an_impossible_moment_yields_nothing(raw: str) -> None:
    """A date the calendar does not have is a misread, not an unusual date."""
    assert parse_rendered(raw, locale=ES) == ""


def test_a_two_digit_year_resolves_to_this_century() -> None:
    """WhatsApp shows no conversation older than the product, so `26` is 2026."""
    assert parse_rendered("14:32, 3/9/26", locale=ES) == "2026-09-03T14:32"


def test_seconds_are_accepted_and_dropped_to_the_minute() -> None:
    assert parse_rendered("14:32:07, 3/9/2026", locale=ES) == "2026-09-03T14:32"


def test_surrounding_whitespace_does_not_defeat_the_parse() -> None:
    assert parse_rendered("  14:32, 3/9/2026  ", locale=ES) == "2026-09-03T14:32"


def test_no_timezone_is_attached_to_a_message() -> None:
    """The zone is recorded once per file, never inferred per row."""
    parsed = parse_rendered("14:32, 3/9/2026", locale=ES)

    assert not parsed.endswith("Z")
    assert "+" not in parsed


def test_undated_messages_are_counted_so_the_corpus_reports_its_own_gaps() -> None:
    assert undated_count(["2026-09-03T14:32", "", "2026-09-03T14:40", ""]) == 2
    assert undated_count([]) == 0
