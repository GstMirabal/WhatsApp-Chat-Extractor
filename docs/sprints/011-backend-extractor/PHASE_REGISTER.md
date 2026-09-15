# Phase Register — Sprint 011 (`backend-extractor`)

Which pipeline phase ran, what it left behind, and what proves it. A phase that
left no artifact did not run (`close_workflow.md` Phase 2.6).

| Phase | Ran | Artifact | Evidence |
| :--- | :--- | :--- | :--- |
| 1. Planning | Yes | `IMPLEMENTATION_PLAN.md` | `audit_plan.py` → `[OK]`, exit `0`. Drafted via Claude Code plan mode, committed at `13aa85c` |
| 2. Environment | Yes | none (precondition) | `.venv` present, no `.env` in this project, no Docker/DB. `git status --porcelain` shielded before branching |
| 3. Roadmap | Yes | `SPRINT_LOG.md` | **Deviation, corrected during the sprint**: Phase 3 originally extracted only `IMPLEMENTATION_PLAN.md` and skipped `SPRINT_LOG.md`; the gap was found before Phase 7 and the file was written retroactively (`1b84a3c`) by the Orchestrator from the real commit history |
| 4.1–4.3 | Yes | `agent_assignment.md`, `skill_assignment.md`, `task_scope.md` | `check_forge_ladder.py` and `check_task_scope.py` both exit `0`. Committed at `f16ecfb` |
| 5. Approval Gate | Yes | none (human) | Human, attended, 2026-09-15, explicit "ok" against the committed plan text. Recorded at `8238b3a` |
| 6. Execution | Yes | 13/13 Work-table units, 5 blocks | See Units delivered below |
| 7. Quality Gate | Yes | four rows in `SPRINT_LOG.md` | QA Round 1 `REJECTED`/`charter` (real finding, not procedural), Round 2 `APPROVED`/`none`; Tester `RECORD`/`testifying`. `RECORD` does not count toward escalation (`RA-17`) |
| 8. Closeout | Yes | this file | Blueprint, Walkthrough, Global Roadmap and Master Ledger updated |

## Units delivered

13 planned, all landed, zero scope change during execution. One deviation
(Block E's last two rows, `T-1`/`T-5`) was completed by `principal_agent`
after the dispatched `implementer_agent` subagent hit a session-wide API rate
limit mid-row; the work it had already committed (`4a188b5`, `914277d`) was
left untouched and the remaining two tests were written to the same design.

| Block | Units | Subject | Outcome |
| :--- | :--- | :--- | :--- |
| A | 1–3 | `KI-009-H` | `STOP_DEADLINE` threaded through `harvest_history`; `--deadline-seconds` CLI flag; 4 pinning tests. The one item the roadmap marked as blocking a fully unattended run |
| B | 4–5 | `T-8` | `journal.read_journal` keeps the first `RECORD_HEADER`, not the last. Regression test with two synthetic resume headers |
| C | 6–9 | `§D6` + pre-existing complexity | `commands.py` (new, 636 lines) absorbs every `cmd_*` handler; `__main__.py` 854→277 lines, argparse wiring only; `export_one.py`'s two over-length and two depth-4 functions extracted into named helpers |
| D | 10–11 | `§D5` | `manifest.write_chat_index` retired; `chat_index_<run_id>.ndjson` written append-only via `open_chat_index_journal`/`append_chat_index_entry`, mirroring `journal.py`'s discipline |
| E | 12–13 | `T-2`, `T-1`–`T-7` | 8 coverage gaps closed, test-only, zero production changes |

Follow-up commit not tied to a Work-table row: `c39020d`, correcting
`--write-index` CLI help text left stale by Block D.

## The Phase 7 structural gate — one round of bounce, by execution

QA Round 1 (`ae7f86939da07ec35`'s predecessor) audited all 13 Work-table units
and rejected on one finding: Block B's fix (`293ea35`) pushed
`journal.py::read_journal` from block-nesting depth 3 to depth 4
(`agents.md §1 max_indentation`) — a violation the plan's own Verification
table did not catch because it scoped its AST re-check to `export_one.py`,
`__main__.py` and `commands.py` only, never naming `journal.py`. Fixed in
`a0b6122` with the semantics-preserving form QA's own report prescribed,
avoiding the trap of a collapsed-condition rewrite that would have silently
broken the two-header regression test's guarantee. QA Round 2 re-audited all
14 changed `.py` files from scratch (not just the one that failed) and
returned `APPROVED`/`none`.

Tester Agent's Gate 2 pass measured a real pre-sprint baseline (294 passed / 1
skipped on `main` at `136c1e1`, exported via `git archive` rather than
assumed) against the branch's 316 passed / 1 skipped, and mutation-killed five
production behaviors to confirm the sprint's own test claims were not
tautologies. One coverage gap was surfaced as `RECORD`/`testifying`, not a
bounce: `--deadline-seconds` is proven correct at the pure `decide_stop`
level but has no test covering its CLI-to-harvest wiring in `commands.py` —
a mutation making the flag a total no-op left the whole suite green. This
resembles the pre-existing `test_strength_gaps` F-4 finding and is carried
forward rather than fixed in this sprint (see Roadmap update).

## Carried forward, unscheduled

| Item | Origin |
| :--- | :--- |
| `--deadline-seconds` end-to-end coverage gap | Found by Tester Agent, Sprint 011 Gate 2. Same harness-gap class as `test_strength_gaps` F-4 (`docs/active_state.json`) — needs a Playwright harness this project does not have |
| 11 upstream framework-class findings (`UPSTREAM_FINDING_003`–`013`) | Pre-existing, unchanged this sprint. Await the nucleus PR from a separate clone (`agents.md §3 jurisdiction`) |
| Platform docs (`CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `NOTICE.md`) | Owned by `/agents:harden`, not a sprint |
| Hotfix candidate H-002 (search-selector reorder) | Pre-existing, measured, not patched. Its own `hotfix/` track per `RA-03` if prioritized |
| `composer_write_risk` hardening | Pre-existing hardening candidate, not an observed defect |

## Session note

This sprint's execution hit one session-wide API rate limit (Block E,
mid-dispatch) and one own-process gap (Phase 3 skipped `SPRINT_LOG.md`,
found and corrected before Phase 7). Both are recorded here rather than
smoothed over, per `agents.md §1 unambiguous_action` and this project's own
established practice of naming what happened rather than what was planned.
