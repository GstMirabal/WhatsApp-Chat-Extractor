# Agent Assignment — Sprint 007 (`backend-extractor`, P3b)

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

**Two proposals from Phase 1 are overwritten here**, which is this phase's
authority (`pipeline_workflow.md` Phase 4.1). The plan proposed `principal_agent`
for W1 and W15. That profile holds no `Write`/`Edit` by design (`agents.md §6`),
and `check_task_scope.py` rejects assigning it a `create` — the same emit-versus-write
split the Phase 7 gates use. `doc_orchestrator` transcribes both; the decision in
W1 remains the lead agent's.

| # | File | Assignee | Destination | Why this profile |
| :--- | :--- | :--- | :--- | :--- |
| W1 | `docs/decisions/ADR-0004-completeness-criterion.md` | `doc_orchestrator` | n/a | ADR authorship is the documentalist's tree; `principal_agent` decides and does not write (`§6`) |
| W2 | `src/whatsapp_chat_extractor/history.py` | `implementer_agent` | n/a | Product source authorship |
| W3 | `src/whatsapp_chat_extractor/writers.py` | `implementer_agent` | n/a | Product source authorship |
| W4 | `tests/test_completeness.py` | `implementer_agent` | n/a | `tester_agent` verifies and never authors test files (`F-026-A1`) |
| W5 | `scripts/probe_chat_list.py` | `implementer_agent` | n/a | Framework-root `scripts/` authorship is this profile's tree (`ADR-0009`); `devops_agent` holds no `Write` there |
| W6 | `docs/sprints/007-backend-extractor/CHAT_LIST_PROBE_NOTES.md` | `doc_orchestrator` | n/a | Measured evidence written as tables, English, no interpretation beyond what the probe returned |
| W7 | `src/whatsapp_chat_extractor/chat_list.py` | `implementer_agent` | n/a | Product source authorship |
| W8 | `tests/test_chat_list.py` | `implementer_agent` | n/a | Test authorship, same split as W4 |
| W9 | `src/whatsapp_chat_extractor/manifest.py` | `implementer_agent` | n/a | Product source authorship |
| W10 | `tests/test_manifest.py` | `implementer_agent` | n/a | Test authorship, same split as W4 |
| W11 | `src/whatsapp_chat_extractor/__main__.py` | `implementer_agent` | n/a | CLI surface is product source |
| W12 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | `doc_orchestrator` | n/a | Blueprint is the architecture record (`RA-05`) |
| W13 | `README.md` | `doc_orchestrator` | n/a | Operator-facing surface; `readme-standardizer` governs its shape |
| W14 | `docs/0_SYSTEM_OVERVIEW.md` | `doc_orchestrator` | n/a | Documentation Entry Point (`agents.md §0`) |
| W15 | `CHANGELOG.md` | `doc_orchestrator` | n/a | Master Ledger transcription; the entry's content is the lead agent's, the write is not |

**Gates.** Phase 7 runs `qa_agent` then `tester_agent` in fresh-context `Task`
with `modelId=claude-opus-5`, `effort=max` (measured this session via
`audit_cursor_models.py --resolve gate`). Fresh context is non-negotiable under
both tools; sequential mode is not an exemption.
