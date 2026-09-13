# 📝 Sprint Log: #010

**Stack / Layer**: `backend` / `extractor`
**Branch**: `ai-sprint/009` (folded onto the open sprint branch by human decision)
**Plan**: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — approved 2026-09-10, attended

---

## 🚦 Session Metadata

| Field | Value |
| :--- | :--- |
| Session tool | `claude-code` |
| Delegation mode | `native` |
| Approval | Human, attended, 2026-09-10, against the plan text in this directory |
| Deviation recorded | Executes on `ai-sprint/009`, not a fresh `ai-sprint/010` (`RA-12`) — the owner chose to fold the work onto the open, undeployed Sprint 009 branch. Sprint 009's deployment carries both |
| Phases folded | Phase 3 (no new branch), 4.1/4.2/4.3 (single implementer for code+tests, doc_orchestrator for docs; `jurisdictional_lock` still one file per unit) collapsed into this log |
| Baseline suite | 283 passed / 1 skipped, `ruff check .` exit `0` |

---

## 🎯 Scope

One deliverable: `wa-extract consolidate` — read every `data/chat_*.json`,
validate all are schema v6 with no repeated `chat_id`, and write one
`data/corpus_<run_id>.ndjson` (a provenance header line, then one line per
conversation carrying the whole v6 export verbatim).

Aborts (exit `2`, writes nothing) on a repeated `chat_id` or a non-v6 input.
Design and rejected alternatives: `IMPLEMENTATION_PLAN.md` § Design.

---

## 🏁 Sprint Progression

| Wave | Units | Subject | Status |
| :--- | :--- | :--- | :--- |
| 1 | A1 | `consolidate.py` — read, validate, write | ✅ `935b3be` |
| 2 | A2 | `test_consolidate.py` — NDJSON contract, both aborts | ✅ `54c052d` |
| 2 | B1 | `__main__.py` — `consolidate` subcommand (wiring only) | ✅ `6616d7a` |
| 3 | B2 | `test_consolidate_cli.py` — orchestration, browserless | ✅ `5d0c5cd` |
| 4 | C1 | Blueprint — component + corpus contract subsection | ✅ `ce2e23c` |
| 4 | C2 | Walkthrough — operator section, footer to `#010` | ✅ `d674a95` |

**6 of 6 units landed.** Suite 292 passed / 1 skipped, from a 283/1 baseline at
Sprint 010's open (`+9`, none removed); `ruff check .` exit `0`. No function in
any touched file exceeds `max_lines_per_func` — a repository-wide scan finds
only the two pre-existing `export_one.py` violations, untouched.

**Smoke-tested against the real corpus, not only synthetic fixtures.** Ran
`consolidate --data-dir data --out <tmp>` over the actual 1018
`data/chat_*.json` files from the Sprint 009 whole-account run: wrote 1019
lines (1 header + 1018), header correctly reads `chat_count: 1018` and
`source_run: 20260902T214002Z` (resolved from the newest real manifest), and
did not abort — confirming Sprint 009's own claim of zero duplicate `chat_id`s
holds under the tool built to consume it.

Unit-level state and per-file assignees: `task_scope.md`.

---

## 🔍 Phase 7 — Double-Gate Review

| Gate | Round | Verdict | Class | Notes |
| :--- | :--- | :--- | :--- | :--- |
| QA (structural) | 1 | `REJECTED` | `charter` | Full repository scan from round 1 (31 files, 551 functions), instructed by the Orchestrator after Sprint 009's round-1 miss. Zero complexity/style findings. **Executed the design contract instead of trusting the docstring**: `write_corpus` accepted a header and a body from two independent lists with no reconciliation — proved by calling it with a 1-chat header and a 2-chat body and getting a corpus whose header lied, no error. The false guarantee had propagated into `EXTRACTOR_BLUEPRINT.md` as Law. Also flagged, unrecorded as a charge: a missing `chat_id` crashed with `KeyError` instead of this module's own `ValueError` contract |
| QA (structural) | 2 | `RECORD` | `testifying` | Both round-1 charges verified fixed by direct execution (not the diff): mismatched header/body now reconciled on disk, missing `chat_id` now raises `ValueError` not `KeyError`. Both pinning tests independently mutation-proven a second time. 553 functions, zero new complexity findings. One finding, `F-1` |
| Tester (functional) | 1 | `RECORD` | `testifying` | 294/1 zero regression, verified against `d0cdbb4`. Ran `consolidate` on the real 1018-file production corpus — zero duplicate `chat_id`, provenance exact, both flags and both aborts confirmed through the real CLI. Eight coverage gaps recorded (`T-1`–`T-8`), none charging the sprint — the gate confirmed each falls outside what the plan required |

