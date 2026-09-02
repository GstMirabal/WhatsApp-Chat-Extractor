"""Turn WhatsApp's rendered timestamp into one that can be compared.

`export_one._row_timestamp` returns the string WhatsApp painted, taken from
`data-pre-plain-text="[HH:MM, D/M/YYYY] Name: "`. That string is not a time: its
day/month order follows the browser's locale, it carries no zone, and the
`msg-meta` fallback yields only `HH:MM` with no date at all. A corpus of those
cannot answer how long a reply took, or what hour of the day the conversation
happened — the first questions a support corpus is read for (`ADR-0001`).

This module produces the comparable form. It does **not** replace the rendered
string: `MessageRecord` keeps both, so if this parse turns out to be wrong it
can be redone against files already on disk without reopening WhatsApp Web.

**Only locales this module has been told the shape of are parsed.** The browser
locale is pinned by `session.launch_context`, so exactly one format reaches
here; an unrecognised locale returns the empty string rather than guessing an
order. Guessing is how `13/9` and `9/13` become the same date, and `KI-004-A`
already forbids classifying what has not been measured.

**A row with no date yields the empty string, never an invented one.** The
tempting fix — borrow the day from the export's own date — would silently place
a message from last year on today. `writers.build_export` counts the empties as
`undated_messages` instead, so the corpus reports its own gaps.
"""

from __future__ import annotations

import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

# `[14:32, 3/9/2026]` after `_row_timestamp` has stripped the brackets. The year
# is optional in width because WhatsApp renders two digits in some builds.
RENDERED_RE = re.compile(
    r"^(?P<hour>\d{1,2}):(?P<minute>\d{2})"
    r"(?::\d{2})?"
    r"\s*,\s*"
    r"(?P<first>\d{1,2})/(?P<second>\d{1,2})/(?P<year>\d{2}|\d{4})$"
)

# Order of the two numeric date components, per locale. Only locales whose
# rendering has actually been observed are listed: an absent locale is answered
# with "" rather than with a default that happens to be right in Europe.
DAY_FIRST = "day_first"
MONTH_FIRST = "month_first"
LOCALE_DATE_ORDER = {
    "es-ES": DAY_FIRST,
    "es": DAY_FIRST,
    "en-GB": DAY_FIRST,
    "en-US": MONTH_FIRST,
}

# Two-digit years: WhatsApp shows no conversation older than the product, so a
# `26` is 2026 and never 1926.
CENTURY = 2000


def date_order(locale: str) -> str | None:
    """Which of the two numeric date components comes first, for one locale.

    Args:
        locale: BCP 47 tag as passed to the browser, e.g. ``es-ES``.

    Returns:
        str | None: ``day_first``, ``month_first``, or None when the locale's
            rendering has not been observed and must not be assumed.
    """
    tag = (locale or "").strip()
    if tag in LOCALE_DATE_ORDER:
        return LOCALE_DATE_ORDER[tag]
    return LOCALE_DATE_ORDER.get(tag.split("-")[0].lower())


def _components(match: re.Match[str], order: str) -> tuple[int, int, int, int, int]:
    """Year, month, day, hour and minute from a matched rendering.

    Args:
        match: A successful :data:`RENDERED_RE` match.
        order: ``day_first`` or ``month_first``.

    Returns:
        tuple: ``(year, month, day, hour, minute)``, not yet validated as a real
            calendar date.
    """
    first = int(match.group("first"))
    second = int(match.group("second"))
    day, month = (first, second) if order == DAY_FIRST else (second, first)
    year = int(match.group("year"))
    if year < 100:
        year += CENTURY
    return year, month, day, int(match.group("hour")), int(match.group("minute"))


def parse_rendered(raw: str, *, locale: str) -> str:
    """The rendered timestamp as ``YYYY-MM-DDTHH:MM``, or ``""``.

    No timezone is attached. The zone the browser rendered in is recorded once
    per file as ``ChatExport.source_timezone`` rather than repeated on every
    message, and inventing an offset here would state a precision the DOM never
    carried.

    Args:
        raw: The bracketed text ``export_one._row_timestamp`` returned, such as
            ``"14:32, 3/9/2026"``. May be empty or hold only a clock.
        locale: The locale the page was rendered under, from
            ``session.DEFAULT_LOCALE`` or the operator's override.

    Returns:
        str: ISO-8601 local date and time to the minute, or ``""`` when the
            input carries no date, the locale is unknown, or the date is not a
            real one. Never a date inferred from anything outside ``raw``.
    """
    order = date_order(locale)
    if order is None:
        logger.warning(
            "Locale %r has no observed date order, so %r is left unparsed. Add it "
            "to LOCALE_DATE_ORDER only once its rendering has been seen.",
            locale, raw,
        )
        return ""
    match = RENDERED_RE.match((raw or "").strip())
    if match is None:
        return ""
    year, month, day, hour, minute = _components(match, order)
    if not _is_real(year, month, day, hour, minute):
        return ""
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}"


def _is_real(year: int, month: int, day: int, hour: int, minute: int) -> bool:
    """Whether these components name a moment that exists.

    Catches the case the locale table cannot: a `month_first` reading of
    ``13/9`` gives month 13, which proves the order was wrong rather than the
    date unusual.

    Args:
        year: Four-digit year.
        month: 1-12 if the reading was right.
        day: 1-31 if the reading was right.
        hour: 0-23.
        minute: 0-59.

    Returns:
        bool: True when the date is a real calendar date and the clock is valid.
    """
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return False
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def undated_count(iso_stamps: list[str]) -> int:
    """How many messages this export could not place on a calendar.

    Counted and written into the file (`ChatExport.undated_messages`) so the
    corpus reports its own gaps: the fraction of rows WhatsApp renders without
    a date has never been measured, and the first whole-account run under
    schema v6 measures it without needing a live probe.

    Args:
        iso_stamps: Every message's ``timestamp_iso``, in export order.

    Returns:
        int: How many are empty.
    """
    return sum(1 for stamp in iso_stamps if not stamp)
