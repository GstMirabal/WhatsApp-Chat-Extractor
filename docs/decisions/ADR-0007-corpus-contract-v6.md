# ADR-0007: Corpus contract v6 — message identity, parsed timestamps, and rendering provenance
**Status**: `Accepted`
**Date**: 2026-09-02
**Supersedes**: Nothing in [ADR-0001](ADR-0001-product-scope-whatsapp-web.md) — see §1.6
**Extends**: [ADR-0001](ADR-0001-product-scope-whatsapp-web.md) §2 ("message body + who + when/order"); [ADR-0004](ADR-0004-completeness-criterion.md) (`complete` stays derived from `completeness` — unchanged by this schema bump, see §2.2)
**Triggers**: 1, 2 (`rules/documentation_standard.md §3.1`)

---

## 1. Context

Schema v5 (`ADR-0004`, `ADR-0003`) exports a chat as an ordered list of
messages plus a completeness verdict. Three gaps in that payload block the
corpus from being analysed rather than only read, and one measurement is
simply missing:

| Gap | Evidence |
| :--- | :--- |
| No message identity reaches the file | `history.HarvestedRow` already carries `message_id` (`history.py:74-81`) — `MessageAccumulator` indexes on it to deduplicate (`history.py:156-157`) — and `MessageAccumulator._as_record` dropped it before v6, so no message in the corpus could be recognised across two exports of the same chat |
| The timestamp is a rendered string of unknown day/month order | `MessageRecord.timestamp` (`writers.py`) is `export_one._row_timestamp`'s output verbatim: `[HH:MM, D/M/YYYY]` or `[HH:MM, M/D/YYYY]` depending on the browser locale, and nothing recorded which locale rendered it — `3/9` is a real date either reading |
| No timezone is recorded | The export never stated what zone the message clocks are relative to |
| The undated fraction is unmeasured | `msg-meta`'s fallback (`export_one.py:673-679`) yields `HH:MM` with no date at all for some rows, and how often that happens has never been counted |

This ADR records the four decisions Sprint 009's Implementation Plan made to
close those gaps (`IMPLEMENTATION_PLAN.md` §D7–§D10) and the two further
decisions the implementation made that plan text did not spell out (§1.5).

### 1.1 D7 — Pin the render locale, record the timezone, never impose it

Two distinct decisions, resolved differently on purpose.

**The locale is pinned.** `session.launch_context` passes `locale="es-ES"` to
`playwright.chromium.launch_persistent_context` (`session.py:68`, `93`,
`DEFAULT_LOCALE` at `session.py:28`). This is the locale the operator's
machine already rendered under, so pinning it changes no observed behaviour —
it converts an unrecorded fact into a recorded one. `timestamps.py` parses
exactly the locales it has been told the rendering shape of
(`LOCALE_DATE_ORDER`, `timestamps.py:46-53`); an unlisted locale returns `""`
rather than guessing an order (`timestamps.py:60-73`, `116-122`).

**The timezone is read, never imposed.** `session.resolve_timezone` evaluates
`Intl.DateTimeFormat().resolvedOptions().timeZone` on the page
(`session.py:34`, `99-126`) and returns what the browser answers, or `""` when
the page could not answer (`session.py:118-126`). `session.launch_context`
takes no `timezone_id` parameter (`session.py:63-69`) — Playwright's
persistent-context launch is never asked to render clocks in any particular
zone. `ChatExport.source_timezone` therefore states an observation, never a
request. This is why it is trustworthy: the recorded value is exactly what the
page's own `Intl` resolution produced, not a value the CLI told the browser to
adopt and then repeated back unverified.

### 1.2 D8 — `timestamp_iso` beside the raw string, never in its place

`MessageRecord` keeps `timestamp` unchanged and adds `timestamp_iso`
(`writers.py:46-49`). `history.MessageAccumulator._as_record` computes it with
`timestamps.parse_rendered(rendered, locale=locale)` (`history.py:196-205`)
and writes both fields from the same row.

