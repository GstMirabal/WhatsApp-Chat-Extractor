# Agent Assignment — Sprint 012 (backend-extractor)

Source: `docs/sprints/012-backend-extractor/IMPLEMENTATION_PLAN.md` (`## Work`).
Phase 4.1 of `workflows/pipeline_workflow.md`. This file is the staffing
authority: it may overwrite the plan's `Assignee (proposed)` column. A Work row
is not closed until it appears here.

Mode: **claude-code**, `delegation_mode: native` — the `Assignee` column names
which profile's ruleset governs each write.

## Scope of this artifact (Phase 4.1 only)

| Owns | Does **not** own |
| :--- | :--- |
| Which ruleset governs each unit | Cursor model / effort (`task_scope.md`) |
| Agent-forge destination on units that create agents | `tier_escalation` proposals |

No unit in this sprint creates a new agent profile; `Destination` is `N/A`
throughout.

---

## Staffing

| # | Target | Operation | Mode | Assignee | Destination | Ruleset file |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `src/whatsapp_chat_extractor/export_one.py` | modify | native | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| 2 | `tests/test_open_first_result.py` | create | native | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| 3 | `tests/test_export_all.py` | modify | native | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| 4 | `README.md` | modify | native | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| 5 | `docs/0_SYSTEM_OVERVIEW.md` | modify | native | `doc_orchestrator` | N/A | `agents/doc_orchestrator.md` |
| 6 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | native | `doc_orchestrator` | N/A | `agents/doc_orchestrator.md` |
| 7 | `pyproject.toml` | modify | native | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| 8 | `identity.config.json` | modify | native | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| 9 | `docs/active_state.json` | modify | native | `topology_mapper` | N/A | `agents/topology_mapper.md` |
| 10 | `CONTRIBUTING.md` | create | native | `doc_orchestrator` | N/A | `agents/doc_orchestrator.md` |
| 11 | `SECURITY.md` | create | native | `doc_orchestrator` | N/A | `agents/doc_orchestrator.md` |
| 12 | `CODE_OF_CONDUCT.md` | create | native | `doc_orchestrator` | N/A | `agents/doc_orchestrator.md` |
| 13 | `NOTICE.md` | create | native | `doc_orchestrator` | N/A | `agents/doc_orchestrator.md` |
| 14 | `docs/RUNBOOK.md` | create | native | `doc_orchestrator` | N/A | `agents/doc_orchestrator.md` |

## Disagreements with the plan

| # | Plan proposed | This file assigns | Reason |
| :--- | :--- | :--- | :--- |
| 9 | `principal_agent` | `topology_mapper` | `principal_agent`'s toolset is `Read, Glob, Grep, TodoWrite` — no `Write`/`Edit`, so it cannot perform a `modify` on `docs/active_state.json` (`check_task_scope.py`'s capability check). `topology_mapper` holds `Write`/`Edit` and is the role scoped to maintaining this anchor's content. |

Every other `Assignee (proposed)` in `IMPLEMENTATION_PLAN.md` § Work stands
unchanged.
