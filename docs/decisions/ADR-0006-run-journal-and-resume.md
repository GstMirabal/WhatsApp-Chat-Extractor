# ADR-0006: An append-only run journal makes a whole-account export resumable and recoverable without a browser
**Status**: `Accepted`
**Date**: 2026-09-02
**Extends**: [ADR-0001](ADR-0001-product-scope-whatsapp-web.md) (chat-index privacy discipline, unchanged here), [ADR-0004](ADR-0004-completeness-criterion.md) and [ADR-0005](ADR-0005-enumeration-completeness.md) (the per-chat `completeness` and per-run `enumeration` verdicts this journal carries forward unmodified)
**Triggers**: 2, 6 (`rules/documentation_standard.md §3.1`)

---

## 1. Context

A whole-account export walks every enumerated conversation in one browser
session. Measured on 2026-08-31 against 910 conversations, the walk takes
**~15 hours**, at roughly 60 seconds per conversation.

Before this decision, `cmd_export_all` called `build_manifest` and
`write_manifest` **only after** its export loop returned. The loop held no
checkpoint: an uncaught exception, `kill`, `Ctrl-C`, a crashed browser, or the
operator's machine sleeping left the process without ever reaching either
call, and **nothing was written** — not which conversations had exported,
which had failed and why, `ADR-0005`'s enumeration verdict for that run, or
the `chat_id` → title index.

The exported chat files (`data/chat_<digest>_<stamp>.json`, written by
`write_chat_export`) survive a crash; the *record of the run* does not, and
the digest that names each file is one-directional, so a surviving file
cannot be matched back to its position in the run without that record. A
crash at hour 12 of a 15-hour run destroys the account of roughly 700
already-exported conversations and forces the operator to repeat the full 15
hours to find out again what had already been done.

Separately, three files of one run each derived their own
`datetime.now(UTC)` timestamp — `write_manifest`, `write_chat_index`, and
`write_chat_export` — so no single identifier named "this run" across its own
outputs.

**Reproduction of the defect this decision closes**: `python3 -m pytest
tests/ -k "resume or journal"` failed with `no tests ran` before this sprint.

## 2. Decision

| # | Topic | Decision |
| :--- | :--- | :--- |
| D1 | Journal format | Append-only NDJSON at `data/run_journal_<run_id>.ndjson` (`journal.py:64-98`), one line per conversation outcome. `Path.write_text` truncates before writing, so rewriting the manifest after each conversation would make the rewrite itself the corruption window — a crash mid-rewrite empties the one file holding the record. Appending cannot destroy what is already on disk. Every write is followed by `flush()` and `os.fsync(fileno)` (`journal.py:112-114`); only a power cut or kernel panic can lose an appended line — a `kill -9` keeps it in the OS buffer regardless. `read_journal` (`journal.py:198-232`) discards an unparseable **final** line as an expected torn write, and raises `ValueError` on a broken line anywhere else, because that can only mean a written record was damaged afterward (`journal.py:235-255`). |
| D2 | `run_id` identity | Minted once by `mint_run_id()` (`__main__.py:108-120`) before `cmd_export_all` opens anything, then threaded through the journal, `write_manifest`, and `write_chat_index`, so every file one run produces shares one identity instead of each deriving its own timestamp. `write_chat_export`'s own filename is unchanged — it keeps deriving its own stamp, deliberately, so existing readers of exported chat files do not break. `--resume RUN_ID` takes this identity as an argument: without a stable identity there is nothing to name when resuming. |
| D3 | Resume re-enumerates | `--resume` re-runs `sweep_until_stable` against the live chat list (`_export_every_chat`, `__main__.py:327-368`) rather than trusting the positions and digests a journal recorded up to 15 hours earlier. `ADR-0005` established that the chat list reorders under an arriving message, so a stored ref could now point at the wrong conversation — the failure mode [`H-001`](../hotfixes/H-001-backend.md) was opened against. The journal is consulted **only** through `exported_chat_ids` (`journal.py:271-291`), which returns the `chat_id` set with outcome `exported`; those are stepped over (`if ref["chat_id"] in done: continue`, `__main__.py:356-358`). A `failed` entry is retried; a `skipped` one was never attempted. Conversations that appeared between the crash and the resume are exported; conversations the new sweep no longer finds are simply absent from it, not misreported by the manifest. A resume is a new run that reuses prior work, not a continuation of the old one. |
| D4 | `recover` is a separate subcommand | `cmd_recover` (`__main__.py:591-612`) rebuilds a manifest from a journal alone and opens no browser — Playwright is imported inside `cmd_login`, `cmd_export_one`, and `_export_all_session` only, never at module level (`__main__.py:1-7`), so `recover` runs on a machine that cannot launch Chromium. Reconstructing what a dead run did is forensic and answers "what happened"; `--resume` is hours of new browser work that answers "finish it." Folding the two would force opening WhatsApp Web to answer a question that does not need it. |
| D5 | Title index stays behind `--write-index`, in a separate file | `ADR-0001` keeps real names out of `data/` by default; the outcomes journal carries no titles at all (`journal.py:24-26`). With `--write-index`, `manifest.write_chat_index` (`manifest.py:300-337`) writes the one file in the project that does carry names, `data/chat_index_<run_id>.json`, and `_titles_for_index` (`__main__.py:492-522`) folds this pass's titles into whatever an earlier pass of the same `run_id` already wrote there — a resumed run would otherwise overwrite the earlier pass's names with only the few this pass reopened. |
| D6 | New module, not growth of `export_one.py` | The journal's read/write/durability logic lives entirely in the new `journal.py`; `export_one.py` (681 lines before this sprint, already carrying two of the project's pre-existing complexity violations) is untouched. `HarvestedRow` already carried `message_id` and `collect_visible_rows` already filled it, so nothing this sprint needed from that file. |