The raw string is retained as evidence: if a parse is later found wrong, it
can be redone against files already on disk without reopening WhatsApp Web
(`timestamps.py:1-13`). `timestamp_iso` is `""`, never an invented date, for a
row WhatsApp rendered with a clock and no date
(`timestamps.py:20-23`, `123-125`) — the same discipline `_row_kind` already
applies to `unknown` senders and kinds. `writers.build_export` counts the
empties into `ChatExport.undated_messages` via `timestamps.undated_count`
(`writers.py:186-188`, `timestamps.py:158-172`), so the first run under v6
measures the undated fraction without a separate live probe.

### 1.3 D9 — Schema v6 is additive; no v5 file is rewritten

No v5 field changes name or meaning. `MessageRecord` gains `message_id` and
`timestamp_iso`; `ChatExport` gains `passes_used`, `source_locale`,
`source_timezone` and `undated_messages` (verified against the TypedDicts at
`writers.py:26-53` and `writers.py:55-113`; see §2.1 for the full table).

**Files already on disk under schema v5 are not touched by this decision and
stay exactly as they are.** They carry timestamps rendered under a locale that
was never recorded and no `message_id`. No script in this sprint reads,
re-parses, or rewrites a v5 file. This is deliberate, not an oversight: there
is no record of which locale rendered any v5 file's timestamps, so a
retroactive repair — guessing `D/M` versus `M/D` from context, or
back-filling a `message_id` from a `sha1:` fallback computed after the fact —
would be a conjecture presented as a correction. `timestamps.py`'s own
discipline (an unlisted locale returns `""` rather than guessing,
`timestamps.py:14-18`) forbids the same guess here. The gap in v5 files is
accepted as permanent.

### 1.4 D10 — Two ADRs, not one

`ADR-0006` (unit D1, a separate physical file) covers the run journal and
`--resume`: the record of *an execution*. This ADR covers the corpus
contract: the payload of *a conversation*. Different objects with different
consumers — an operator recovering a killed run reads the journal; an
external AI system reading the JSON (`ADR-0001` §2, "Consumers") reads the
export. Merging them into one ADR would make it unreadable which one a future
change supersedes.

### 1.5 Two decisions the implementation made that plan text did not state

| # | What the plan text implied | What the code does | Where |
| :--- | :--- | :--- | :--- |
| 1 | §D7's prose reads `--timezone permite imponerla explícitamente cuando el operador lo decida` ("lets the operator impose it explicitly") | `--timezone` cannot impose a zone. `session.launch_context` takes no `timezone_id` parameter, so `--timezone` is implemented as an environment request: `_request_timezone` sets `os.environ["TZ"]` before the browser launches, which the Chromium process may or may not honour (`__main__.py:371-386`). `_confirm_timezone` then reads back what the page actually resolved and warns, but never substitutes, when it disagrees with the request (`__main__.py:389-408`). `ChatExport.source_timezone` is always the confirmed value, never the requested one | `__main__.py:371-408`, `426`, `434` |
| 2 | Neither §D6 nor §D7–§D10 names `cmd_export_one` | `cmd_export_one` (the single-chat CLI path) writes schema v6 too. Its `build_export` call was patched with the same four fields as the whole-account path (`passes_used`, `source_locale`, `source_timezone` via `resolve_timezone(page)`), so a single-conversation export is not left as a v5 island | `__main__.py:147-188`, call at `174-182`; whole-account equivalent at `_export_open_chat`, `__main__.py:223-251`, call at `242-250` |

Row 1 is a disagreement between the plan's prose and the landed code, not a
restatement: the code is what shipped, and what shipped is deliberately
weaker than "impose" — §1.1 above states why an unverified imposed value
would be untrustworthy. Row 2 is not a disagreement, only an omission in the
plan text that the commit closed.

### 1.6 Relationship to `ADR-0001` — explicit boundary