**The gate verified rather than trusted, on every claim.** It ran against a
throwaway copy of the tree, drove eight separate mutants through the full
suite to show which shipped behaviours have no test able to catch their loss,
and constructed a real message body carrying U+2028/U+2029/U+0085 to
independently confirm round 2's `F-1` fix rather than accepting the commit
message.

**`T-8` is not this sprint's defect, and matters more than the seven others
combined.** While proving `consolidate`'s provenance against real `data/`, the
gate found that the credited manifest's `started_at`
(`2026-09-09T20:56:52Z`) is the timestamp of its **last** `--resume` pass, not
when the run actually began (`2026-09-02T21:40:02Z`). Root cause, confirmed by
the Orchestrator independently: `journal.read_journal` (`journal.py:223-230`)
overwrites `header` on every header record it walks past, so a journal holding
five resume headers — Sprint 009's own — yields only the most recent one.
**570 of 1018 conversations (56%) carry an `exported_at` earlier than the date
the manifest claims the run started.** Not corpus contamination — every
conversation's provenance is otherwise correct — but a corpus consumer dating
the whole export from `source_run`'s manifest is off by up to a week. Carried
below rather than fixed in this sprint: it is `journal.py`/`manifest.py`
territory from Sprint 009, outside `consolidate`'s own scope and this sprint's
Work table.

**`T-8` is carried, by human decision at session #16, 2026-09-13, rather than
hotfixed.** Unlike `H-003`, nothing operational is blocked: every
conversation's own content and identity are correct, and the misdated field is
metadata about the run, not about any message in it. Carried to a future
sprint (`journal.read_journal` must keep the FIRST header's `started_at`, not
the last written) alongside the other Sprint 009 debt already carried
(`§D5`, `§D6`, `T-2`, `KI-009-H`).

The other seven (`T-1` through `T-7`) are mutation-proven coverage gaps in
`consolidate.py` itself, none charging the sprint because each is a behaviour
the plan's `A2`/`B2` rows never required tested: `--from-manifest` has zero
test coverage though it works; four of six header fields are silently
deletable; "newest manifest" selection is untested; the input glob is
unpinned (though a widened glob fails loudly against real data, not silently);
the schema abort is pinned below the CLI only; the `F-1` fix has no
regression test of its own; and `--from-manifest`/`source_run` accepts a path
to a file that was never a real run, the same unvalidated-string shape as the
carried Sprint 009 gap `F-6`.

**`F-1` closed at `0e333b8`.** `str.splitlines()` also breaks on U+2028/U+2029/
U+0085, which `json.dumps(..., ensure_ascii=False)` leaves unescaped inside a
string value a real WhatsApp message body can carry. The four line-counting
sites in `tests/test_consolidate.py` and `tests/test_consolidate_cli.py` —
including the test that proves `write_corpus`'s own `chat_count`
reconciliation — used `.splitlines()` and could have overcounted a file that
was written and would be read correctly by anything iterating the file
object. Switched to `text.rstrip("\n").split("\n")`, matching what
`EXTRACTOR_WALKTHROUGH.md`'s operator guidance already did safely. Reproduced
independently before and after the fix.

**`jurisdictional_lock` reconciled, not waived.** Round 2 was asked to examine
whether `9169e4c` touching two files (`consolidate.py` + its pinning test)
conflicts with "one physical file per unit." It does not: the lock bounds one
file per *task*, not per commit, and both paths were already assigned to the
same unit's assignee in `task_scope.md`. `rules/code_craft.md §6` /
`hooks/on_commit.py`'s `audit_regression_test` **mandates** the pairing for
any `fix(` commit — the two rules point the same direction, not opposite
ones.

---

## 🧠 Rule Amendments & Heuristic Harvest

| # | Finding | Class | Destination |
| :--- | :--- | :--- | :--- |
| *(none yet)* | | | |