**What D5 does not do, against what was planned.** The Implementation Plan
(`IMPLEMENTATION_PLAN.md` §D5) specified a *second append-only NDJSON
journal*, `data/chat_index_<run_id>.ndjson`, with "the same append discipline"
as the outcomes journal. The shipped `write_chat_index` does not do this: it
still performs one batched `path.write_text` of a JSON object
(`manifest.py:328-331`), called exactly once, after `_export_every_chat`
returns (`cmd_export_all`, `__main__.py:584-586`). `_titles_for_index` reads
back and merges the *previous* pass's already-completed `.json` file — it
gives the current pass no durability of its own. The practical effect: the
outcomes journal survives a crash losing at most its torn final line, but if
the process dies before `cmd_export_all` reaches its post-loop
`write_chat_index` call, every title `--write-index` collected during that
pass is gone in full, with nothing to recover it from —
`manifest_from_journal` carries no title field to rebuild one. This is a real
gap against the plan's stated durability guarantee for D5, not a
documentation-only slip.

**D6 held for `export_one.py`, not for `__main__.py`.** The plan's own
rationale named both files as already large and already carrying complexity
violations (`__main__.py` at 421 lines, `export_one.py` at 681) and stated
the large files "only call" the new modules. `__main__.py` is now 794 lines —
the CLI orchestration this half of the sprint needed (`RunJournal`,
`mint_run_id`, `_record_header`/`_record_outcome`, the rewritten
`_export_every_chat`, `_request_timezone`/`_confirm_timezone`,
`_latest_per_chat`, `_manifest_from_journal_file`, `_titles_for_index`,
`_run_exit_code`, `_warn_on_partial_enumeration`, `cmd_recover`) landed
directly in it rather than in a new module. `journal.py` holds only the
line-level read/write/durability primitives; every decision about *when* to
call them stayed in `__main__.py`. The file grew by roughly 373 lines against
the figure the plan itself cited as already too large.

### Three points the plan did not decide

1. **Timezone imposition is a request through the environment, not a
   Playwright argument.** `session.launch_context` (`session.py:63-69`) takes
   `locale` but no `timezone_id` — `session.py` was another Sprint 009 unit's
   file, out of this file's jurisdiction. `_request_timezone`
   (`__main__.py:371-386`) sets `os.environ["TZ"]` before Chromium launches
   instead. This is a request, not a guarantee: `_confirm_timezone`
   (`__main__.py:389-408`) reads back what the page actually resolved via
   `resolve_timezone`, and that reading — never the requested value — is what
   every export records, because recording an unconfirmed request would put a
   false frame on every timestamp in the corpus. A true imposition needs
   `launch_persistent_context(..., timezone_id=requested)` inside
   `session.py`, which no unit of this sprint held the file lock to add.
