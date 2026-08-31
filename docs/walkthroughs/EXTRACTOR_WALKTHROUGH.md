# Walkthrough: EXTRACTOR
**File**: `docs/walkthroughs/EXTRACTOR_WALKTHROUGH.md`
**Last updated**: Sprint #006

---

## 1. What was achieved

| Sprint | Milestone | Outcome |
| :--- | :--- | :--- |
| #003 | P1 spike | Playwright package + CLI; live export of one chat (84 text messages) to gitignored `data/` |
| #004 | P2 happy path | Full-history harvest with automatic load-older clicking, schema v3 (pseudonymous, completeness-declaring), `/wa-export` — **verified live: 513 messages in 12 passes; 135 contact / 119 me / 0 unknown** |
| #005 | P2.5 corpus fidelity | Media placeholders (schema v4), operator surface, README, LICENSE. Closed with 88 tests green |
| H-001 | Wrong-chat hotfix | `open_chat_by_query` verifies the opened conversation against the query and fails closed. Shipped as v0.5.1 |
| #006 | P3a completeness criterion | **Measured that `complete: true` is unreachable**: across 5 real conversations and 2 runs, `COMPLETE_REASONS` never fired and no start marker appeared in any panel. Built `scripts/probe_chat_start.py` to answer it by measurement rather than assumption, and fixed a harvester defect it exposed — `decide_stop` was calling a still-fetching panel a stall. `ADR-0004` and the schema change were gate-withheld and carry into #007 |
| #005 | P2.5 corpus fidelity | Schema v4 with a mandatory `kind`; media recorded as placeholders instead of dropped (ADR-0003); emoji-only messages recovered; Cursor entry point, `README.md`, `LICENSE` — **verified live: 301 messages in 12 passes; text 276 / voice 10 / image 9 / unknown 6** |

## 2. Current state

`wa-extract login` / `wa-extract export-one` work on the operator Mac with a
persistent Chromium profile under `data/browser_profile/`. Offline pytest covers
the JSON writers, the search-locator fallbacks and the harvest merge/termination
rules (no live WhatsApp in CI). Blueprint:
`docs/architecture/EXTRACTOR_BLUEPRINT.md`. Spike evidence:
`docs/sprints/003-backend-extractor/SPIKE_NOTES.md`.

`export-one` walks the whole conversation instead of reading the DOM once after
a fixed number of scrolls, clicks the "load older messages" control by itself,
and declares in the file whether the result is complete. Verified against live
WhatsApp Web on 2026-08-30.

**Not yet observed: a run that reaches the start of a chat.** Every live run so
far was deliberately capped (6-12 passes) to iterate quickly, so all of them
ended `complete: false` / `max_passes`. An uncapped run is what would first
produce `stopped_reason: chat_start`, and with it the only proof the
start-of-chat markers match a real conversation's beginning.

## 3. Known limitations / tech debt

| Item | Marked as | Tracked where |
| :--- | :--- | :--- |
| No uncapped run yet: `chat_start` / `complete: true` never observed | open risk | Sprint 004 Phase Register |
| Direction depends on WA Web markup (tail, aria-label, `data-pre-plain-text`) | `:tech-debt:` | Blueprint §3 direction contract |
| All-chats dump not implemented (one chat per invocation) | deferred | ADR-0002 P3 / Sprint 005+ |
| Retry after a session drop mid-harvest | `:tech-debt:` | ADR-0002 P3 / Sprint 005+ |
| WhatsApp Web selectors churn | `:tech-debt:` | `SPIKE_NOTES.md` + `export_one.py` constants |
| Host lacks CONTRIBUTING/SECURITY/CODE_OF_CONDUCT/NOTICE at root | platform gap | `/agents:harden` |

Deliberate product boundary (not debt): analysis/bot stay out of repo —
`docs/decisions/ADR-0001-product-scope-whatsapp-web.md`.

## 4. How to operate it

```bash
source .venv/bin/activate
wa-extract login --keep-open
wa-extract export-one --query "PARTIAL_CHAT_NAME"   # exit 3 = truncated
.venv/bin/python -m pytest tests/ -q
```

Live runs must be issued **outside the agent sandbox**: Chromium cannot create
its `ProcessSingleton` socket under it and aborts before opening a page.

From an agent session, `/wa-export PARTIAL_CHAT_NAME` runs the same export and
reports the path, `message_count` and `complete`.

Read `complete` before using an export as a learning corpus:

```bash
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));\
print(d['message_count'], d['complete'], d['stopped_reason'])" data/<file>.json
```

`complete: false` means the run hit `--max-passes` and history remains above the
oldest message in the file. Re-run with a higher cap.

## Reading `kind` (schema v4, #005)

Every message carries a `kind`. Count them before trusting a corpus:

```bash
python3 -c "import json,sys,collections;d=json.load(open(sys.argv[1]));\
print(collections.Counter(m['kind'] for m in d['messages']))" data/<file>.json
```

| `kind` | What it means for a reader |
| :--- | :--- |
| `text` | Ordinary message; `body` holds it, emoji included |
| `image` | A photo. `body` is its caption when it had one, otherwise empty |
| `voice` | A voice note. `body` is empty; the audio is never downloaded |
| `unknown` | A medium the DOM probe has not identified yet. The turn is preserved, the medium is not named |

A rising `unknown` count means WhatsApp is drawing a medium the probe has not
seen. Re-probe the DOM before adding a selector — three assumption-driven
theories about message direction shipped wrong in #004 (`KI-004-A`).

Media rows carry a `timestamp` of `H:MM` with **no date**, because a row without
text carries no `data-pre-plain-text`. The date is deliberately not synthesized.
Order messages by `order`, not by `timestamp`.

---
*Updated at Sprint Closeout #005 (RA-05).*
