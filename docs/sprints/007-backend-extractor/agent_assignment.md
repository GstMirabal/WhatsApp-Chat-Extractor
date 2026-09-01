# Agent Assignment — Sprint 007 (`backend-extractor`, P3b)

Phase 4.1 of `workflows/pipeline_workflow.md`. Source: `IMPLEMENTATION_PLAN.md`
`## Work`.

**Mode.** `session_tool: claude-code`, `delegation_mode: native`. `Assignee` names
the profile whose ruleset governs each write and which may be dispatched as a
subagent. Model tiers come from `config/model_tiers.json` `claude_code`, not from
`audit_cursor_models.py` — see `task_scope.md` §Model tiers for why this file was
first written for the wrong harness.

**Declared mode and effective execution diverge, and the divergence is reported
rather than absorbed** (`start_workflow.md` `delegation_conflict`). The harness
can dispatch the eight roles; this session's operating instructions forbid
spawning subagents unless the human asks for them. Execution therefore proceeds
sequentially in the parent, with `Assignee` read as the governing ruleset for
each write. Silent self-substitution is prohibited — this paragraph is the
report, and fan-out is available on request.

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

**Gates.** Phase 7 runs `qa_agent` then `tester_agent` in fresh context at the
gate tier — `model: opus`, `effort: high` (`config/model_tiers.json`
`tiers.gate.claude_code`). Fresh context is non-negotiable under both tools and
is the one place this sprint will dispatch subagents regardless of the divergence
above: a gate that reviews its own author's context is not a gate.
