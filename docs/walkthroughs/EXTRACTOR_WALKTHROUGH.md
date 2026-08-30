# Walkthrough: EXTRACTOR
**File**: `docs/walkthroughs/EXTRACTOR_WALKTHROUGH.md`
**Last updated**: Sprint #003

---

## 1. What was achieved

| Sprint | Milestone | Outcome |
| :--- | :--- | :--- |
| #003 | P1 spike | Playwright package + CLI; live export of one chat (84 text messages) to gitignored `data/` |
| #004 | P2 happy path | Full-history harvest with automatic load-older clicking, schema v3 (pseudonymous, completeness-declaring), `/wa-export` — **verified live: 513 messages in 12 passes; 135 contact / 119 me / 0 unknown** |

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

---
*Updated at Sprint Closeout #004 (RA-05).*
