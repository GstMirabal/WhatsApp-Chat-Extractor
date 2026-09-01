# Blueprint: EXTRACTOR
**File**: `docs/architecture/EXTRACTOR_BLUEPRINT.md`
**Status**: `RATIFIED`
**Sprint of origin**: #003
**Last Audit Sprint**: #008
**Last Audit Date**: 2026-09-01
**Last Audit Commit SHA**: `d30a1b5`

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
| `wa-extract login` | CLI | `src/whatsapp_chat_extractor/__main__.py` |
| `wa-extract export-one` | CLI | `src/whatsapp_chat_extractor/__main__.py` |
| `wa-extract export-all` | CLI | `src/whatsapp_chat_extractor/__main__.py` (#007) |
| `ChatExport` JSON | file schema | `writers.ChatExport` / this blueprint §3 |
| `RunManifest` JSON | file schema | `manifest.RunManifest` / this blueprint §3 (#007) |
| `/wa-export <chat>` | slash command | `.claude/commands/wa-export.md`, `.cursor/commands/wa-export.md` |

Data model (schema v5, #007):
- **ChatExport**: `schema_version`, `chat_id`, `exported_at`, `message_count`,
  `complete`, `completeness`, `stopped_reason`, `messages[]`
- **MessageRecord**: `sender`, `timestamp`, `body`, `kind`, `order` — every
  message, whatever medium it carried
- **RunManifest** (`manifest.py`, manifest schema v2, #008): `schema_version`,
  `started_at`, `finished_at`, `chats_enumerated`, `enumeration`, `sweeps`,
  `counts`, `chats[]`. The manifest versions independently of `ChatExport`:
  it is at v2 while the export file is at v5
- **ChatOutcome**: `chat_id`, `index`, `outcome`, `reason`, `completeness`,
  `message_count`, `file` — one per conversation the sweep found

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
exception and is named for it: `data/chat_index_<stamp>.json`, written only when
the operator passes `export-all --write-index`, maps `chat_id` back to the real
conversation name. It is a separate file from the run manifest so it can be
deleted without losing the record of what a run did, and the manifest itself
never carries a title.

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
| `truncated` | `false` | `max_passes`, or `stalled` while loading | The harvest ended before the conversation did |

`classify_completeness` **fails closed**: a stop reason it does not recognise is
`truncated`, never `proven`. An unknown reason is not evidence of having arrived.

The `stalled`-while-loading pairing is defensive rather than reachable, and
deliberately kept: `decide_stop` suppresses the stall verdict while the panel is
fetching, so the harvest loop no longer produces it. It is exactly what Sprint
006's probe run 3 recorded before that fix — 175 passes with a `loading-spinner`
still on screen — and classifying it as `unproven` would reinstate the error the
fix removed.

`stalled` counted as complete until the first live run, which exported 217
messages of a longer conversation and marked them complete. Only the marker is
proof; an inference is not recorded as one.

**A stall requires a quiet panel, not merely a quiet pass (Sprint 006).**
`decide_stop` takes `panel_loading`, and a visible loading indicator
(`LOADING_SELECTORS`) suppresses the `stalled` verdict: a spinner is positive
evidence that more history is coming, so stopping on it reports a top that was
never reached. `max_passes` is deliberately *not* suppressed, so a spinner that
never resolves still terminates the run and says `max_passes` — the honest
reason — rather than claiming a top. Measured: one conversation was declared
`stalled` after 175 passes with a spinner on screen, and ran 255 with the panel
genuinely quiet once corrected.

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
| Harvest always terminates | `--max-passes` hard cap, covered by `tests/test_history.py` |
| Submodule purity | `git -C .agents status --porcelain` empty at close |

## 7. Decisions

- `docs/decisions/ADR-0001-product-scope-whatsapp-web.md`: Web + text JSON + Cursor/scripts split
- `docs/decisions/ADR-0002-delivery-program-and-layout.md`: P1 spike layout + exit criterion
- `docs/decisions/ADR-0003-media-placeholders-in-export.md`: media messages are placeholders, never dropped (schema v4)
- `docs/decisions/ADR-0004-completeness-criterion.md`: `completeness` has three values; `complete` is derived (schema v5)
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