2. **A resumed run's journal can hold two lines of history for one
   conversation.** Because D1 opens the journal in append mode and D2 keeps
   the resumed run's `run_id`, a conversation that `failed` on the first pass
   and `exported` on the resume carries both lines in the same file. Both are
   true of what happened; only the last is true of the result.
   `_latest_per_chat` (`__main__.py:440-458`) folds by `chat_id`, keeping only
   the last-written outcome, before `manifest_from_journal`
   (`manifest.py:209-262`) ever sees the list — otherwise one conversation
   could count as both failed and exported in the same manifest.
3. **`recover` reports a count it cannot name the members of.**
   `manifest_from_journal` marks an enumerated `chat_id` absent from the
   journal's outcomes as `skipped`, reason `run ended before this
   conversation` (`manifest.py:246-255`) — but only for refs present in
   `enumerated_refs`. `cmd_recover` has no browser and passes
   `enumerated_refs=[]` (`__main__.py:602`), consistent with D3's own rule
   that the journal deliberately holds no chat-list positions to fall back
   on. `recover` therefore cannot say *which* conversations a dead run never
   reached, only *how many*: `unrecorded = manifest["chats_enumerated"] -
   len(manifest["chats"])`, logged as a warning that names the count and
   points the operator at `--resume` (`__main__.py:604-611`).

## 3. Consequences

| Easier | Harder |
| :--- | :--- |
| A crash at any point during a ~15-hour run leaves a journal that reconstructs the manifest for every conversation attempted so far | The chat-index title file (D5) does not share the outcomes journal's crash safety — see the D5 gap above |
| `--resume RUN_ID` skips only conversations the journal marks `exported`, so a crash never forces repeating already-exported work | `--resume` still pays the full re-enumeration sweep before doing anything else, because `ADR-0005` established that trusting stored positions can open the wrong conversation |
| `recover` answers "what did that dead run do" with no browser, in seconds rather than hours | `recover` cannot name the conversations a dead run never reached, only count them — reaching them still needs `--resume` |
| One `run_id`, minted once, names every file one run produces | A live `cmd_export_all` completion whose manifest shows `chats_enumerated` greater than `len(chats)` would indicate the enumeration/recording invariant broke, since a normal run's own loop writes or inherits an outcome for every ref it enumerates |

**Privacy is unchanged.** The outcomes journal carries no title, matching
`ADR-0001`; `data/chat_index_<run_id>.json` remains the one file with names,
unlocked only by `--write-index`, in the same discipline it followed before
this sprint.

## 4. Deciders

Human (product owner), 2026-09-02, at the Sprint 009 Approval Gate. Approved
as part of the Sprint 009 Implementation Plan, whose Design §D1–§D6 carries
this decision.

## 5. Considered Options

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **A — Rewrite the whole manifest after each conversation (status quo)** | No new file format; one file to read | Rejected by measurement: 910 rewrites over one run write 414,505 entries in total (`python3 -c "print(sum(range(1, 911)))"`), and `Path.write_text` truncates before writing, so a crash during rewrite 700 empties the one file holding the record of the 699 before it |
| **B — Append-only NDJSON journal, `run_id` minted once, `--resume` re-enumerates, `recover` as a separate subcommand (chosen)** | A crash loses at most a torn final line; one identity per run; resume never opens the wrong conversation; forensic recovery needs no browser | Two files per run instead of one (journal plus manifest); a resumed journal can carry more than one outcome line per conversation, requiring the `_latest_per_chat` fold |
| **C — Fold `recover` into `--resume`** | One flag, one mental model | Rejected (`§D4`): forces opening WhatsApp Web to answer a question — "what did the dead run do" — that costs nothing to answer without a browser |
| **D — Trust the journal's stored refs on resume, skip re-enumeration** | A resume would be fast — no new sweep | Rejected: a stored ref is a position and digest captured up to 15 hours earlier, and the chat list reorders under an arriving message (`ADR-0005`); reusing it risks opening the wrong conversation, which [`H-001`](../hotfixes/H-001-backend.md) was opened to stop |

---
*Immutable once Accepted — a changed decision gets a new ADR that supersedes
this one, never an in-place edit (`rules/documentation_standard.md §3`). File
lives at `docs/decisions/ADR-0006-run-journal-and-resume.md`.*
