"""Contract of the Sprint 006 chat-start probe (`scripts/probe_chat_start.py`).

Two layers, on purpose.

The verdict and termination rules are pure and run with fake page objects, like
every other test here: no browser, no WhatsApp Web.

One test is different. `test_sampled_chrome_can_miss_a_buried_marker` needs a
real Chromium, because the defect it pins lives in the probe's JavaScript and a
Python re-implementation of that JavaScript would only be testing itself. It
skips when a browser cannot be launched (a sandbox, or `playwright install`
never run), so the fast suite stays fast and green either way. It is not
decoration: it is the regression that justifies `chrome_attribute_inventory`
existing at all.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# The probe is an operator-run script, not part of the installed package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import probe_chat_start as probe

# A panel whose only start-of-conversation marker sits under a deep stack of
# attribute-less wrappers. That nesting is what a live WA panel is made of, and
# it is the condition under which sampling the first nodes goes wrong.
BURIED_MARKER_PAGE = """
<!doctype html><html><body><div id="main">
  <div data-testid="conversation-panel-messages">
    {wrappers}
    <div class="date-divider" role="row"><span>TODAY</span></div>
    <div data-testid="msg-container" data-id="x_1" class="message-in">
      <span class="selectable-text">hello</span>
    </div>
  </div>
