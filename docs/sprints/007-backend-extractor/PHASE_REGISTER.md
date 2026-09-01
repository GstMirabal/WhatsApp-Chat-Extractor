# Phase Register — Sprint 007 (`backend-extractor`, P3b)

Which pipeline phase ran, what it left behind, and what proves it. A phase that
left no artifact did not run (`close_workflow.md` Phase 2.6).

| Phase | Ran | Artifact | Evidence |
| :--- | :--- | :--- | :--- |
| 1. Planning | Yes | `IMPLEMENTATION_PLAN.md` | Committed `dd815a6` **before** Phase 5. `audit_plan.py` → `[OK]`, exit `0` — the first time this host reproduced that gate; Sprint 006 could not and said so |
| 2. Environment | Yes | none (precondition) | `.venv` Python 3.13.13; `ruff` clean and **116 passed / 1 skipped** at sprint open. No `.env` read (`RA-09`) |
| 3. Roadmap | Yes | `SPRINT_LOG.md` | Branch `ai-sprint/007` created from `main` at `c3e827a` before the first commit (`RA-12`) |
| 4.1 Agent assignment | Yes | `agent_assignment.md` | `check_forge_ladder.py` exit `0`. Two Phase-1 proposals overwritten (`principal_agent` holds no `Write`) |
| 4.2 Skill assignment | Yes | `skill_assignment.md` | `check_forge_ladder.py` exit `0`. No skill forged; P1→P3 ladder walked and recorded |
| 4.3 Rule audit | Yes | `task_scope.md` | `check_task_scope.py` exit `0`. Model/Effort from `config/model_tiers.json` `claude_code` |
| 5. Approval Gate | Yes | none (human) | **Full approval, human, 2026-08-31**: all four blocks, `ADR-0004` confirmed as Option C |
| 6. Execution | Yes | 31 commits on `ai-sprint/007` | One physical file per commit (`jurisdictional_lock`); every message carries `#007` |
| 7. Quality Gate | Yes | two rows in `SPRINT_LOG.md` | QA `RECORD`/`testifying`, Tester `RECORD`/`testifying`, both dispatched as fresh-context subagents at the gate tier. `check_gate_log.py` and `check_role_artifact.py` exit `0` for both roles |
| 8. Closeout | Yes | this file | Blueprint, README, System Overview, Walkthrough, Master Ledger and Global Roadmap all updated |

## Units delivered

15 planned, 6 added during execution and recorded rather than absorbed
(`task_scope.md` §Units added during execution): W3a, W5b, W5c, W11a, W11b, W15b.

| Block | Units | Outcome |
| :--- | :--- | :--- |
| A — decide and pin | W1–W4, W3a, W11a | `ADR-0004`; schema v5; `complete` derived |
| B — measure | W5, W5b, W6 | Chat list virtualizes; position stable across a sweep |
| C — enumerate | W7–W11, W5c, W11b | `chat_list.py`, `manifest.py`, `export-all` |
| D — document | W12–W15, W15b | Blueprint, README, Overview, Ledger, Roadmap |

## What this sprint measured

| Question | Answer | How |
| :--- | :--- | :--- |
| Does the chat list virtualize? | **Yes** | 899 conversations while ≤70 rendered; reproduced twice, both reaching the pane foot |
| Is a chat's position stable? | **Yes, across a sweep** | 0 of 69 positions changed, both readings anchored at the pane head |
| Do two chats share a title? | **No** | 0 collisions in 7 100 row observations |
| Is `chat_id` permanent across runs? | **No** | Two sweeps counting 899 shared 898 |
| Does `export-all` work live? | **Yes** | 3 exported, 0 failed, 907 skipped of 910 |
| How long is a whole-account run? | **~15 hours** | ~3 min enumeration + ~60 s per conversation |

## What it got wrong, and how that was found

Recorded because the pattern is the lesson: **every one of these was found by the
next measurement, never by review** (`KI-007-F`).

| Defect | Found by |
| :--- | :--- |
| Probe declared `not-virtualized` from 3.3% of the pane — the same error `W4a` fixed one panel over, two days earlier | Reading the geometry in the run it produced |
| Two consecutive stability verdicts were artifacts: readings taken at different scroll positions of a virtualized list | The next run, whose verdict inverted |
| Three functions pushed over the 50-line cap, one of them lengthened by this sprint | Running the cap over the whole tree instead of the edited files |
| Four of five new test files "fail against the old tree" only by module absence, not by demonstrating a defect | Running them in a worktree at the base commit |
| **The enumerator undercounts silently when the list reorders mid-sweep** | Probing the test double's fidelity after the gates had passed |

## Outstanding at close

| Item | Destination |
| :--- | :--- |
| Enumerator undercount under reordering (open defect, pinned by test) | Sprint 008, first unit |
| `sender: unknown` at 3.9% — recorded, not diagnosed | Sprint 008 probe |
| `unknown_media` classification, carried since #006 | Sprint 008 |
| ~15-hour whole-account run | P4 |
| `UPSTREAM_FINDING_008`, `_010`, `_011`, `_012` | Nucleus PR from a separate clone — not host work |
| Neither gate delivered its evidence through the result channel | Reported; the verdicts stand, the evidence in the rows is the orchestrator's |

---
*Sealed at Sprint Closeout #007 (`RA-05`).*
