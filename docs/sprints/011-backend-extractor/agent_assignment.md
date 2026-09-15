# Agent Assignment — Sprint 011 (backend-extractor)

Source: `docs/sprints/011-backend-extractor/IMPLEMENTATION_PLAN.md` (`## Work`).
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

## Forge ladder

**No agent profile is forged in this sprint.** Every unit is assigned to
`implementer_agent`, which already exists in the nucleus at
`.agents/agents/implementer_agent.md` and already declares the tools its rows
require, so no forge row applies (`RA-16`, `D19`).

| Profile | Path | `tools:` declared | Tier |
| :--- | :--- | :--- | :--- |
| `implementer_agent` | `.agents/agents/implementer_agent.md` | `Read, Glob, Grep, Write, Edit, Bash` | `author` |

**Why `implementer_agent` and not `devops_agent`**: `ADR-0009` (Sprint 033)
moved authorship of framework-root `scripts/`, `hooks/` and `tests/` to
`implementer_agent`; `devops_agent` retains `Bash` for environment routines and
holds no `Write`/`Edit`. All 13 units below are source or test authorship
inside the host's `src/whatsapp_chat_extractor/` package or its `tests/` tree,
none of them `devops_agent` work.

---

## Staffing

### Block A — `KI-009-H` (deadline-bounded harvest, blocking item)

| # | Target | Operation | Mode | Assignee | Destination | Ruleset file |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `src/whatsapp_chat_extractor/history.py` | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| 2 | `src/whatsapp_chat_extractor/__main__.py` (CLI flag wiring only, Block A) | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| 3 | `tests/test_history.py` | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |

### Block B — `T-8` (journal first-header-wins fix)

| # | Target | Operation | Mode | Assignee | Destination | Ruleset file |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 4 | `src/whatsapp_chat_extractor/journal.py` | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| 5 | `tests/test_journal.py` | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |

### Block C — `§D6` + pre-existing complexity (`commands.py` extraction)

| # | Target | Operation | Mode | Assignee | Destination | Ruleset file |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 6 | `src/whatsapp_chat_extractor/commands.py` (new, Block C extraction) | create | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| 7 | `src/whatsapp_chat_extractor/__main__.py` (strip `cmd_*`, Block C) | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| 8 | `src/whatsapp_chat_extractor/export_one.py` | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| 9 | `tests/test_export_all.py` / `test_resume.py` / `test_consolidate_cli.py` (repoint patches, Block C) | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |

### Block D — `§D5` (append-only chat index)

| # | Target | Operation | Mode | Assignee | Destination | Ruleset file |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 10 | `src/whatsapp_chat_extractor/manifest.py` | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| 11 | `tests/test_manifest.py` | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |

### Block E — `T-2`, `T-1`–`T-7` (test-only coverage gaps)

| # | Target | Operation | Mode | Assignee | Destination | Ruleset file |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 12 | `tests/test_consolidate.py` / `test_consolidate_cli.py` (`T-1`–`T-7`) | modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |
| 13 | `tests/test_export_search.py` or new `tests/test_timezone.py` (`T-2`) | create/modify | ruleset | `implementer_agent` | N/A | `agents/implementer_agent.md` |

`jurisdictional_lock` note carried from the plan: rows 9 and 12 each name more
than one physical file because they are a single coherent
test-repointing/coverage pass, not independent structural edits. Not split
further here — Execution (Phase 6) commits one physical file per commit where
`jurisdictional_lock` applies, regardless of how the row is written in this
table.

---

## Roles that are deliberately absent

Recorded rather than omitted: a role missing without a reason reads as an
oversight (`pipeline_workflow.md` Phase 4 note).

| Role | Why it holds no unit here |
| :--- | :--- |
| `devops_agent` | No Docker, database, or `.env` work in this sprint's Work table; it authors nothing under `scripts/`/`hooks/`/`tests/` (`ADR-0009`) |
| `orchestrator` | Owns `SPRINT_LOG.md`, written at Phase 3, and transcribes the Phase 7 gate rows. Holds no execution unit |
| `qa_agent` / `tester_agent` | Phase 7 only. They emit verdicts; they write no file (`ADR-0008`) |
| `skill_architect` | No skill is forged (Phase 4.2). It has no unit when the ladder does not reach a forge |
| `agent_orchestrator` | Author of this file. Assigns; does not execute |
| `principal_agent` | Phases 1, 5 and 8. Holds the Approval Gate, writes no code |
| `doc_orchestrator` | This sprint's `Documentary impact (T5)` rows (roadmap, blueprint, `CHANGELOG.md`) are Phase 8 Sprint Closeout deliverables, not Work-table units — no row assigns `doc_orchestrator` here |

## Disagreements with the plan

None. All 13 Work rows keep the plan's proposed assignee `implementer_agent`;
nothing in `IMPLEMENTATION_PLAN.md` gives a reason to disagree with any of
them.
