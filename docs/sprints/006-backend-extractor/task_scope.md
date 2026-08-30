# Task Scope — Sprint 006 (`backend-extractor`, P3a)

Phase 4.3 of `workflows/pipeline_workflow.md`. Source: `IMPLEMENTATION_PLAN.md`
`## Work`.

**Mode.** `session_tool: cursor`, `delegation_mode: sequential`. Cursor cannot
spawn the eight pipeline roles, so `Assignee` names **which profile's ruleset
governs each write**, not a dispatched subagent.

**Isolation.** `jurisdictional_lock` and `no_interference` are applied by
*reading* this file during execution. It is written **before** Phase 6, unlike
Sprint 005 where it was written during the close (`KI-005-C`) and both rules were
therefore not in force.

## Measured model tiers

Run in this session, immediately before writing the `Model` / `Effort` columns.
`make -f .agents/Makefile cursor-tiers` **fails in this host** — the Makefile
target does not quote the repository path and this one contains spaces, so `cd`
splits the argument. Invoked directly instead, from `.agents/`:

```
$ python3 scripts/audit_cursor_models.py --resolve mechanical
modelId=composer-2.5
effort=

$ python3 scripts/audit_cursor_models.py --resolve gate
modelId=claude-opus-5
effort=max
```

Values are transcribed from that measured block. No `claude_code` alias was
copied from `config/model_tiers.json` (`F-20260825-027`).

## Scope

| # | File | Operation | Risk | Assignee | Model | Effort | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| W1 | `scripts/probe_chat_start.py` | create | medium | `implementer_agent` | `claude-opus-5` | `high` | ✅ |
| W1b | `tests/test_probe_chat_start.py` | create | medium | `implementer_agent` | `claude-opus-5` | `high` | ✅ |
| W2 | `docs/sprints/006-backend-extractor/DOM_PROBE_NOTES.md` | create | low | `doc_orchestrator` | `composer-2.5` | — | 🟡 |
| W3 | `docs/decisions/ADR-0004-completeness-criterion.md` | create | high | `doc_orchestrator` | `claude-opus-5` | `max` | 🔒 |
| W4a | `src/whatsapp_chat_extractor/history.py` | modify | high | `implementer_agent` | `claude-opus-5` | `max` | ✅ |
| W4 | `src/whatsapp_chat_extractor/history.py` | modify | high | `implementer_agent` | `claude-opus-5` | `max` | 🔒 |
| W5 | `tests/test_completeness.py` | create | medium | `implementer_agent` | `claude-opus-5` | `high` | 🔒 |
| W6 | `src/whatsapp_chat_extractor/writers.py` | modify | medium | `implementer_agent` | `claude-opus-5` | `high` | 🔒 |
| W7 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | `composer-2.5` | — | 🔒 |
| W8 | `README.md` | modify | low | `doc_orchestrator` | `composer-2.5` | — | 🔒 |

**W4a is a partial unlock of W4, authorized by the human on 2026-08-31.** It
covers *only* the stall rule (`decide_stop` gains `panel_loading`, plus
`panel_is_loading`) and its tests. `COMPLETE_REASONS` — the completeness
criterion itself — is untouched and stays locked behind `ADR-0004` (W3). The
reason for the unlock is ordering, not convenience: run 3 declared a top on a
panel that was still fetching, so an ADR written on that evidence would be
deciding "what to report when the marker is absent" without having established
that it is absent. Same argument as the plan's D1, one level down. W4's
remaining scope stays 🔒.

**W1b was added during execution, not planned.** The Phase 4.3 table shipped W1
with no test row, and `hooks/on_commit.py` refused the probe's `fix(` commit for
exactly that reason (`rules/code_craft.md §6`: a fix stages the test that proves
the bug). The hook was right and the plan was short a row. W1b is W1's test, not
new scope: it is the same unit of work, and it is deliberately **not**
`tests/test_completeness.py`, which is W5 and stays gate-locked.

**Status legend.** ✅ done · 🟡 written, awaiting the operator's probe run ·
🔒 **not authorized**: the Approval Gate of 2026-08-30 covered W1–W2 only, so
W3–W8 stay closed until the probe's verdict reopens the gate. A row marked 🔒 is
out of scope for this session, and `no_interference` refuses any write to it.

## Escalation notes

Required wherever a row's risk exceeds the mechanical tier's reach.

| # | Escalated from | Why the mechanical tier is not enough |
| :--- | :--- | :--- |
| W1 | `composer-2.5` | The probe runs against a live third-party DOM in the operator's real session. `KI-004-D` records a harvester that clicked links inside message bubbles; a probe with a careless selector does damage that no test catches |
| W3 | `composer-2.5` | The ADR chooses between two completeness models and must record why the rejected one was rejected. That is judgment, and `history.py:39` shows the cost of getting it wrong: 217 messages labelled complete |
| W4 | `composer-2.5` | `COMPLETE_REASONS` is the single point where an inference could be recorded as proof. The whole sprint exists because this classification is wrong today |
| W5 | `composer-2.5` | The tests must fail against the current tree to be worth anything (`KI-H001-B`); writing a test that passes either way is the failure mode here |
| W6 | `composer-2.5` | Schema change: a field that reaches the written corpus and cannot be corrected retroactively without re-running the export |

Rows W2, W7 and W8 stay mechanical: they transcribe measured evidence and
decisions already taken elsewhere, and none of them can put a wrong value into an
exported corpus.

## Conflicts

No file appears twice. No unit shares a physical file with another, so
`jurisdictional_lock` (one structural file per task) holds for every row and
`no_interference` has nothing to refuse.
