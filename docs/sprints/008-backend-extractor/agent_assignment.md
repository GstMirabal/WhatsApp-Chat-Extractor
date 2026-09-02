# Agent Assignment — Sprint 008 (backend-extractor)

Source: `docs/sprints/008-backend-extractor/IMPLEMENTATION_PLAN.md` (`## Work`).
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

`Destination` is **required** on every unit that **creates** an agent profile.
Values: `host:.claude/agents/` (default), `profile:<path>`, `nucleus:PR`.
Units that do not create a profile use `N/A`.

This sprint creates **no** agent profile, so every `Destination` is `N/A`.

---

## Staffing

### Wave A — Preflight

| # | Target | Operation | Mode | Assignee | Destination | Ruleset file |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| A1 | `docs/sprints/008-backend-extractor/GATE_CHANNEL_DIAGNOSIS.md` | create | ruleset | `orchestrator` | N/A | `agents/orchestrator.md` |
| A2 | `docs/active_state.json` | modify | ruleset | `orchestrator` | N/A | `agents/orchestrator.md` |
| A3 | `docs/0_SYSTEM_OVERVIEW.md` | modify | ruleset | `doc_orchestrator` | N/A | `agents/doc_orchestrator.md` |

### Wave B — Enumeration undercount

| # | Target | Operation | Mode | Assignee | Destination | Ruleset file |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| B1 | `docs/decisions/ADR-0005-enumeration-completeness.md` | create | ruleset | `doc_orchestrator` | N/A | `agents/doc_orchestrator.md` |
| B2 | `src/whatsapp_chat_extractor/chat_list.py` | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| B3 | `tests/test_chat_list.py` | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| B4 | `src/whatsapp_chat_extractor/manifest.py` | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| B5 | `tests/test_manifest.py` | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| B6 | `src/whatsapp_chat_extractor/__main__.py` | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| B7 | `tests/test_export_all.py` | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| B8 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | ruleset | `doc_orchestrator` | N/A | `agents/doc_orchestrator.md` |

### Wave C — Unknown-row probe

| # | Target | Operation | Mode | Assignee | Destination | Ruleset file |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C1 | `scripts/probe_unknown_rows.py` | create | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| C2 | `tests/test_probe_unknown_rows.py` | create | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| C3 | `docs/sprints/008-backend-extractor/PROBE_UNKNOWN_ROWS_RUN.md` | create | ruleset | `doc_orchestrator` | N/A | `agents/doc_orchestrator.md` |

### Wave D — Platform and upstream debt

| # | Target | Operation | Mode | Assignee | Destination | Ruleset file |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| D1 | `docs/PLATFORM_HARDENING.md` | modify | ruleset | `doc_orchestrator` | N/A | `agents/doc_orchestrator.md` |
| D2 | `docs/audits/UPSTREAM_FINDING_008_BOOT_MISROUTE.md` | create | ruleset | `rule_validator` | N/A | `agents/rule_validator.md` |
| D3 | `docs/audits/UPSTREAM_FINDING_009_POST_CONDITION.md` | create | ruleset | `rule_validator` | N/A | `agents/rule_validator.md` |
| D4 | `docs/audits/UPSTREAM_FINDING_010_AUDIT_PLAN_FILTER6.md` | create | ruleset | `rule_validator` | N/A | `agents/rule_validator.md` |
| D5 | `docs/audits/UPSTREAM_FINDING_011_MAKEFILE_UNQUOTED.md` | create | ruleset | `rule_validator` | N/A | `agents/rule_validator.md` |

## Disagreements with the plan

One overwrite. The Implementation Plan proposed `devops_agent` for D1.

| # | Plan proposed | Recorded here | Reason |
| :--- | :--- | :--- | :--- |
| D1 | `devops_agent` | `doc_orchestrator` | `devops_agent` holds `Read`, `Glob`, `Grep`, `Bash` and **no `Write`/`Edit`** (`agents.md §6`, `ADR-0009`), so it cannot perform D1's `modify`. `scripts/check_task_scope.py` rejected the plan's proposal with exit `2` on exactly this capability test. The `/agents:harden` execution itself is still `devops_agent`'s `Bash` work; what moves is authorship of the record it produces — the same emitter/transcriber split `F-026-A1` applies to `tester_agent` and test files |

## Note on `implementer_agent` and `scripts/`

`agents.md §6` assigns framework-root `scripts/` authorship to
`implementer_agent`, not `devops_agent` (`ADR-0009`, `F-086-A1`). Unit C1 writes
`scripts/probe_unknown_rows.py` in the **host** tree and follows the same
ownership, matching how Sprint 006 and 007 staffed `scripts/probe_chat_start.py`
and `scripts/probe_chat_list.py`. D1 stays with `devops_agent` because its
subject is platform controls and the `gh` CLI, not source authorship.
