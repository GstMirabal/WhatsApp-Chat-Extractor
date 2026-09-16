# Blueprint: EXTRACTOR
**File**: `docs/architecture/EXTRACTOR_BLUEPRINT.md`
**Status**: `RATIFIED`
**Sprint of origin**: #003
**Last Audit Sprint**: #012
**Last Audit Date**: 2026-09-16
**Last Audit Commit SHA**: `016db68`

> **Stamp correction (Sprint 012):** this header still read `#008` /
> `d30a1b5` while the body below already documented Sprint 011 content in
> four places (`grep -n "Sprint 011" docs/architecture/EXTRACTOR_BLUEPRINT.md`)
> — `RA-05 SPRINT_CLOSEOUT` requires the stamp to move with the sprint that
> touches the file, and Sprint 011 touched it without advancing this line.

---

arc42-lite (`rules/documentation_standard.md §5`) — Reference only.

## 1. Introduction & Goals

Python package that opens WhatsApp Web via Playwright, lets the operator
complete QR login once (persistent Chromium profile), opens **one**
human-selected chat, and writes its **complete** text history as JSON under
gitignored `data/`.

The consumer is an agent learning from the conversation, which sets the bar for
correctness: the export must either hold the whole chat or say that it does not.
A dump silently truncated by a scroll count is not a partial deliverable, it is
an invalid one.

## 2. Context & Scope

| Aspect | Value |
| :--- | :--- |
| **Upstream dependencies** | Playwright Chromium; WhatsApp Web UI; operator Mac + phone for QR |
| **Downstream consumers** | External AI / learning pipelines reading `data/*.json` (out of repo) |

## 3. Building Block View

| Aspect | Value |
| :--- | :--- |
| **Owns** | `src/whatsapp_chat_extractor/`, `tests/`, `pyproject.toml`, writes under `data/` |
| **Must not touch** | Sentiment/bot code; `.agents/` internals |

