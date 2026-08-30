# Blueprint: EXTRACTOR
**File**: `docs/architecture/EXTRACTOR_BLUEPRINT.md`
**Status**: `RATIFIED`
**Sprint of origin**: #003
**Last Audit Sprint**: #004
**Last Audit Date**: 2026-08-29
**Last Audit Commit SHA**: `b090ed3`

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
| **Must not touch** | Sentiment/bot code; all-chats dump (P3); `.agents/` internals |

| Interface | Type | Defined in |
| :--- | :--- | :--- |
| `wa-extract login` | CLI | `src/whatsapp_chat_extractor/__main__.py` |
| `wa-extract export-one` | CLI | `src/whatsapp_chat_extractor/__main__.py` |
| `ChatExport` JSON | file schema | `writers.ChatExport` / this blueprint §3 |
| `/wa-export <chat>` | slash command | `.claude/commands/wa-export.md` |

Data model (schema v3, #004):
- **ChatExport**: `schema_version`, `chat_id`, `exported_at`, `message_count`,
  `complete`, `stopped_reason`, `messages[]`
- **MessageRecord**: `sender`, `timestamp`, `body`, `order` (text only)

### Identity contract

No personal identifier is written to disk.

| Field | Rule |
| :--- | :--- |
| `chat_id` | `chat_` + first 12 hex of `sha256(chat title)`. Stable across exports |
| filename | `<chat_id>_<stamp>.json` — a directory listing shows no name |
| `title` | Removed in v3. The title is hashed in `build_export` and dropped |
| `sender` | A role — `me`, `contact`, `unknown` — never a name |
| `timestamp` | The bracketed part of `data-pre-plain-text`; the name after it is discarded in the same expression |

This is **pseudonymization, not anonymization**, and the blueprint says so
rather than implying more: the digest is unsalted, so a holder of the contact
list can confirm a match by hashing a candidate name. Message bodies are
untouched and may name people on their own.

### Completeness contract

`complete` is `true` only when the harvest reached the beginning of the chat.
`stopped_reason` keeps a proven start distinguishable from an inferred one,
because WhatsApp Web does not always render a start marker:

| `stopped_reason` | `complete` | Meaning |
| :--- | :--- | :--- |
| `chat_start` | `true` | A start-of-conversation marker was found |
| `stalled` | `false` | The panel stopped loading; the top is inferred, not proven |
| `max_passes` | `false` | The hard cap ended the run; history remains above |

`stalled` counted as complete until the first live run, which exported 217
messages of a longer conversation and marked them complete. Only the marker is
proof; an inference is not recorded as one.

`wa-extract export-one` exits `3` on `complete: false`, so a caller detects a
truncated corpus without parsing the file.

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
5. Message identity is WhatsApp's `data-id` when the row carries one, otherwise
   a SHA-1 of `sender|timestamp|body`. Without a stable identity, deduplication
   across passes cannot be proven correct.
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
| Harvest always terminates | `--max-passes` hard cap, covered by `tests/test_history.py` |
| Submodule purity | `git -C .agents status --porcelain` empty at close |

## 7. Decisions

- `docs/decisions/ADR-0001-product-scope-whatsapp-web.md`: Web + text JSON + Cursor/scripts split
- `docs/decisions/ADR-0002-delivery-program-and-layout.md`: P1 spike layout + exit criterion
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
| Pseudonymous id | `chat_` + digest of the title; stable, name-free, unsalted |