| ADR-0001 §2 row | Status under this ADR |
| :--- | :--- |
| Product boundary (export JSON only) | Unchanged |
| Source (WhatsApp Web, single business number) | Unchanged |
| Coverage — "Full history, text only" | Unchanged |
| Coverage — "message body + who + when/order" | **Extended, not superseded.** The "when" component gains structure: a parsed `timestamp_iso` beside the existing rendered `timestamp`, plus file-level `source_locale`/`source_timezone` stating the frame those clocks were rendered in. The raw string ADR-0001 already covered is still written, unchanged |
| Operator UX, automation split, runtime, output location | Unchanged |
| Consumers ("External AI / learning systems read the JSON") | Unchanged; this ADR is written for that consumer — the fields it adds make the corpus analysable rather than only readable |

**This ADR supersedes nothing in `ADR-0001`.** No decision recorded there is
reversed or replaced. It is an extension of a single row (Coverage,
"when") under the boundary `ADR-0001` already set, in the same relationship
`ADR-0005` has to `ADR-0004` — a decision at a different altitude of the same
subject, not a correction of it. Compare `ADR-0004`, which *did* supersede an
`ADR-0001` semantic (the `complete` reading of "full history"): no such
semantic exists in `ADR-0001` for message identity or timezone, so there is
nothing here for this ADR to supersede.

## 2. Decision

### 2.1 Fields added in schema v6

| Container | Field | Type | Source | Semantics |
| :--- | :--- | :--- | :--- | :--- |
| `MessageRecord` | `message_id` | `str` | `history.HarvestedRow["message_id"]`, passed through unchanged (`history.py:202`) | Stable identity for the row; a real WhatsApp `data-id` or a `sha1:`-prefixed fallback (`history.fallback_message_id`, `history.py:99-126`) |
| `MessageRecord` | `timestamp_iso` | `str` | `timestamps.parse_rendered(timestamp, locale=locale)` (`history.py:205`) | `YYYY-MM-DDTHH:MM`, no timezone offset attached; `""` when the row carries no date, the locale is unrecognised, or the parsed components name no real calendar date (`timestamps.py:96-129`) |
| `ChatExport` | `passes_used` | `int` | `history.HarvestResult["passes_used"]`, forwarded by `build_export` (`writers.py:144`, `168-170`, `192`) | Scroll passes the harvest spent; the context `completeness` must be read in |
| `ChatExport` | `source_locale` | `str` | `session.DEFAULT_LOCALE`, passed at the call site (`__main__.py:180`, `248`) | BCP 47 tag the page rendered under. Empty means unrecorded — the state every export before v6 is effectively in |
| `ChatExport` | `source_timezone` | `str` | `session.resolve_timezone(page)`, confirmed value only (§1.1, §1.5 row 1) | IANA zone the browser's `Intl` resolution named, or `""` when the page could not answer |
| `ChatExport` | `undated_messages` | `int` | `timestamps.undated_count(...)`, derived inside `build_export`, never accepted as a caller argument (`writers.py:156-158`, `186-188`) | Count of messages whose `timestamp_iso` is `""` |

`SCHEMA_VERSION` is `6` (`writers.py:17`).

### 2.2 What v6 leaves untouched

| Prior decision | Status under v6 |
| :--- | :--- |
| `ADR-0004`: `complete` is derived from `completeness`, never accepted independently | **Unchanged.** `writers.build_export` still computes `"complete": completeness == COMPLETENESS_PROVEN` (`writers.py:189`) and `history.build_result` still computes the identical expression (`history.py:325`). No caller of either function can set `complete` on its own in v6, exactly as in v5 |
| `ADR-0003`: `kind` is mandatory on every message | Unchanged; `kind` is untouched by this schema bump |
| `ADR-0005`: `enumeration`/`sweeps` on the run manifest | Unrelated container — the manifest and the chat export are different files (`ADR-0005` §2, "Export schema: Untouched") |
| v4→v5 `complete` boolean retained for backward compatibility | Unchanged; the same reasoning that kept it at v5 keeps it at v6 |