| Interface | Type | Defined in |
| :--- | :--- | :--- |
| `wa-extract login` | CLI | `commands.cmd_login`, parser wiring in `__main__.build_parser` (handler moved to `commands.py` #011) |
| `wa-extract export-one` | CLI | `commands.cmd_export_one`, parser wiring in `__main__.build_parser` (handler moved to `commands.py` #011) |
| `wa-extract export-all` | CLI | `commands.cmd_export_all` (#007; handler moved to `commands.py` #011), parser wiring in `__main__.build_parser` |
| `ChatExport` JSON | file schema | `writers.ChatExport` / this blueprint §3 |
| `RunManifest` JSON | file schema | `manifest.RunManifest` / this blueprint §3 (#007) |
| `wa-extract recover` | CLI | `commands.cmd_recover` (#009; handler moved to `commands.py` #011), parser wiring in `__main__.build_parser` |
| `wa-extract consolidate` | CLI | `commands.cmd_consolidate` (#010; handler moved to `commands.py` #011), parser wiring in `__main__.build_parser` |
| Run journal NDJSON | file schema | `journal.JournalHeader` / this blueprint §3 (#009) |
| `timestamps.parse_rendered` | function | `src/whatsapp_chat_extractor/timestamps.py` (#009) |
| `/wa-export <chat>` | slash command | `.claude/commands/wa-export.md`, `.cursor/commands/wa-export.md` |
| `whatsapp_chat_extractor.commands` | module | `src/whatsapp_chat_extractor/commands.py` (#011) — holds every `cmd_*` handler; `__main__.py` keeps `build_parser`/`_add_*`/`main()` only |

### CLI orchestration split (§D6, #011)

`__main__.py` carried every `cmd_*` handler since Sprint 007 and had grown to
854 lines (421 at Sprint 008), with `cmd_login` at block depth 4
(`agents.md §1 max_indentation`, limit 3). Sprint 011 extracted all five
handlers — `cmd_login`, `cmd_export_one`, `cmd_export_all`, `cmd_recover`,
`cmd_consolidate` — into a new module, `whatsapp_chat_extractor.commands`
(636 lines). `__main__.py` is now 277 lines and holds only `build_parser`,
the `_add_*` parser-registration helpers, and `main()`, importing
`commands.cmd_*` for dispatch. No CLI-visible behavior changed: the
extraction also fixed `cmd_login`'s depth-4 block and `export_one.py`'s two
over-length / two depth-4 functions (`open_chat_by_query`, `scroll_one_pass`,
`_open_first_result`, `_click_load_earlier`) by extracting their innermost
`try`/`for` bodies into named helpers, closing the module-growth concern this
item was carried under without changing what any flag does.

Data model (schema v6, #009):
- **ChatExport**: `schema_version`, `chat_id`, `exported_at`, `message_count`,
  `undated_messages`, `complete`, `completeness`, `stopped_reason`,
  `passes_used`, `source_locale`, `source_timezone`, `messages[]`
- **MessageRecord**: `message_id`, `sender`, `timestamp`, `timestamp_iso`,
  `body`, `kind`, `order` — every message, whatever medium it carried
- **RunManifest** (`src/whatsapp_chat_extractor/manifest.py`, manifest schema
  v2, #008): `schema_version`, `started_at`, `finished_at`,
  `chats_enumerated`, `enumeration`, `sweeps`, `counts`, `chats[]`. The
  manifest versions independently of `ChatExport`: it is at v2 while the
  export file is at v6
- **ChatOutcome**: `chat_id`, `index`, `outcome`, `reason`, `completeness`,
  `message_count`, `file` — one per conversation the sweep found
- **JournalHeader** (`src/whatsapp_chat_extractor/journal.py`, journal schema
  v1, #009): `record`, `schema_version`, `run_id`, `started_at`,
  `chats_enumerated`, `enumeration`, `sweeps` — written once, the moment
  enumeration returns. The journal versions independently of both
  `ChatExport` and `RunManifest`: it is at v1

### Search-result selector order (#012)

`_open_first_result` (`export_one.py`) tries `SEARCH_RESULT_SELECTORS` in
order and clicks the first one that matches anything. Until Sprint 012 that
order was `#pane-side div[role="listitem"]` (0 matches, measured), then
`#pane-side div[role="row"]` (59 matches — a wrapper that accepts a click
and opens nothing), then `[data-testid="cell-frame-container"]` (the entry
that actually opens a chat, per `scripts/probe_chat_start.py` runs 1-2).
Neither selector raises on `.click()`, so the click silently landed on the
dead wrapper first: `export-one --query "..."` could return with no chat
open, requiring a manual open. Reordered to try `data-testid` before
`role="row"`; regression test (`tests/test_open_first_result.py`) pins the
order against the pre-fix defect.

**Known gap, carried, not fixed here** (`cmd_export_all`'s exit code):
`_export_one_ref` records `exported(...)` for any per-chat harvest that does
not raise, regardless of `harvest["completeness"]`, and `_run_exit_code`
(`commands.py:523-541`) reads only `enumeration`, `counts[OUTCOME_FAILED]`
and the chat/enumerated count — never per-chat `completeness`. A run with a
`truncated` conversation inside it can still exit `0`, unlike `export-one`'s
own exit `3` for the identical condition on a single chat. The tally exists
(`counts["truncated"]` in the manifest) but the exit code does not reflect
it. Found by Sprint 012's Tester Agent while closing a coverage gap;
`docs/active_state.json acknowledged_gaps.exit_code_ignores_per_chat_truncation`.

### Kind contract (ADR-0003, #005)

`kind` is mandatory on every record. An optional field would leave a reader
unable to tell an absent `kind` from a message written before the field existed.

| `kind` | Signal in the DOM | `body` |
| :--- | :--- | :--- |
| `voice` | `[data-testid="ptt-status"]` or `[data-icon="ptt-status"]` | Empty |
| `image` | `[data-testid="image-thumb"]` | Its caption, or empty |
| `text` | Neither of the above, and a body was extracted | The text |
| `unknown` | Neither of the above, and no body | Empty |

Both media signals were observed on live rows by the Sprint 005 W2 probe, never
inferred (`KI-004-A`). Media is tested before text, because a captioned photo is
a photo: the caption belongs in `body` while `kind` names what it captions.

`message_count` counts messages of every kind. Under v3 it counted text while
naming itself a message count, because a row with no text was discarded before
it could be counted.

**Emoji-only messages are `text`, not media.** WhatsApp draws an emoji as
`<img alt="…">` inside a `div[data-testid="selectable-text"]`, which the
`span.selectable-text` matcher never saw, so these rows read as bodiless and
were dropped. `_row_emoji_body` recovers the characters from `alt`. The first
live v4 export recovered 23 such messages in 301 — a larger loss than the media
this ADR was written for.

**Stated limitation.** A row with no text carries no `data-pre-plain-text`, so
media rows have a `timestamp` of `H:MM` while text rows have `H:MM, D/M/YYYY`.
The date is not synthesized: a fabricated date would be indistinguishable from a
measured one, which is the failure ADR-0003 exists to prevent. `order` carries
the sequence.

### Identity contract

No personal identifier is written to disk **by default**. One file is the
exception and is named for it: `data/chat_index_<run_id>.ndjson`, written only
when the operator passes `export-all --write-index`, maps `chat_id` back to
the real conversation name. It is a separate file from the run manifest so it
can be deleted without losing the record of what a run did, and the manifest
itself never carries a title.

**Append-only since Sprint 011 (§D5).** `manifest.write_chat_index` used to
write one batched JSON object at the end of a run — a crash before that call
lost every title gathered during the run, unlike the outcomes journal's
append-on-every-record discipline. `manifest.open_chat_index_journal` now
opens the file for append at run start and `manifest.append_chat_index_entry`
writes one line per conversation as its title is discovered, mirroring
`journal.append_outcome`'s crash-tolerance argument exactly. `write_chat_index`
is retired. No change to the privacy boundary: `--write-index` remains the
gate, and titles never entered the pseudonymous run journal either way.

| Field | Rule |
| :--- | :--- |
| `chat_id` | `chat_` + first 12 hex of `sha256(chat title)`. Stable across exports **while the title is unchanged** — see below |
| filename | `<chat_id>_<stamp>.json` — a directory listing shows no name |
| `title` | Removed in v3. The title is hashed in `build_export` and dropped |
| `sender` | A role — `me`, `contact`, `unknown` — never a name |
| `timestamp` | The bracketed part of `data-pre-plain-text`; the name after it is discarded in the same expression. A row without that attribute falls back to the meta clock, which carries no date |

**The digest follows the title, so identity is not permanent (#007).** Two
enumeration sweeps 2.5 hours apart both counted 899 conversations and shared
**898** of them: one digest changed, because a conversation was renamed or a bare
number acquired a saved contact name. Within a run the digest is a sound key —
zero title collisions in 7 100 row observations across a 899-chat list — but a
renamed conversation becomes a **new** `chat_id`, and its later exports will not
link to its earlier ones. `pseudonymous_chat_id` documents itself as stable
across exports; that promise holds only while the title does.

### Direction contract

Derived from three signals in order, because no single one covers every row.
Established by probing the live DOM (Sprint 004) after three separate
assumption-driven attempts each shipped a wrong answer:

| # | Signal | Covers | Misses |
| :--- | :--- | :--- | :--- |
| 1 | `tail-out` / `tail-in` (`data-testid`, `data-icon`) | First message of any run | Consecutive messages — WA draws no tail |
| 2 | `aria-label` of the form `Name:` | Media rows (photo, voice note) | Plain consecutive text |
| 3 | Name in `data-pre-plain-text` | Consecutive text messages | Rows with no attribute at all → `unknown` |

Each label is compared with the chat title and discarded. In a one-to-one chat
the title is the contact, so a label equal to it is `contact` and any other
non-empty label (`Tú:`, `You:`, an own display name) is `me`.

**Measured facts about the live DOM**, recorded so the next change starts from
evidence rather than from these same three wrong guesses:

| Assumption that failed | What the probe measured |
| :--- | :--- |
| `data-id` is `true_`/`false_` prefixed | Bare hex, e.g. `3AE791A711C2B982F858` |
| `.message-in` / `.message-out` exist | Match **zero** rows |
| `data-pre-plain-text` sits on the row | Sits on a descendant |

This is **pseudonymization, not anonymization**, and the blueprint says so
rather than implying more: the digest is unsalted, so a holder of the contact
list can confirm a match by hashing a candidate name. Message bodies are
untouched and may name people on their own.

### Enumeration contract (ADR-0005, manifest schema v2, #008)

`enumeration` states how far the run can vouch for having seen the whole chat
list, in three values. It **replaces** the boolean `enumeration_complete`, which
was set from whether the pane reached its foot — a true statement about the
pane, and not the one its name made. A list that reorders mid-sweep drops
conversations below the sweep position and they are never rendered into any
pass: 882 of 899 found at one reorder per 5 reads, 856 at one per 2, zero
duplicates, and the boolean reported `true` throughout.

| `enumeration` | Condition | Meaning |
| :--- | :--- | :--- |
| `converged` | Pane foot reached **and** the final two sweeps contributed nothing new | Evidence the list was seen whole. Never proof — a conversation can evade any finite number of sweeps |
| `unconverged` | Pane foot reached, sweeps still contributing when the budget ran out | The list was still yielding conversations when enumeration stopped |
| `truncated` | Pane foot never reached | The pass cap ended the sweep |

Fails closed: `converged` requires a positive demonstration of both conditions.
`sweeps` carries the count, so the claim is auditable from the file. The
mitigation is `sweep_until_stable`, which repeats `sweep_chat_list` from the
head and unions by digest; measured recovery is 899 of 899 at both reorder rates
in 4 sweeps, against 3 for a quiet list. `sweep_chat_list` is unchanged and
remains the single-pass primitive, with its measured limit still pinned by
`tests/test_chat_list.py::test_a_reordering_list_makes_the_sweep_UNDERCOUNT_silently`.

Unlike `completeness`, this value set does **not** offer a `proven`. There, a
future WhatsApp Web start marker would make `proven` reachable; here no
observation of a virtualized list can ever establish that nothing moved behind
the reader, so a permanently dead value is not defined.

### Completeness contract (ADR-0004, schema v5, #007)

`completeness` states how far back a harvest can prove it reached, in three
values. `complete` survives as a boolean **derived** from it — never set
independently, so the two cannot disagree — because schema v4 files exist and a
reader of the boolean must not break on a v5 file.

| `completeness` | `complete` | Condition | Meaning |
| :--- | :--- | :--- | :--- |
| `proven` | `true` | `stopped_reason == "chat_start"` | The beginning was **observed** |
| `unproven` | `false` | `stalled`, panel quiet | The panel stopped producing history and nothing indicated more was coming. An inference, named as one |
| `truncated` | `false` | `max_passes`, `loading_unresolved` (a spinner suppressed the stall verdict past `loading_grace`, H-003), or `deadline` (`STOP_DEADLINE`, the `--deadline-seconds` wall-clock cap elapsed, `KI-009-H`, #011) | The harvest ended before the conversation did |

`classify_completeness` **fails closed**: a stop reason it does not recognise is
`truncated`, never `proven`. An unknown reason is not evidence of having arrived.

The `loading_unresolved` pairing is **reached in practice, not defensive
padding**. `decide_stop` suppresses the `stalled` verdict while the panel is
fetching — Sprint 006's probe run 3 is why: a harvest was declared `stalled`
after 175 passes with a `loading-spinner` still on screen, and classifying a
live spinner as `unproven` would reinstate that error. Hotfix H-003 then hit the
opposite failure — a production run whose phone never answered the load-earlier
request left the spinner up for 890 consecutive passes, and the suppression,
unbounded at the time, held all the way to `max_passes`. `decide_stop` now
bounds it: past `stall_threshold + loading_grace` stalled passes under a spinner
it returns `STOP_LOADING_UNRESOLVED`, which `classify_completeness` fails closed
to `truncated` with no code change. Full account:
`docs/hotfixes/H-003-backend.md`.

`stalled` counted as complete until the first live run, which exported 217
messages of a longer conversation and marked them complete. Only the marker is
proof; an inference is not recorded as one.

**A stall requires a quiet panel, not merely a quiet pass (Sprint 006).**
`decide_stop` takes `panel_loading`, and a visible loading indicator
(`LOADING_SELECTORS`) suppresses the `stalled` verdict: a spinner is positive
evidence that more history is coming, so stopping on it reports a top that was
never reached. The suppression is **bounded**: `DEFAULT_LOADING_GRACE = 20` caps
how many stalled passes past `stall_threshold` a visible spinner may suppress,
and beyond that `decide_stop` returns `STOP_LOADING_UNRESOLVED` and the harvest
ends — roughly 6 minutes rather than the 8.3 hours `max_passes` alone cost the
H-003 production run. `20` is empirical: across the 250 conversations exported
under schema v6 at the time of the fix, `passes_used` was minimum 4, median 4,
90th percentile 6, maximum 13, none over 20. `max_passes` still terminates any
run the grace window does not, and `STOP_CHAT_START` still wins over every
condition. Measured: one conversation was declared `stalled` after 175 passes
with a spinner on screen, and ran 255 with the panel genuinely quiet once
corrected.

**`proven` has never been produced, and Sprint 006 established it is unreachable
in practice.** Across five real conversations and two runs, with the stall defect
corrected, `COMPLETE_REASONS` did not fire once and no start marker appeared in
any panel — `data-icon` was empty in every chrome inventory taken. The narrower
statement is the honest one: no harvest reached a *provable* beginning, so "the
marker does not exist" remains an inference. Evidence:
`docs/sprints/006-backend-extractor/DOM_PROBE_NOTES.md`.

That measurement is what `ADR-0004` decided against: a field that is always
`false` cannot distinguish a complete history from a truncated one, which is the
single thing it exists to do in a training corpus. `proven` is nonetheless kept
in the value set, because the day WhatsApp Web renders a start marker the export
must be able to say so without another schema change.

**`KI-009-H` closed, Sprint 011: wall-clock deadline.** `harvest_history` had
only `max_passes` — an iteration count — bounding it; nothing bounded wall
time, so a conversation whose panel never resolved and never tripped
`loading_unresolved` either could still run the full `max_passes` budget
regardless of elapsed time. `deadline_seconds` now threads through
`harvest_history` → `_one_pass` → `_observe_and_decide` → `decide_stop`,
checked against `time.monotonic()` captured once at harvest start, and a new
`STOP_DEADLINE` reason joins `STOP_MAX_PASSES` and `STOP_LOADING_UNRESOLVED`.
It is deliberately **not** added to `COMPLETE_REASONS`, so
`classify_completeness` fails it closed to `truncated` — the same discipline
`STOP_LOADING_UNRESOLVED` already follows. Exposed as `--deadline-seconds`
with no default enforced (`None`, unbounded, unless the operator sets one):
H-003's own measurement (13 passes maximum across 250 conversations) bounds
the `loading_grace` window, not a global wall-clock default, and stating one
here would invent a figure the corpus does not support. `max_passes` and
`deadline_seconds` are complementary bounds, not substitutes — one guarantees
termination on iteration count, the other on wall time.

**Only `truncated` is a failure.** `export-one` exits `3` on `truncated` and `0`
otherwise. It previously exited `3` whenever `complete` was false, which — since
`complete` was never true — meant **every export ever produced reported failure**
and advised raising a `--max-passes` cap that was not the cause.

### Enumeration contract (#007)

Measured before written, over three probe runs
(`docs/sprints/007-backend-extractor/CHAT_LIST_PROBE_NOTES.md`):

| Property | Measurement |
| :--- | :--- |
| The chat pane **virtualizes** | 899 conversations seen while the DOM never held more than 70 rows at once |
| Position is **stable across a sweep** | 0 of 69 positions changed between two readings anchored at the pane head, two minutes apart |
| Titles are **unique within a run** | 0 collisions in 7 100 row observations |
| The working title selector is `span[title]` | The two `cell-frame-title` candidates match nothing in this build |

Consequences, and they are not interchangeable:

| Rule | Why |
| :--- | :--- |
| Enumeration is a **sweep that merges by identity**, never one `query_selector_all` | A single read returns 70 of 910 and reports success |
| A sweep stops only once the pane foot is reached **and** three passes add nothing | Quiet passes before the foot mean the sweep is inside the render buffer, not that the list ended. Probe run 1 confounded them and named a whole list from 3.3% of it |
| `index` is a **hint** for where to look; `chat_id` is the identity | Position is proven stable over a two-minute sweep and unproven over a run of hours |
| Every open is **verified**: the opened title must hash to the requested `chat_id`, or the run refuses that chat | H-001 shipped a wrong-chat export because a click was trusted without checking what it opened |
| A conversation that fails is recorded and the run **continues**; losing the session aborts it | A run of hundreds that dies on the third wastes the manual login and every export already made. A lost session, by contrast, makes every later attempt fail identically |
| A conversation beyond `--limit` is recorded as `skipped`, never omitted | An omitted conversation is indistinguishable from one that never existed |

### Corpus contract v6 (ADR-0007, schema v6, #009)

Every v6 field is additive — no v5 field changes name, meaning, or type.
Rationale is `docs/decisions/ADR-0007-corpus-contract-v6.md`; this table
states the fields that resulted, verified against `writers.MessageRecord` and
`writers.ChatExport`.

| Field | On | Type | Source |
| :--- | :--- | :--- | :--- |
| `message_id` | `MessageRecord` | `str` | Identity already computed by `history.HarvestedRow` for pass-to-pass deduplication, carried through to the written record instead of being dropped at that boundary |
| `timestamp_iso` | `MessageRecord` | `str` | `timestamps.parse_rendered` of the row's rendered `timestamp`. `""` for a row WhatsApp rendered with a clock and no date — never a date inferred from anything outside that row |
| `passes_used` | `ChatExport` | `int` | `history.HarvestResult.passes_used`, the scroll-pass count the harvest reached `completeness` in |
| `source_locale` | `ChatExport` | `str` | The browser locale pinned by `session.launch_context`, e.g. `es-ES` |
| `source_timezone` | `ChatExport` | `str` | The IANA zone `session.resolve_timezone` reads from the page — the zone the page actually rendered in, never the `--timezone` request |
| `undated_messages` | `ChatExport` | `int` | `timestamps.undated_count` over every message's `timestamp_iso` in the export |

`timestamp_iso` sits **beside** `timestamp`, never in place of it: the
rendered string stays the evidence, so a parse later found wrong can be redone
against files already on disk without reopening WhatsApp Web. Only the
locales in `timestamps.LOCALE_DATE_ORDER` are parsed — an unrecognised locale
yields `""` rather than a guessed day/month order.

## 4. Runtime View

1. Operator runs `wa-extract login` → Chromium persistent profile → QR if needed → chat list ready.
2. Operator runs `wa-extract export-one --query "…"` (or `/wa-export …`) →
   search → open chat → **harvest loop** → write `data/*.json`.
3. The harvest loop (`history.harvest_history`) repeats: read the rows in the
   DOM, merge them by message id, decide whether to stop, otherwise scroll one
   pass upward. It exists because WhatsApp Web **virtualizes** the message list:
   rows scrolled out of view are removed from the DOM, so a single read after N
   scrolls loses the recent end of the conversation, and raising N makes the
   loss larger rather than smaller.
4. A pass ends by scrolling to the top, clicking any load-earlier control, and
   polling the panel's signature (row count + scroll height) until it changes or
   `max_wait_ms` elapses. Waiting on a fixed timeout ended the first live
   harvest after 1.2 seconds; the wait is on evidence of loading now.
5. Message identity is WhatsApp's `data-id` when the row carries one, then the
   `conv-msg-<HEX>` wrapper test id, and only then a SHA-1 of
   `sender|timestamp|body|kind`. Without a stable identity, deduplication across
   passes cannot be proven correct — and the hash alone cannot separate two
   captionless voice notes sent by one speaker inside the same minute, which is
   why the wrapper id is consulted first (#005).
6. Pytest exercises `writers`, the pure half of `history`, and row-field
   extraction with stub rows — no live WhatsApp.

### Run journal and resume (ADR-0006, #009)

`wa-extract export-all` records what it did as the run makes progress, not
only once the whole sweep returns: a run over hundreds of conversations takes
hours, so a crash must not erase the record of what was already exported.
Rationale is `docs/decisions/ADR-0006-run-journal-and-resume.md`; this table
states the sequence.

| Step | Event | Function |
| :--- | :--- | :--- |
| 1 | `run_id` minted once, before anything is written | `__main__.mint_run_id` |
| 2 | Journal opened for append at `data/run_journal_<run_id>.ndjson` | `journal.open_journal` |
| 3 | Header written the moment enumeration returns — not before, because `chats_enumerated` is unknown until then, and not after the first conversation, because a run that dies on it would leave no header at all | `journal.write_header`, called from `__main__._record_header` |
| 4 | One outcome appended per conversation, as the run makes it, `fsync`ed to disk before the next chat opens | `journal.append_outcome`, called from `__main__._record_outcome` |
| 5 | Manifest rebuilt from the journal's header and outcomes; every enumerated `chat_id` the journal never reached is recorded `skipped`, reason `run ended before this conversation` | `manifest.manifest_from_journal` |
| 6a | Rebuild at the end of a live run, against the enumeration that same run just produced | `commands.cmd_export_all` (#011) |
| 6b | Rebuild later, from the journal alone, with no enumeration and no browser opened | `commands.cmd_recover` (#011) |

`export-all --resume <run_id>` reopens that same journal in append mode and
steps over the conversations `journal.exported_chat_ids` already found
`exported`; the chat list is enumerated again from scratch, never read back
from the journal. A `failed` or `skipped` outcome does not count as done, so a
resumed run retries it.

**`T-8` closed, Sprint 011: first header wins.** `journal.read_journal` used
to set `header = record` on every `RECORD_HEADER` line with no guard, so a
journal holding two or more `--resume` headers reconstructed `started_at`
from the **last** resume rather than the run's true start — measured against
this project's own 1018-conversation corpus, 570 conversations (56%) carried
an `exported_at` earlier than the date their manifest claimed the run
started. Fixed with a first-write-wins guard
(`if header is None: header = record`); pinned by a regression test against a
synthetic two-header journal, the exact shape that produced the defect.

### Corpus consolidation (#010)

`wa-extract consolidate` joins every per-conversation `data/chat_*.json` an
export run left into one `data/corpus_<source_run>.ndjson`. It opens no
browser, the same posture as `recover`. Design rationale is
`docs/sprints/010-backend-extractor/IMPLEMENTATION_PLAN.md` §Design (D1-D7);
this section states the resulting contract, verified against
`consolidate.read_chat_files`, `consolidate.build_header` and
`consolidate.write_corpus`.

| Line | Content |
| :--- | :--- |
| 1 (header) | `record`, `corpus_schema` (`consolidate.CORPUS_SCHEMA_VERSION`), `chat_schema` (`writers.SCHEMA_VERSION`), `source_run`, `generated_at`, `chat_count` |
| 2…N+1 (body) | One line per conversation, `json.dumps` of its `chat_*.json` payload verbatim — every schema v6 field and every message, nothing flattened, trimmed, or recomputed |

`chat_count` is not a value the caller supplies and this system trusts:
`write_corpus` recomputes it from the ``chats`` list it actually writes and
overwrites whatever the header carried, so the written file's header cannot
disagree with the body beneath it regardless of what built the header
(`src/whatsapp_chat_extractor/consolidate.py`, `§D2`; corrected at the Phase 7
structural gate, which
proved the earlier "written after counting" claim false by execution rather
than by reading the docstring — the pre-fix code computed the count in
`build_header`, independently of what `write_corpus` later wrote).

| Abort | Condition | Exit code |
| :--- | :--- | :--- |
| Duplicate `chat_id` | Two input files under `--data-dir` carry the same `chat_id` | `2`, `ValueError` naming both files — never silently de-duplicated |
| Wrong schema | An input file's `schema_version` is not `writers.SCHEMA_VERSION` (`6`) | `2`, `ValueError` naming the file and the schema found — a v5 file is rejected, never migrated |

Implemented in `src/whatsapp_chat_extractor/consolidate.py`
(`read_chat_files`, `resolve_source_run`, `build_header`, `write_corpus`);
wired by `commands.cmd_consolidate` / `__main__._add_consolidate` (handler
moved to `commands.py` #011).

## 5. Crosscutting Concepts

- Selectors centralized in `session.py` / `export_one.py`; changes logged in `SPIKE_NOTES.md`.
- Customer data and browser profile stay under `data/` (gitignored).
- Logging via stdlib `logging`; no secrets in logs.

## 6. Non-negotiable Constraints

| Constraint | Verification |
| :--- | :--- |
| No live WhatsApp in CI | `python -m pytest tests/ -q` uses fixtures only |
| Exports never committed | `rg -n '^/data/' .gitignore` |
| Text-only messages | Schema has no media fields |
| Truncation is always declared | `complete` / `stopped_reason` in every export; exit `3` |
| No name on disk | `tests/test_writers.py` asserts the name is absent from payload and filename |
| Sender is a role, never a person | `tests/test_row_fields.py` |
| The harvester never clicks inside a message | Candidates are panel chrome; any node under `[data-id]`/`.message-in`/`.message-out` is rejected |
| Older history is loaded without the operator | `_click_load_earlier` matches the control by text across button and `[role=button]` |
| Harvest always terminates | `--max-passes` hard cap and, since #011, `--deadline-seconds` wall-clock cap (`STOP_DEADLINE`); both covered by `tests/test_history.py` |
| Submodule purity | `git -C .agents status --porcelain` empty at close |

## 7. Decisions

- `docs/decisions/ADR-0001-product-scope-whatsapp-web.md`: Web + text JSON + Cursor/scripts split
- `docs/decisions/ADR-0002-delivery-program-and-layout.md`: P1 spike layout + exit criterion
- `docs/decisions/ADR-0003-media-placeholders-in-export.md`: media messages are placeholders, never dropped (schema v4)
- `docs/decisions/ADR-0004-completeness-criterion.md`: `completeness` has three values; `complete` is derived (schema v5)
- `docs/decisions/ADR-0005-enumeration-completeness.md`: `enumeration` states enumeration completeness in three values, replacing a boolean the pane could satisfy while the list moved underneath it (manifest schema v2)
- `docs/decisions/ADR-0006-run-journal-and-resume.md`: append-only NDJSON run journal, `fsync`ed per line, enabling `--resume` and a browserless `recover` (journal schema v1)
- `docs/decisions/ADR-0007-corpus-contract-v6.md`: message identity and a parsed timestamp beside the raw string, pinned locale with resolved timezone recorded, `passes_used`, `undated_messages` (schema v6)
- Sprint #004 brought full history forward from P3: a corpus truncated by a
  scroll count does not serve the stated consumer
  (`docs/sprints/004-backend-extractor/IMPLEMENTATION_PLAN.md`)

## 8. Glossary

| Term | Meaning in this module |
| :--- | :--- |
| Persistent profile | Chromium `user_data_dir` under `data/browser_profile` reused after QR |
| Spike export | Visible DOM messages after limited scroll — the #003 strategy, replaced in #004 |
| Harvest pass | One cycle of read-DOM → merge → decide → scroll |
| Stalled pass | A pass that revealed no message id not already held |
| Row virtualization | WA Web removing off-screen message rows from the DOM |
| Panel signature | Row count + scroll height, compared to detect real loading |
| Bubble tail | `tail-in`/`tail-out` marker WA draws on the first message of a run |
| Speaker label | `Name:` text read only to compare with the chat title, never stored |
| Pseudonymous id | `chat_` + digest of the title; stable, name-free, unsalted |
