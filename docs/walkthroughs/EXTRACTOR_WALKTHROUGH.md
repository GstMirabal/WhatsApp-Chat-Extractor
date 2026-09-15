# Walkthrough: EXTRACTOR
**File**: `docs/walkthroughs/EXTRACTOR_WALKTHROUGH.md`
**Last updated**: Sprint #011

---

## 1. What was achieved

| Sprint | Milestone | Outcome |
| :--- | :--- | :--- |
| #003 | P1 spike | Playwright package + CLI; live export of one chat (84 text messages) to gitignored `data/` |
| #004 | P2 happy path | Full-history harvest with automatic load-older clicking, schema v3 (pseudonymous, completeness-declaring), `/wa-export` — **verified live: 513 messages in 12 passes; 135 contact / 119 me / 0 unknown** |
| H-001 | Wrong-chat hotfix | `open_chat_by_query` verifies the opened conversation against the query and fails closed. Shipped as v0.5.1 |
| #006 | P3a completeness criterion | **Measured that `complete: true` is unreachable**: across 5 real conversations and 2 runs, `COMPLETE_REASONS` never fired and no start marker appeared in any panel. Built `scripts/probe_chat_start.py` to answer it by measurement rather than assumption, and fixed a harvester defect it exposed — `decide_stop` was calling a still-fetching panel a stall. `ADR-0004` and the schema change were gate-withheld and carry into #007 |
| #007 | P3b all chats | `export-all` enumerates every conversation and writes a run manifest. **Measured that the chat list virtualizes**: 899 conversations behind a 70-row window, reproduced across two sweeps. `ADR-0004` replaced the completeness boolean with three values (schema v5). **Verified live: 3 exported, 0 failed, 907 skipped of 910 enumerated.** Two probe defects and one enumerator limit were found by measuring again rather than by review |
| #009 | P4 resume + corpus v6 | `export-all` writes an append-only NDJSON run journal (`data/run_journal_<run_id>.ndjson`) as it goes; `export-all --resume <run_id>` re-enumerates the chat list and exports only what the journal lacks; `recover --run-id <id>` rebuilds `data/run_manifest_<run_id>.json` from the journal with no browser. Schema v6 adds `message_id` and `timestamp_iso` per message and `passes_used`, `source_locale`, `source_timezone`, `undated_messages` per export (`ADR-0006`, `ADR-0007`). Suite 277 passed / 1 skipped, from a 224 / 1 baseline |
| H-003 | Unresolved-spinner hotfix | A harvest whose "load older messages from your phone" request the phone never answers previously ran the full `--max-passes` budget (~8.3 h per conversation). It now gives up after `loading_grace` stalled passes past the stall threshold (default `20`) with `stopped_reason: loading_unresolved` and `completeness: truncated`, ~6 minutes instead. Landed on `ai-sprint/009` at `1728519` |
| #011 | Backlog closure | Closed every item carried from Sprints 009-010 in one sprint. `--deadline-seconds` bounds the harvest loop by wall-clock time (`STOP_DEADLINE`) so a stuck conversation no longer risks the full `--max-passes` budget with no operator watching; the chat-index journal (`--write-index`) is now append-only and survives a crash mid-run instead of losing every title on one batched write; `journal.read_journal` keeps the first `--resume` header, not the last; every `cmd_*` handler moved out of `__main__.py` into a new `commands.py` (`__main__.py` 854→277 lines); timezone-prompt functions gained test coverage. 13/13 units, QA `APPROVED` after one bounce-and-fix cycle, Tester `RECORD`. Suite 294 / 1 → 316 / 1 |

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
to the requested `chat_id` or the chat is refused), and harvests it with the
same loop. Since #009 (`ADR-0006`) each outcome is appended to an
`fsync`ed run journal, `data/run_journal_<run_id>.ndjson`, as the run makes it;
the manifest, `data/run_manifest_<run_id>.json`, is reconstructed from that
journal at the end. A run that crashed part-way is continued with
`export-all --resume <run_id>` and its manifest rebuilt offline with
`recover --run-id <id>` — see §5.

**A start-of-chat marker has never been observed, and Sprint 006 established it
is unreachable in practice** — five conversations, two runs, `COMPLETE_REASONS`
never firing. That is why `completeness` reports `unproven` rather than pretending
to a `proven` it cannot reach (`ADR-0004`). The value is kept for the day
WhatsApp Web renders such a marker.

## 3. Known limitations / tech debt

