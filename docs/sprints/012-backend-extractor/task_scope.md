# Task Scope — Sprint 012 (backend-extractor)

Source: `docs/sprints/012-backend-extractor/IMPLEMENTATION_PLAN.md` § Work,
`agent_assignment.md` (Assignee is the Phase 4.1 authority, not the plan's
proposal). Phase 4.3 of `workflows/pipeline_workflow.md`, drafted by
`rule_validator`. `Model`/`Effort` required from Sprint 28 onward
(`scripts/check_task_scope.py:38`); resolved against
`.agents/config/model_tiers.json` `claude_code` cells, never a Cursor alias
(this session: `session_tool: claude-code`).

`jurisdictional_lock` and `no_interference` (`agents.md §2`) both read this
file: one physical file per row, and a row in progress here blocks a second
subtask from claiming the same file.

---

| # | File | Operation | Risk | Assignee | Model | Effort | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `src/whatsapp_chat_extractor/export_one.py` | modify | medium | `implementer_agent` | sonnet | medium | ✅ `c6b29d0` |
| 2 | `tests/test_open_first_result.py` | create | low | `implementer_agent` | sonnet | medium | ✅ `c6b29d0` |
| 3 | `tests/test_export_all.py` | modify | low | `implementer_agent` | sonnet | medium | ✅ `3dc92e5` |
| 4 | `README.md` | modify | low | `implementer_agent` | sonnet | medium | ✅ `7e48a3e` |
| 5 | `docs/0_SYSTEM_OVERVIEW.md` | modify | low | `doc_orchestrator` | sonnet | medium | ✅ `016db68` |
| 6 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | sonnet | medium | ✅ `5b6e2ec` |
| 7 | `pyproject.toml` | modify | low | `implementer_agent` | sonnet | medium | ✅ `b21f1d3` |
| 8 | `identity.config.json` | modify | low | `implementer_agent` | sonnet | medium | ✅ `f5d0938` |
| 9 | `docs/active_state.json` | modify | low | `topology_mapper` | haiku | low | ✅ (untracked, `.gitignore:37` — no commit) |
| 10 | `CONTRIBUTING.md` | create | low | `doc_orchestrator` | sonnet | medium | ✅ `872b586` |
| 11 | `SECURITY.md` | create | low | `doc_orchestrator` | sonnet | medium | ✅ `3150c5f` |
| 12 | `CODE_OF_CONDUCT.md` | create | low | `doc_orchestrator` | sonnet | medium | ✅ `857cf5c` |
| 13 | `NOTICE.md` | create | low | `doc_orchestrator` | sonnet | medium | ✅ `b039cc5` |
| 14 | `docs/RUNBOOK.md` | create | low | `doc_orchestrator` | sonnet | medium | ✅ `d5f9b74` |

Model/Effort source: `.agents/config/model_tiers.json` `tiers.author.claude_code`
(sonnet/medium — `implementer_agent`, `doc_orchestrator`) and
`tiers.mechanical.claude_code` (haiku/low — `topology_mapper`). No row uses
the `gate` tier: Phase 7's `qa_agent`/`tester_agent` are not Work rows.

No row is `in progress` by another subtask; no row overlaps a file locked
elsewhere in this sprint. `jurisdictional_lock`/`no_interference`: satisfied.
