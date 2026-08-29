# Walkthrough: EXTRACTOR
**File**: `docs/walkthroughs/EXTRACTOR_WALKTHROUGH.md`
**Last updated**: Sprint #003

---

## 1. What was achieved

| Sprint | Milestone | Outcome |
| :--- | :--- | :--- |
| #003 | P1 spike | Playwright package + CLI; live export of one chat (84 text messages) to gitignored `data/` |
| #004 | P2 happy path | Full-history harvest, export schema v2 with a completeness contract, `/wa-export` command — **offline gates green, live run pending** |

## 2. Current state

`wa-extract login` / `wa-extract export-one` work on the operator Mac with a
persistent Chromium profile under `data/browser_profile/`. Offline pytest covers
the JSON writers, the search-locator fallbacks and the harvest merge/termination
rules (no live WhatsApp in CI). Blueprint:
`docs/architecture/EXTRACTOR_BLUEPRINT.md`. Spike evidence:
`docs/sprints/003-backend-extractor/SPIKE_NOTES.md`.

`export-one` now walks the whole conversation instead of reading the DOM once
after a fixed number of scrolls, and every export declares whether it is
complete. **The #004 harvest has not yet been run against live WhatsApp Web**:
the selectors it depends on (`data-id` for message identity, the start-of-chat
marker) are verified only against synthetic passes until the operator runs it.

## 3. Known limitations / tech debt

| Item | Marked as | Tracked where |
| :--- | :--- | :--- |
| Harvest unverified against live WhatsApp Web | open risk | Sprint 004 abort criterion |
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
*Updated during Sprint #004 execution; live verification pending (RA-05).*