## 3. Consequences

| Easier | Harder |
| :--- | :--- |
| A consumer can recognise the same message across two exports of one chat (`message_id`), enabling merge/dedupe workflows this repository does not itself implement (`ADR-0001` §2, "Consumers") |  |
| Reply latency and time-of-day analysis become possible on rows with a date, without re-touching WhatsApp Web | Rows with no date (`undated_messages`) still cannot answer those questions; the count makes the gap visible instead of silent |
| A reader knows the frame every v6 file's clocks are relative to (`source_locale`, `source_timezone`) | v5 files carry no such frame and cannot be repaired retroactively (§1.3) — they remain permanently under-specified |
| The undated fraction is measured by the first run rather than requiring a separate probe |  |
| `passes_used` gives `completeness` a comparable context across runs | Consumers must read three more fields; no schema-version consumer breaks, because every v6 addition is additive |

**Privacy is unchanged.** `message_id`, `timestamp_iso`, `passes_used`,
`source_locale`, `source_timezone` and `undated_messages` describe message
identity, timing, and rendering context — never a name. `chat_title` is still
consumed only to be hashed and dropped (`writers.py:150-153`,
`pseudonymous_chat_id`, `writers.py:116-135`). No content, sender name, or
contact identifier newly reaches disk.

## 4. Deciders

Human (product owner), at the Sprint 009 Approval Gate. Approved as part of
the Sprint 009 Implementation Plan
(`docs/sprints/009-backend-extractor/IMPLEMENTATION_PLAN.md`, status
`APPROVED` → `EXECUTING`), whose §D7–§D10 (lines 178-231) carries these four
decisions and the trade-off accepted for each.

## 5. Considered Options

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **A — Status quo, schema v5 unchanged** | No change; no schema break | Rejected. `message_id` was already computed and discarded (§1); the corpus could not be merged, corrected, or deduplicated across exports, and the timestamp's day/month order was unrecorded |
| **B — Replace `timestamp` with `timestamp_iso`, drop the raw string** | Smaller payload; one timestamp field | Rejected (`D8`). A wrong parse would be unrecoverable without re-scraping WhatsApp Web; the raw string is the only evidence a later fix can be checked against |
| **C — Impose the timezone via a forced browser setting** | A requested zone would always match the recorded zone | Rejected. `launch_persistent_context` accepts no `timezone_id` in this codebase's usage, and forcing one would shift every rendered clock away from what the operator sees and away from every export written before v6; whether the corpus *should* be forced into a zone is a decision for the operator, not a default this ADR can set (`session.py:30-33`) |
| **D — Additive v6, raw timestamp retained, timezone read and confirmed rather than imposed, v5 files left untouched (chosen)** | Corpus becomes analysable; no evidence is destroyed; no file is rewritten on a guess; recorded values are always independently confirmed | Schema break for new consumers reading the field set; the undated fraction and the v5/v6 gap remain permanent facts about the corpus rather than something a later migration can retroactively fix |
| **E — Retroactively repair v5 files (backfill `message_id`, re-parse `timestamp_iso`)** | Would make the whole corpus uniform at v6 | Rejected (`D9`). No record exists of which locale rendered any v5 file, so a `D/M` versus `M/D` reading would be a guess, and a synthesised `message_id` could not be verified against the original DOM. The same discipline that returns `""` for an unlisted locale in `timestamps.date_order` forbids guessing here |

Option E was the closest alternative to D and is rejected on the same ground
`timestamps.py` states for itself: an unlisted or unrecorded rendering
context must return nothing, never an inferred value presented as a fact.

---
*Immutable once Accepted — a changed decision gets a new ADR that supersedes this one, never an in-place edit (`rules/documentation_standard.md §3`). File lives at `docs/decisions/ADR-0007-corpus-contract-v6.md`.*
