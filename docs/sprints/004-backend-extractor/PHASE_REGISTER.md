# Phase Register — Sprint 004 (`backend-extractor` / P2)

| Phase | Status | Evidence |
| :--- | :--- | :--- |
| 0 Session start | DONE | Boot exit `2` traced to a framework defect, not drift; binding steps re-run from the host root; stale lock taken over after confirming a crashed 2026-08-27 session |
| 1 Planning | DONE | Chat negotiation 2026-08-29; `IMPLEMENTATION_PLAN.md` written directly at the canonical path (`RA-18`) |
| 2–4 Roadmap / assignments | DONE (sequential) | `task_scope.md`; `check_task_scope.py --current-sprint` passes |
| 5 Approval Gate | DONE | Human OK 2026-08-29; plan committed at `b0747b1` before the first work unit |
| 6 Execution | DONE (code + docs) | 12 atomic commits, `b0747b1`…`9f1667b`; **live WhatsApp Web run pending operator** |
| 7 Double-Gate | DONE (offline scope) | QA APPROVED (charter); Tester APPROVED (charter) — see below |
| 8 Close | PENDING | Blocked on live verification; see Residual risk |

---

## Phase 7 verdicts (`RA-17`)

| Gate | Verdict | Class | Evidence |
| :--- | :--- | :--- | :--- |
| QA (structural) | `APPROVED` | charter | `ruff check .` exit `0`; `python3 -m py_compile` over `src/` + `tests/` exit `0`; `submodule_purity.py` clean; `check_task_scope.py --current-sprint` passes |
| Tester (logic) | `APPROVED` | charter | `pytest -q` — 22 passed, 0 failed. 13 new cases in `tests/test_history.py`, 3 updated + 3 new in `tests/test_writers.py` |

QA raised one finding during the pass, remediated before the verdict: `task_scope.md`
assigned `create` units to `principal_agent` and `devops_agent`, neither of which
declares `Write`/`Edit`. Reassigned to `doc_orchestrator` and `implementer_agent`.

## Residual risk — why Phase 8 is not closed

The offline gates are green, and they do not prove the sprint's own exit
criterion. Every check above runs against synthetic pass sequences; none opens a
browser.

| Unverified | Consequence if wrong |
| :--- | :--- |
| `data-id` present on message rows | Falls back to the content hash; the abort criterion applies if that collides |
| `CHAT_START_SELECTORS` match a real start marker | `stopped_reason` reports `stalled` instead of `chat_start`; `complete` is unaffected |
| A stalled run really means the top of history | A conversation could be reported complete while older messages remain |
| `message_count` exceeds the 84 of the P1 spike | The sprint's stated exit criterion is unmet |

The operator runs, on the Mac that holds the WhatsApp session:

```bash
.venv/bin/wa-extract export-one --query "PARTIAL_CHAT_NAME"
```

and reads exit code, `message_count`, `complete` and `stopped_reason`.