| Item | Marked as | Tracked where |
| :--- | :--- | :--- |
| The single-pass sweep undercounts silently when the chat list reorders mid-sweep — 882 of 899 at one reorder per 5 reads, 856 at one per 2. No duplicates; pure loss | **mitigated (#008)** | `sweep_until_stable` unions repeated sweeps and recovers 899 of 899 at both rates in 4 sweeps; `enumeration_complete` is replaced by `ADR-0005`'s three values. The primitive's limit is still pinned by `tests/test_chat_list.py::test_a_reordering_list_makes_the_sweep_UNDERCOUNT_silently` |
| Convergence is evidence, not proof: a conversation can in principle evade any finite number of sweeps, so `converged` never means the list was provably seen whole | measured, by design | ADR-0005 |
| A whole-account run takes ~15 hours (910 conversations at ~60 s each, mostly `--load-wait-ms` waits) | open risk | Sprint 007 `task_scope.md` live verification |
| `sender: unknown` on 3.9% of messages (5 of 129) in the #007 live run, against 0 of 513 in #004 — recorded, deliberately not diagnosed | open risk | Sprint 007 `CHANGELOG.md` Known open |
| `chat_id` is not permanent: the digest follows the title, so a renamed conversation will not link to its earlier exports | `:tech-debt:` | Blueprint §3 identity contract |
| `proven` completeness never observed; `unproven` is the normal result | measured, by design | ADR-0004 |
| Direction depends on WA Web markup (tail, aria-label, `data-pre-plain-text`) | `:tech-debt:` | Blueprint §3 direction contract |
| Retry after a session drop mid-harvest; resume of a partial whole-account run | **resolved (#009)** | `ADR-0006` shipped `export-all --resume <run_id>` (re-enumerate, skip conversations the journal marks `exported`) and `recover --run-id <id>` (rebuild the manifest, no browser); see §5 |
| The harvest loop had no wall-clock bound — only `max_passes` (iteration count) — so a conversation whose panel never resolved, and never tripped H-003's spinner rule either, could still burn hours with no operator watching | **resolved (#011)** | `--deadline-seconds` / `STOP_DEADLINE`; see §9 |
| `export-all --write-index` wrote `data/chat_index_<run_id>.json` once, at the end of a run — a crash before that write lost every title the run had already gathered | **resolved (#011)** | Append-only `data/chat_index_<run_id>.ndjson`; see §9 |
| `journal.read_journal` kept the timestamp of the **last** `--resume` header, not the run's true start | **resolved (#011)** | First-write-wins guard; see roadmap `T-8` |
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

`complete: false` is the normal result (`ADR-0004`); what to do about it depends
on `stopped_reason`:

| `stopped_reason` | What it means | Action |
| :--- | :--- | :--- |
| `max_passes` | The run hit `--max-passes` and history remains above the oldest message in the file | Re-run with a higher `--max-passes` |
| `loading_unresolved` | The load-older spinner never resolved: the paired phone is not delivering history (`completeness: truncated`, H-003) | A higher cap does not help — see §7 |
| `stalled` / `chat_start` | The panel stopped producing history, or the start-of-chat marker was seen | Nothing; the file holds as much as WhatsApp Web will give |

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

## 5. Resuming a crashed whole-account run (schema v6, #009)

A whole-account `export-all` walk takes hours. As it goes it appends one line
per conversation to `data/run_journal_<run_id>.ndjson`, `fsync`ed after every
write, so a crash, `kill`, or the machine sleeping loses at most the torn last
line (`ADR-0006`). The `run_id` is the timestamp embedded in that filename.

`--resume <run_id>` re-enumerates the live chat list from scratch — it never
trusts the positions the journal recorded — and exports only what the journal
does not already mark `exported`. A `failed` conversation is retried;
conversations that appeared since the crash are picked up. Issue it outside the
agent sandbox, like any browser run:

```bash
wa-extract export-all --resume <run_id>
```

`recover --run-id <id>` rebuilds `data/run_manifest_<run_id>.json` from the
journal alone and opens no browser, so it runs on a machine that cannot launch
Chromium:

```bash
wa-extract recover --run-id <run_id>
```

| `recover` exit | Meaning |
| :--- | :--- |
| `0` | Enumeration converged, nothing failed, every enumerated conversation has a journal line |
| `3` | The run recorded fewer conversations than it enumerated — it stopped early; finish it with `--resume` |

`recover` reports how many conversations a dead run never reached, but cannot
name them: the journal records what was done, never the chat-list positions
(`ADR-0006`).

## 6. Schema v6 fields a reader now gets (#009)

Schema v6 is additive (`ADR-0007`): no v5 field changed name or meaning.
`SCHEMA_VERSION` is `6`.

| Container | Field | What a reader gets |
| :--- | :--- | :--- |
| each message | `message_id` | Stable identity for the row — a WhatsApp `data-id`, or a `sha1:`-prefixed fallback — so the same message is recognisable across two exports of one chat |
| each message | `timestamp_iso` | The rendered clock parsed to `YYYY-MM-DDTHH:MM`, no timezone offset attached |
| each export | `passes_used` | Scroll passes the harvest spent; read it together with `completeness` |
| each export | `source_locale` | BCP 47 tag the page rendered under (`es-ES`); empty means unrecorded, the state of every pre-v6 file |
| each export | `source_timezone` | IANA zone the browser's own `Intl` resolution named, or `""` when the page could not answer |
| each export | `undated_messages` | Count of messages whose `timestamp_iso` is `""` |

`timestamp_iso` is `""` for a row WhatsApp rendered with a clock and no date;
`undated_messages` counts exactly those rows. The raw `timestamp` string is kept
beside the parsed value as evidence, and v5 files are not back-filled — see
`ADR-0007` for the rationale.

```bash
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));\
print(d['undated_messages'], 'of', len(d['messages']), 'undated;', \
d['source_locale'], d['source_timezone'], d['passes_used'])" data/<file>.json
```

`export-all --timezone <IANA_ZONE>` asks the browser to render clocks in that
zone through the environment it inherits, but cannot impose it; `source_timezone`
always records what the page resolved and logs a warning on a mismatch
(`ADR-0007`).

## 7. Truncated exports: the unresolved-spinner case (H-003)

When WhatsApp asks the paired phone for older messages and the phone never
answers, the panel spinner never resolves. A visible spinner is positive
evidence that more history is coming, so the harvest suppresses its stall
verdict while one is up — but only for `loading_grace` stalled passes past the
stall threshold (default `20`). Past that it stops with
`stopped_reason: loading_unresolved` rather than running the full 2000-pass
budget: about 6 minutes instead of about 8.3 hours. Such an export carries
`completeness: truncated`.

Find them in a finished run:

```bash
python3 -c "import json,glob;[print(f) for f in glob.glob('data/chat_*.json') if json.load(open(f)).get('stopped_reason')=='loading_unresolved']"
```

Retry with a higher cap:

```bash
wa-extract export-all --resume <run_id> --max-passes 40
```

If the phone is not delivering history there is nothing more to get: a higher
cap only changes how long the conversation waits before it is recorded
`truncated` again.

## 8. Building one corpus from a run (`consolidate`, #010)

`export-all` and `export-one` leave one `data/chat_*.json` file per
conversation. `consolidate` joins every one of them under `--data-dir` into a
single NDJSON file, opening no browser (`§D4`):

```bash
wa-extract consolidate
```

| Flag | Default | What it changes |
| :--- | :--- | :--- |
| `--data-dir` | `data/` | Directory holding the `chat_*.json` files and, unless `--from-manifest` is given, the run manifests it reads the source run id from |
| `--from-manifest` | none (newest `run_manifest_*.json` under `--data-dir`) | Names the source run explicitly from this manifest path instead |
| `--out` | `<data-dir>/corpus_<source_run>.ndjson` | Output file path |

`consolidate` aborts with exit `2` and writes no file on either of two
conflicts:

| Cause | Detail |
| :--- | :--- |
| Duplicate `chat_id` | Two input files carry the same pseudonymous `chat_id`; the operator resolves it by deleting the wrong file |
| Wrong schema | An input file's `schema_version` is not the current one (`6`) |

### Reading the corpus line by line

The first line is a provenance header, not a conversation. Read it once, then
one `json.loads` per remaining line:

```python
import json

with open("data/corpus_<source_run>.ndjson", encoding="utf-8") as handle:
    header = json.loads(next(handle))
    for line in handle:
        chat = json.loads(line)
```

| Header field | What it carries |
| :--- | :--- |
| `record` | Always `"header"`, the discriminator that marks this line as the header rather than a conversation |
| `corpus_schema` | Version of the header shape itself |
| `chat_schema` | Schema version every conversation line was written under (`6`) |
| `source_run` | The run id the corpus was consolidated from, or `unknown` when no run manifest was found |
| `generated_at` | UTC ISO 8601 timestamp of the `consolidate` run that wrote the file |
| `chat_count` | How many conversation lines follow the header — read exactly this many `json.loads` calls after skipping the header, or read until EOF |

Each conversation line is one `chat_*.json` export written verbatim: nothing
is flattened, trimmed or recomputed during consolidation.

## 9. Bounding a stuck harvest and protecting the chat index (#011)

**Wall-clock deadline.** H-003 bounds a harvest whose spinner never resolves;
it does not bound a harvest that shows no spinner and simply never advances.
`--deadline-seconds` now caps the whole harvest by wall-clock time,
independent of `--max-passes`:

```bash
wa-extract export-one --query "PARTIAL_CHAT_NAME" --deadline-seconds 1800
```

An export that hits the deadline carries `stopped_reason: deadline` and
`completeness: truncated` — the same honest failure as `max_passes` or
`loading_unresolved`, bounded by time instead of iteration count. There is no
default: an unset `--deadline-seconds` runs exactly as before this sprint,
unbounded except by `--max-passes`. A conversation this large no longer risks
the ~8-hour `max_passes` budget with no operator watching.

**Chat-index journal survives a crash.** `export-all --write-index` used to
write `data/chat_index_<run_id>.json` once, at the very end of a run — a
crash before that write lost every title the run had already gathered. It
now appends one line per conversation to `data/chat_index_<run_id>.ndjson` as
each title is discovered, the same discipline the outcomes journal has used
since #009:

```bash
python3 -c "import json;[print(json.loads(l)) for l in open('data/chat_index_<run_id>.ndjson')]"
```

---
*Updated at Sprint Closeout #011 (RA-05).*
