# Walkthrough: EXTRACTOR
**File**: `docs/walkthroughs/EXTRACTOR_WALKTHROUGH.md`
**Last updated**: Sprint #007

---

## 1. What was achieved

| Sprint | Milestone | Outcome |
| :--- | :--- | :--- |
| #003 | P1 spike | Playwright package + CLI; live export of one chat (84 text messages) to gitignored `data/` |
| #004 | P2 happy path | Full-history harvest with automatic load-older clicking, schema v3 (pseudonymous, completeness-declaring), `/wa-export` — **verified live: 513 messages in 12 passes; 135 contact / 119 me / 0 unknown** |
| H-001 | Wrong-chat hotfix | `open_chat_by_query` verifies the opened conversation against the query and fails closed. Shipped as v0.5.1 |
| #006 | P3a completeness criterion | **Measured that `complete: true` is unreachable**: across 5 real conversations and 2 runs, `COMPLETE_REASONS` never fired and no start marker appeared in any panel. Built `scripts/probe_chat_start.py` to answer it by measurement rather than assumption, and fixed a harvester defect it exposed — `decide_stop` was calling a still-fetching panel a stall. `ADR-0004` and the schema change were gate-withheld and carry into #007 |
| #007 | P3b all chats | `export-all` enumerates every conversation and writes a run manifest. **Measured that the chat list virtualizes**: 899 conversations behind a 70-row window, reproduced across two sweeps. `ADR-0004` replaced the completeness boolean with three values (schema v5). **Verified live: 3 exported, 0 failed, 907 skipped of 910 enumerated.** Two probe defects and one enumerator limit were found by measuring again rather than by review |

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

`export-all` covers the whole account: it sweeps the virtualized chat list,
opens each conversation by **verified identity** (the opened title must hash back
to the requested `chat_id` or the chat is refused), harvests it with the same
loop, and records every outcome in `data/run_manifest_<stamp>.json`.

**A start-of-chat marker has never been observed, and Sprint 006 established it
is unreachable in practice** — five conversations, two runs, `COMPLETE_REASONS`
never firing. That is why `completeness` reports `unproven` rather than pretending
to a `proven` it cannot reach (`ADR-0004`). The value is kept for the day
WhatsApp Web renders such a marker.

## 3. Known limitations / tech debt

| Item | Marked as | Tracked where |
| :--- | :--- | :--- |
| **The enumerator undercounts silently when the chat list reorders mid-sweep** — 882 of 899 found at one reorder per 5 reads. No duplicates; pure loss, while `enumeration_complete` still reports `true` | **open defect** | Sprint 007 `SPRINT_LOG.md` F3; pinned by `tests/test_chat_list.py::test_a_reordering_list_makes_the_sweep_UNDERCOUNT_silently` |
| A whole-account run takes ~15 hours (910 conversations at ~60 s each, mostly `--load-wait-ms` waits) | open risk | Sprint 007 `task_scope.md` live verification |
| `sender: unknown` on 3.9% of messages (5 of 129) in the #007 live run, against 0 of 513 in #004 — recorded, deliberately not diagnosed | open risk | Sprint 007 `CHANGELOG.md` Known open |
| `chat_id` is not permanent: the digest follows the title, so a renamed conversation will not link to its earlier exports | `:tech-debt:` | Blueprint §3 identity contract |
| `proven` completeness never observed; `unproven` is the normal result | measured, by design | ADR-0004 |
| Direction depends on WA Web markup (tail, aria-label, `data-pre-plain-text`) | `:tech-debt:` | Blueprint §3 direction contract |
| Retry after a session drop mid-harvest; resume of a partial whole-account run | `:tech-debt:` | Sprint 007 plan §D3 — the manifest is built to allow it |
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

## Reading `kind` (schema v4, #005; carried unchanged into v5)

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
*Updated at Sprint Closeout #007 (RA-05).*
