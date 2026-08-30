# Phase Register — Sprint 004 (`backend-extractor` / P2)

| Phase | Status | Evidence |
| :--- | :--- | :--- |
| 0 Session start | DONE | Boot exit `2` traced to a framework defect, not drift; binding steps re-run from the host root; stale lock taken over after confirming a crashed 2026-08-27 session |
| 1 Planning | DONE | Chat negotiation 2026-08-29; `IMPLEMENTATION_PLAN.md` written directly at the canonical path (`RA-18`) |
| 2–4 Roadmap / assignments | DONE (sequential) | `task_scope.md`; `check_task_scope.py --current-sprint` passes |
| 5 Approval Gate | DONE | Human OK 2026-08-29; plan committed at `b0747b1` before the first work unit |
| 6 Execution | DONE | 27 atomic commits, `b0747b1`…`2ac7ec2`, on `ai-sprint/004` |
| 7 Double-Gate | DONE | QA APPROVED (charter); Tester APPROVED (charter) |
| 8 Close | DONE | Blueprint, walkthrough, roadmap, ledger, `memory_index.json` updated; `data/` purged |

---

## Phase 7 verdicts (`RA-17`)

| Gate | Verdict | Class | Evidence |
| :--- | :--- | :--- | :--- |
| QA (structural) | `APPROVED` | charter | `ruff check .` exit `0`; `py_compile` over `src/` + `tests/` exit `0`; `submodule_purity.py` clean; `check_task_scope.py --current-sprint` passes |
| Tester (logic) | `APPROVED` | charter | `pytest -q` — 62 passed, 0 failed |
| Live verification | `APPROVED` | testifying | 2026-08-30 against real WhatsApp Web: 513 messages in 12 passes; final run 254 messages, 135 `contact` / 119 `me`, **0 `unknown`**, 0 duplicates, 254/254 real timestamps, no name in payload or filename |

## What running it found that no offline gate could

The sprint's own tests were green while five defects were live. Each was
reproduced against the shipped implementation before being fixed.

| Defect | How it presented |
| :--- | :--- |
| Load-older control never clicked | Operator had to press it by hand once per batch; the matcher required a `<button>` and WA renders `div[role="button"]` |
| Harvester clicked links inside the chat | Candidate set included `#main a` / `#main [tabindex]`, and `haz clic aquí` matched ordinary message text |
| A stall recorded as a complete history | 217 messages of a longer conversation written as `complete: true` |
| `sender` held a clock, `timestamp` held message body | 214 of 217 messages; inherited from #003 and never tested |
| Every sender `unknown` | 513 of 513; `.message-in`/`.message-out` match zero rows, `data-id` is bare hex |

The lesson is recorded as `KI-004-A`: probe a third-party DOM before theorizing
about it. Three successive selector hypotheses were each wrong and each shipped.

## Residual risk carried into P3

| Unverified | Consequence if wrong |
| :--- | :--- |
| A run that reaches a chat start | Every live run was capped at 6–12 passes, so `stopped_reason: chat_start` and `complete: true` have **never been produced**. `CHAT_START_SELECTORS` remains unproven against a real beginning-of-conversation |
| Behaviour over thousands of passes | The longest run was 12 passes / 513 messages; the chat still had history above it |
| Session drop mid-harvest | No retry. Partial output is honest (`complete: false`) but the run is lost |

An uncapped `wa-extract export-one --query "…"` is what closes the first row.

## Framework findings routed upstream (`§4 feedback_upstream`)

| # | Defect |
| :--- | :--- |
| `UPSTREAM_FINDING_004` | `session_start.py --boot` claims the session lock on the nucleus anchor in submodule mode |
| `UPSTREAM_FINDING_005` | The commit gate reads any added `key = value` in `pyproject.toml` as a new dependency |

Neither was patched in place: `agents.md §3 strict_rule`. `git -C .agents status --porcelain` is empty.