</div></body></html>
"""
WRAPPER_DEPTH = 30
MARKER_HTML = (
    '<div data-testid="msg-system" class="message-system">'
    '<span data-icon="lock"></span></div>'
)


def buried_marker_html(depth: int = WRAPPER_DEPTH) -> str:
    """Return a page whose marker is nested ``depth`` wrappers deep."""
    opening = "<div>" * depth
    closing = "</div>" * depth
    return BURIED_MARKER_PAGE.format(wrappers=f"{opening}{MARKER_HTML}{closing}")


class FakeNode:
    """Stands in for a Playwright element handle."""

    def __init__(self, signature: dict | None = None, outside: bool = False) -> None:
        self._signature = signature or {
            "tag": "div", "attrs": {}, "has_data_id": False, "child_count": 0
        }
        self._outside = outside

    def evaluate(self, js: str, arg: object = None) -> object:
        if "closest('#pane-side')" in js:
            return self._outside
        return self._signature


class FakePage:
    """Maps a CSS selector to the nodes it should match."""

    def __init__(self, mapping: dict[str, list[FakeNode]]) -> None:
        self.mapping = mapping

    def query_selector(self, selector: str) -> FakeNode | None:
        found = self.mapping.get(selector) or []
        return found[0] if found else None

    def query_selector_all(self, selector: str) -> list[FakeNode]:
        return self.mapping.get(selector) or []


def probed(marker_found: bool, stopped_reason: str) -> dict:
    """One entry shaped like `probe_one_chat` returns it."""
    return {
        "marker": {"marker_found": marker_found},
        "scroll": {"stopped_reason": stopped_reason},
    }


# --------------------------------------------------------------- the verdict


def test_five_chats_with_no_marker_answer_h2() -> None:
    """Five chats that each reached a top and showed no marker settle H2."""
    chats = [probed(False, probe.STOP_STALLED) for _ in range(5)]
    assert probe.summarize(chats, min_chats=5)["verdict"] == "H2"


def test_one_marker_anywhere_answers_h1() -> None:
    """H1 claims the marker exists *somewhere*, so one sighting establishes it."""
    chats = [probed(False, probe.STOP_STALLED) for _ in range(4)]
    chats.append(probed(True, probe.STOP_CHAT_START))
    assert probe.summarize(chats, min_chats=5)["verdict"] == "H1"


def test_too_few_chats_decide_nothing() -> None:
    """Below the minimum the probe declines to decide rather than guessing."""
    chats = [probed(False, probe.STOP_STALLED) for _ in range(3)]
    assert probe.summarize(chats, min_chats=5)["verdict"] == "inconclusive"


def test_chats_that_only_hit_the_cap_decide_nothing() -> None:
    """A chat stopped by `max_passes` never saw its top, so it proves nothing.

    Without this, a run capped too low would report H2 from chats whose
    beginning was never reached — the strongest way this probe could lie.
    """
    chats = [probed(False, probe.STOP_MAX_PASSES) for _ in range(5)]
    assert probe.summarize(chats, min_chats=5)["verdict"] == "inconclusive"


def test_unopenable_chats_do_not_count_as_evidence() -> None:
    """A chat that failed to open is requested but not probed."""
    chats = [{"chat_id": None, "error": "refused"}]
    chats += [probed(False, probe.STOP_STALLED) for _ in range(5)]
    summary = probe.summarize(chats, min_chats=5)
    assert (summary["chats_probed"], summary["chats_requested"]) == (5, 6)


# ----------------------------------------------------------- when to stop


def test_marker_already_on_screen_stops_without_scrolling(monkeypatch) -> None:
    """A short chat can show its start immediately; that is zero passes."""
    monkeypatch.setattr(probe, "at_chat_start", lambda page: True)
    result = probe.scroll_to_top(page=None, max_passes=5)
    assert result == {"stopped_reason": probe.STOP_CHAT_START, "passes_used": 0}


def test_consecutive_dead_scrolls_report_a_stall(monkeypatch) -> None:
    """Three passes that pull nothing older end the run as `stalled`."""
    monkeypatch.setattr(probe, "at_chat_start", lambda page: False)
    monkeypatch.setattr(probe, "scroll_one_pass", lambda page, max_wait_ms=0: False)
    result = probe.scroll_to_top(page=None, max_passes=99, stall_threshold=3)
    assert result == {"stopped_reason": probe.STOP_STALLED, "passes_used": 3}


def test_the_cap_always_terminates(monkeypatch) -> None:
    """A chat that keeps yielding history still stops, and says why."""
    monkeypatch.setattr(probe, "at_chat_start", lambda page: False)
    monkeypatch.setattr(probe, "scroll_one_pass", lambda page, max_wait_ms=0: True)
    result = probe.scroll_to_top(page=None, max_passes=4)
    assert result == {"stopped_reason": probe.STOP_MAX_PASSES, "passes_used": 4}


# --------------------------------------------------------------- evidence


def test_marker_evidence_names_the_selector_that_matched() -> None:
    """Which selector fired matters: it is what a future fix would edit."""
    second = probe.CHAT_START_SELECTORS[1]
    evidence = probe.marker_evidence(FakePage({second: [FakeNode()]}))
    assert evidence["matched_selector"] == second
    assert evidence["marker_found"] is True


def test_marker_evidence_counts_every_candidate_separately() -> None:
    """A selector firing on the wrong node differs from one never firing."""
    evidence = probe.marker_evidence(FakePage({}))
    assert evidence["matched_selector"] is None
    assert set(evidence["counts_per_selector"]) == set(probe.CHAT_START_SELECTORS)


def test_missing_panel_yields_no_inventory_rather_than_an_exception() -> None:
    """One unreadable chat must not void a five-chat probe."""
    assert probe.chrome_attribute_inventory(FakePage({})) == {}
    assert probe.top_chrome_signatures(FakePage({})) == []


def test_unopenable_chat_is_recorded_and_survived(monkeypatch) -> None:
    """`probe_one_chat` degrades to an error entry instead of raising."""
    def refuse(page: object, query: str) -> str:
        raise RuntimeError("wrong chat")

    monkeypatch.setattr(probe, "open_chat_by_query", refuse)
    result = probe.probe_one_chat(FakePage({}), "x", max_passes=1)
    assert result["chat_id"] is None
    assert "wrong chat" in result["error"]


def test_no_chats_requested_is_refused() -> None:
    """The probe will not report a verdict over zero chats."""
    assert probe.main([]) == 2


# ------------------------------------------------- the regression, in a browser


@pytest.fixture(scope="module")
def chromium_page():
    """A real Chromium page, or a skip when one cannot be launched."""
    sync_playwright = pytest.importorskip(
        "playwright.sync_api", reason="playwright not installed"
    ).sync_playwright
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:  # noqa: BLE001 - reported, then skipped
            pytest.skip(f"Chromium could not be launched: {type(exc).__name__}")
        page = browser.new_page()
        try:
            yield page
        finally:
            browser.close()


def test_sampled_chrome_can_miss_a_buried_marker(chromium_page) -> None:
    """The defect that `chrome_attribute_inventory` was added to close.

    `top_chrome_signatures` walks the panel in document order and stops at
    `TOP_NODE_LIMIT`. With the marker nested 30 wrappers deep — ordinary for a
    live panel — the sample never reaches it and reports no icon at all.

    That miss points the wrong way: a marker that exists but was not sampled is
    indistinguishable in the notes from a marker that does not exist, so W1
    would answer H2 from missing evidence. The inventory has no budget, so it
    still finds it.
    """
    chromium_page.set_content(buried_marker_html())

    sampled = probe.top_chrome_signatures(chromium_page, limit=probe.TOP_NODE_LIMIT)
    assert "lock" not in [node["attrs"].get("data-icon") for node in sampled]

    inventory = probe.chrome_attribute_inventory(chromium_page)
    assert inventory["data_icon"].get("lock") == 1

    # The exporter's own predicate was never fooled: it uses descendant
    # selectors. Only the recorded evidence was at risk, which is why this is a
    # probe defect and not a completeness defect.
    from whatsapp_chat_extractor.export_one import at_chat_start

    assert at_chat_start(chromium_page) is True
