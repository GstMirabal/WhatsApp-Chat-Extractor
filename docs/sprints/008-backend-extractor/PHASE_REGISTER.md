# Phase Register — Sprint 008 (`backend-extractor`)

Which pipeline phase ran, what it left behind, and what proves it. A phase that
left no artifact did not run (`close_workflow.md` Phase 2.6).

| Phase | Ran | Artifact | Evidence |
| :--- | :--- | :--- | :--- |
| 0. Session start | Partly | none (precondition) | `session_start.py --boot` **refused**, exit `2`, on the stale nucleus lock `20260827T154222Z-45916` (`UPSTREAM_FINDING_004`/`_008`). The five binding steps were run individually from the host root: drift `0`, claim `0` (resumed, session #14), probe advisory, sync `0` (pin v4.24.0), bridge fresh |
| 1. Planning | Yes | `IMPLEMENTATION_PLAN.md` | Committed `50b8f83` **before** Phase 5. `audit_plan.py` → `[OK]`, exit `0` |
| 2. Environment | Yes | none (precondition) | `ruff` clean and **194 passed / 1 skipped** at sprint open. No `.env` read (`RA-09`) |
| 3. Roadmap | Yes | `SPRINT_LOG.md` | Branch `ai-sprint/008` created from `main` at `ac6ddd9` before the first commit (`RA-12`) |
| 4.1 Agent assignment | Yes | `agent_assignment.md` | `check_forge_ladder.py` exit `0`. One Phase-1 proposal overwritten: D1 moved off `devops_agent`, which holds no `Write`/`Edit` — `check_task_scope.py` rejected the proposal with exit `2` on that capability test |
| 4.2 Skill assignment | Yes | `skill_assignment.md` | `check_forge_ladder.py` exit `0`. No skill forged; ladder terminated at P1 and said so |
| 4.3 Rule audit | Yes | `task_scope.md` | `check_task_scope.py` exit `0`. Model/Effort from `config/model_tiers.json` `claude_code`; one escalation (B2 → `opus`/`high`) with its reason recorded |
| 5. Approval Gate | Yes | none (human) | **Full approval, human, attended, 2026-09-01**, against the plan committed at `50b8f83`. Not wrapped in any `/loop` |
| 6. Execution | Yes | 13 commits on `ai-sprint/008` | Every message carries `#008`. Three documented deviations from one-file-per-commit, each with its reason in `task_scope.md` |
| 7. Quality Gate | Yes | three rows in `SPRINT_LOG.md` | QA `RECORD`/`testifying`, Tester `RECORD`/`testifying`, plus an Orchestrator response row. `check_gate_log.py` exit `0`; `check_role_artifact.py` exit `0` for both roles. **Both gates initially returned evidence-free verdicts** — cause diagnosed, fixed and routed upstream, see below |
| 8. Closeout | Yes | this file | Blueprint, System Overview, Walkthrough, Master Ledger and the state anchor all updated |

## Units delivered

19 planned, 1 added during execution and recorded rather than absorbed
(`task_scope.md` §Added during execution): D6.

| Block | Units | Outcome |
| :--- | :--- | :--- |
| A — preflight | A1–A3 | Gate-evidence diagnosis; two stale records corrected |
| B — the defect | B1–B8 | `ADR-0005`; `sweep_until_stable`; manifest schema v2 |
| C — measure later | C1–C3 | `probe_unknown_rows.py` built and tested; **live run not taken** |
| D — platform and upstream | D1–D6 | Platform re-probed; five upstream drafts written |

## What this sprint proved, and what it did not

**Proved.** `sweep_until_stable` recovers **899 of 899** conversations at one
reorder per 5 reads and at one per 2, where the single-pass sweep found 882 and
856. Confirmed twice over: by the committed fixture, and by `RandomReorderPane`,
which perturbs irregularly rather than rotating — added at the gate precisely
because the first fixture was favourable to the fix.

**Not proved, and not claimed.** That the enumeration is complete. Convergence
is statistical evidence; a conversation can evade any finite number of sweeps.
`ADR-0005` names this by refusing to define a `proven` value.

**Not measured.** The `sender`/`kind` unknown rates. The instrument exists and
is tested; the live run needs an authenticated session and is operator-gated.
`PROBE_UNKNOWN_ROWS_RUN.md` says `NOT RUN` rather than implying otherwise.

## The Phase 7 incident

Both gates first returned a verdict and no evidence — the same failure Sprint
007 recorded twice and misattributed. Cause: the `SubagentStop` hook runs
`check_role_artifact.py --from-hook`, which exits `2` unless `SPRINT_LOG.md`
already holds that gate's row — a row the gate profiles hold no `Write` tool to
produce. Exit `2` forces a continuation and the continuation overwrites the
report.

Unit A1 had concluded the opposite, confidently, and was wrong: it ran before
A2 repointed the anchor at Sprint 008, and Sprint 007's log already had rows, so
the hook stayed quiet. `GATE_CHANNEL_DIAGNOSIS.md §7` supersedes §4 and keeps
both, so the wrong conclusion and its refutation stay legible.

Transcribing the rows first unblocked it. Both agents then delivered in full,
and Gate 2's 18-mutant analysis found five survivors, three of which were this
sprint's own work and were closed in `343ab84`.

## Carried to Sprint 009

| Item | Why not here |
| :--- | :--- |
| Live probe run and the `sender`/`kind` classification | Operator-gated; `KI-004-A` forbids classifying without the data |
| `F-4` — `cmd_export_all` exit condition untested | Needs a Playwright harness that does not exist; untested at `ac6ddd9` too |
| `F-6` — `enumeration` is an unvalidated `str` | The classifier is its only producer; a validator is a design choice, not a fix |
| Five pre-existing complexity violations | Outside the approved scope, in files this sprint does not own |
| Nucleus PR for eleven upstream drafts | `§3 jurisdiction`: a separate act in a separate clone |
| Repository visibility, which would unblock `ci_gate.py` | The owner's decision, not a sprint's |
