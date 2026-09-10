# Phase Register — Sprint 009 (`backend-extractor`)

Which pipeline phase ran, what it left behind, and what proves it. A phase that
left no artifact did not run (`close_workflow.md` Phase 2.6).

| Phase | Ran | Artifact | Evidence |
| :--- | :--- | :--- | :--- |
| 0. Session start | Partly | none (precondition) | `session_start.py --boot` **refused**, exit `2`, on the stale nucleus lock `20260827T154222Z-45916` (`UPSTREAM_FINDING_004`, fifth instance). Binding steps run individually from the host root: drift `2` (a false positive — 19 commits, all `#009`, all recorded; `KI-009-E`), claim `0` (resumed, sessions #15 and #16), probe advisory, sync `0` (pin v4.24.0), bridge fresh both targets |
| 1. Planning | Yes | `IMPLEMENTATION_PLAN.md` | Committed `a4a22df` **before** Phase 5. `audit_plan.py` → `[OK]`, exit `0`. Scope renegotiated once between Phase 1 and Phase 3 (resume-only → resume + corpus v6), deliberately and recorded |
| 2. Environment | Yes | none (precondition) | `ruff` clean and **224 passed / 1 skipped** at the branch point `d0cdbb4`. No `.env` read (`RA-09`) |
| 3. Roadmap | Yes | `SPRINT_LOG.md` | Branch `ai-sprint/009` from `main` at `d0cdbb4` (`v0.8.1`) before the first commit (`RA-12`) |
| 4.1 Agent assignment | Yes | `agent_assignment.md` | Every unit assigned. `implementer_agent` for code and tests, `doc_orchestrator` for the four documents |
| 4.2 Skill assignment | Yes | `skill_assignment.md` | Tools resolved per unit; no skill forged, ladder terminated and said so |
| 4.3 Rule audit | Yes | `task_scope.md` | `check_task_scope.py` exit `0`. Model/Effort from `config/model_tiers.json` `claude_code`; two escalations (`C1`, `E5` → `opus`/`high`), each with its reason. One unit (`E8`) added during Phase 6 and recorded rather than absorbed |
| 5. Approval Gate | Yes | none (human) | **Full approval, human, attended**, recorded at commit `2191122`, against the plan committed at `a4a22df`. Not wrapped in any `/loop` |
| 6. Execution | Yes | 40 commits on `ai-sprint/009` (`d0cdbb4..HEAD`) | 37 carry `#009`, 3 carry `#H003` (the hotfix, merged back at `d157676`). 19 of 19 planned units landed |
| 7. Quality Gate | Yes | two rows in `SPRINT_LOG.md` | QA `APPROVED` / `charter` (round 3, after two `REJECTED` / `charter`); Tester `RECORD` / `testifying`. `RECORD` does not count toward escalation (`RA-17`). Gate ran on `sonnet` after an `opus` attempt was killed by an API session limit — recorded in the log |
| 8. Closeout | Yes | this file | Blueprint, Walkthrough, Global Roadmap, Master Ledger and the state anchor updated; graph rebuilt |

## Units delivered

19 planned, all landed. One (`E8`, `tests/test_completeness.py`) added during
execution when `E5`'s schema bump broke an assertion Phase 1 had not enumerated.

| Block | Units | Outcome |
| :--- | :--- | :--- |
| A — run journal | A1–A2 | Append-only NDJSON journal, `fsync` per record, `read_journal` tolerating one damaged trailing line |
| E — corpus v6 | E1–E8 | `message_id`, `timestamp_iso`, `passes_used`, `source_locale`, `source_timezone`, `undated_messages`; pinned locale, resolved-not-imposed timezone; `ADR-0007` |
| B — manifest from journal | B1–B2 | `manifest_from_journal` reconstructs a manifest from a journal; `run_id` threads through both writers |
| C — resume and recover | C1–C3 | `--resume`, `--timezone`, the browserless `recover` subcommand, `_latest_per_chat` dedup of a retried conversation; `ADR-0006` |
| D — documentation | D1–D4 | `ADR-0006`, `ADR-0007`, Blueprint, System Overview |

## The Phase 7 structural gate — three rounds

All three `REJECTED` verdicts were the same rule, `max_lines_per_func` (50),
which `ruff` cannot catch because no function-length rule is armed in this
project — the reason the check sits on the gate.

| Round | Finding | Remediation |
| :--- | :--- | :--- |
| 1 | `manifest.py::manifest_from_journal`, 54 lines. **Scan covered three files and returned a verdict as if it had covered the sprint** | `1f82981` — extracted `_with_reconstructed_skips`; 44 lines |
| — | `writers.py::build_export`, 40 → 59 lines under `E5`. Found by the Orchestrator widening round 1's scan, not by a gate | `ab8454a` — extracted `_derive_computed_fields` and `_assemble_export_payload`; 47 lines |
| 2 | `tests/test_resume.py` resume case, 51 lines. Scan widened to all modules and all touched tests | `68c550d` — extracted a `browserless_run` fixture; 25 lines |
| 3 | none — 470 functions across 25 files, both axes | `APPROVED` |

No remediation weakened anything to satisfy a line count. A first attempt at the
`_observe_and_decide` extraction (H-003) bought its lines by deleting three
comments, including one explaining the interaction the hotfix turns on; rejected
on review and the prose restored verbatim.

## The Phase 7 functional gate — two coverage gaps

Tester `RECORD`. The gate verified rather than read: it shadowed `playwright`
with a module that raises on import (after confirming the real package is
installed) to prove `recover` is browserless, exercised `_run_exit_code` with
four constructed manifests, and walked the 11 removed test lines hunk by hunk.

| Gap | Disposition |
| :--- | :--- |
| `T-1` — `_latest_per_chat` had no test; a mutation to the identity function makes a run that succeeded report as failed with exit `3` | **Closed at `998603c`** by human decision — the sprint's headline capability was untested and a whole-account run was about to start on it. New case drives the real `cmd_export_all`, proven by mutation twice independently |
| `T-2` — `_request_timezone` / `_confirm_timezone` have no tests | Carried to Sprint 010: those two functions are likely rewritten when `launch_context` gains `timezone_id` (`§D7`), so tests now would carry a known expiry |

## Two parts of the approved plan that did not ship

Both found by unit `D1` while writing the ADR meant to record them. Neither is a
defect in what landed; both are gaps between the plan approved at Phase 5 and
the work the units were given. Carried to Sprint 010 by human decision, plan
text left unamended so the evidence stays legible.

| Plan | What did not happen |
| :--- | :--- |
| `§D5` | A second append-only journal, `data/chat_index_<run_id>.ndjson`, for titles. No work unit was ever assigned it; `A1`'s row names four journal functions and no title journal. `write_chat_index` still writes one batched JSON at run end |
| `§D6` | The large files were to "only call" the new modules. `journal.py` and `timestamps.py` exist and `export_one.py` was left alone, but `__main__.py` grew from 421 to 793 lines: the run orchestration landed in it rather than a module of its own |

## Unplanned — hotfix H-003

A whole-account run stalled on one conversation for 4 h 24 m without collecting a
message. `decide_stop` suppressed the stall verdict for as long as the panel
showed a loading spinner, and WhatsApp Web leaves that spinner up indefinitely
when the paired phone never answers a load-earlier request — so the only exit
left was `max_passes`, 8.3 hours per affected conversation.

Fixed on `hotfix/H-003` (branched from `ai-sprint/009`, since `main` carries no
`--resume`): `DEFAULT_LOADING_GRACE = 20` bounds the suppression, and
`STOP_LOADING_UNRESOLVED` ends the harvest honestly — about 6 minutes.
`classify_completeness` unchanged; it fails closed to `truncated`. Five pinning
tests, proven by mutation. Merged back at `d157676`. Suite 278/1 → 283/1.

Found in production on 2026-09-08, not in review — the suite runs without a
browser and no test can hang on a live page. Second defect of this family in six
days (`KI-009-H` was the first). Systemic candidate recorded: every loop that
waits on an external system must state its bound in wall-clock time, not only in
iterations.

## Carried to Sprint 010

| Item | Why not here |
| :--- | :--- |
| `§D5` — the title-index journal | No unit was assigned it; decide whether it becomes the NDJSON journal the note specifies or the plan text is amended to the batched writer |
| `§D6` — `__main__.py` at 793 lines | Decide whether the run orchestration leaves it for a module of its own |
| `T-2` — the two timezone functions untested | Likely rewritten in Sprint 010 when `launch_context` gains `timezone_id` |
| `KI-009-H` — the harvest loop has no wall-clock timeout | A per-conversation deadline outside the page API; `set_default_timeout` does not govern the `ElementHandle` calls the loop uses |
| The systemic wall-clock-bound amendment (H-003 §5) | A rule amendment via `constitutional_escalation`, indexed at `extract` |
