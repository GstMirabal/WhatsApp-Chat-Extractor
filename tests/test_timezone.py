"""`--timezone` request/confirm pair: `_request_timezone` and `_confirm_timezone`.

Carried twice (Sprint 009, Sprint 010) with no test against either name at all
(`grep -rn "_request_timezone\\|_confirm_timezone" tests/` returned nothing
before this file). New file rather than an addition to an existing one: no
existing test file imports `commands` for this contract specifically —
`tests/test_export_search.py` covers `_locate_search_box`, an unrelated
selector concern in `export_one.py`, not the timezone request/confirm pair.

No browser: `_confirm_timezone` takes `page: object` and never touches it
itself — it calls `session.resolve_timezone(page)`, which is monkeypatched
here so no real Playwright `Page` is needed, following the `monkeypatch`
idiom already used in `tests/test_resume.py`.
"""

from __future__ import annotations

import os

import pytest

from whatsapp_chat_extractor import commands as cli


def test_request_timezone_sets_the_tz_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-empty `--timezone` value is exported to `TZ` for the browser
    process Chromium inherits at launch (`session.launch_context` takes no
    `timezone_id`)."""
    monkeypatch.delenv("TZ", raising=False)

    cli._request_timezone("Europe/Madrid")

    assert os.environ["TZ"] == "Europe/Madrid"


def test_request_timezone_empty_string_is_a_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No `--timezone` flag (`""`) must leave `TZ` untouched — the machine's
    own zone stands (`§D7`), rather than being cleared or set to empty."""
    monkeypatch.delenv("TZ", raising=False)

    cli._request_timezone("")

    assert "TZ" not in os.environ


def test_confirm_timezone_returns_the_resolved_zone_not_the_requested_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`_confirm_timezone` must never hand back the requested value on a
    mismatch — recording a zone the page did not use would put a false frame
    on every timestamp in the corpus (`ADR-0007`)."""
    monkeypatch.setattr(cli, "resolve_timezone", lambda page: "America/New_York")

    resolved = cli._confirm_timezone(page=object(), requested="Europe/Madrid")

    assert resolved == "America/New_York"


def test_confirm_timezone_matching_request_returns_that_zone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the page resolves exactly what was requested, that same zone is
    returned (the ordinary, non-mismatched path)."""
    monkeypatch.setattr(cli, "resolve_timezone", lambda page: "Europe/Madrid")

    resolved = cli._confirm_timezone(page=object(), requested="Europe/Madrid")

    assert resolved == "Europe/Madrid"


def test_confirm_timezone_with_no_request_returns_whatever_the_page_resolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No `--timezone` flag (`requested=""`) still returns the page's own
    resolution — `_confirm_timezone` is never skipped, only its mismatch
    warning is (an empty `requested` cannot mismatch anything)."""
    monkeypatch.setattr(cli, "resolve_timezone", lambda page: "UTC")

    resolved = cli._confirm_timezone(page=object(), requested="")

    assert resolved == "UTC"
