# Agent Assignment — Sprint 006 (`backend-extractor`, P3a)

Phase 4.1 of `workflows/pipeline_workflow.md`. Source: `IMPLEMENTATION_PLAN.md`
`## Work`.

**Mode.** `session_tool: cursor`, `delegation_mode: sequential`. Cursor cannot
spawn the eight pipeline roles, so `Assignee` names **which profile's ruleset
governs each write**, not a dispatched subagent. Mechanical and gate units are
dispatched via Cursor `Task` with the Model column (`ADR-0010`); the parent stays
sequential.

**Destination.** No unit creates a new agent profile, so every row is `n/a`. The
column is kept because `check_forge_ladder.py` reads it and because an absent
column is indistinguishable from an unanswered question.

| # | File | Assignee | Destination | Why this profile |
| :--- | :--- | :--- | :--- | :--- |
| W1 | `scripts/probe_chat_start.py` | `implementer_agent` | n/a | Framework-root `scripts/` authorship is this profile's tree (`ADR-0009`); `devops_agent` holds no `Write` there |
| W2 | `docs/sprints/006-backend-extractor/DOM_PROBE_NOTES.md` | `doc_orchestrator` | n/a | Measured evidence written as tables, English, no interpretation beyond what the probe returned |
| W3 | `docs/decisions/ADR-0004-completeness-criterion.md` | `doc_orchestrator` | n/a | The decision is the lead agent's, but `principal_agent` holds no `Write`/`Edit` by design (`§6`) and `check_task_scope` rejects assigning it a `create`. The documentalist transcribes it, the same emit-versus-write split the Phase 7 gates use |
| W4 | `src/whatsapp_chat_extractor/history.py` | `implementer_agent` | n/a | Product source authorship |
| W5 | `tests/test_completeness.py` | `implementer_agent` | n/a | `tester_agent` verifies and never authors test files (`F-026-A1`) |
| W6 | `src/whatsapp_chat_extractor/writers.py` | `implementer_agent` | n/a | Product source authorship |
| W7 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | `doc_orchestrator` | n/a | Blueprint is the architecture record (`RA-05`) |
| W8 | `README.md` | `doc_orchestrator` | n/a | Operator-facing surface; `readme-standardizer` governs its shape |

**Gates.** Phase 7 runs `qa_agent` then `tester_agent` in fresh-context `Task`
with `modelId=claude-opus-5`, `effort=max` (measured this session via
`audit_cursor_models.py --resolve gate`). Fresh context is non-negotiable under
both tools; sequential mode is not an exemption.
