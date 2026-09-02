# 🧑‍🔧 Agent Assignment: Sprint #009

**Phase 4.1** (`agent_orchestrator`) · Plan: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)
**Check**: `python3 .agents/scripts/check_forge_ladder.py --sprint-dir docs/sprints/009-backend-extractor`

The Implementation Plan's `Assignee (proposed)` column is a Phase 1 proposal.
**This file is the authority** (`pipeline_workflow.md` Phase 4.1). A Work row is
not closed until it appears here.

---

## Forge ladder

**No agent profile is forged in this sprint.** Every unit is assigned to a
profile that already exists in the nucleus and already declares the tools its
rows require, so no `Destination` column applies (`RA-16`, `D19`).

| Profile | Path | `tools:` declared | Tier |
| :--- | :--- | :--- | :--- |
| `implementer_agent` | `.agents/agents/implementer_agent.md` | `Read, Glob, Grep, Write, Edit, Bash` | `author` |
| `doc_orchestrator` | `.agents/agents/doc_orchestrator.md` | `Read, Glob, Grep, Write, Edit` | `author` |

Verified rather than assumed — the capability check in `check_task_scope.py`
rejects a mutating row whose assignee declares no `Write`/`Edit`:

```
grep -m1 "^tools:" .agents/agents/implementer_agent.md
grep -m1 "^tools:" .agents/agents/doc_orchestrator.md
```

**Why `implementer_agent` and not `devops_agent` for `scripts/`-shaped work**:
`ADR-0009` (Sprint 033) moved authorship of framework-root `scripts/`, `hooks/`
and `tests/` to `implementer_agent`; `devops_agent` retains `Bash` for
environment routines and holds no `Write`/`Edit`. Every code and test unit below
is authorship, so none of them is `devops_agent` work.

---

## Assignment

### Block A — Run journal

| # | File | Operation | Assignee | Why this profile |
| :--- | :--- | :--- | :--- | :--- |
| A1 | `src/whatsapp_chat_extractor/journal.py` | create | `implementer_agent` | Source authorship in the host package |
| A2 | `tests/test_journal.py` | create | `implementer_agent` | Test authorship. `tester_agent` **emits verdicts and does not write tests** (`F-026-A1`) |

### Block B — Manifest reconstruction

| # | File | Operation | Assignee | Why this profile |
| :--- | :--- | :--- | :--- | :--- |
| B1 | `src/whatsapp_chat_extractor/manifest.py` | modify | `implementer_agent` | Source authorship |
| B2 | `tests/test_manifest.py` | modify | `implementer_agent` | Test authorship |

### Block C — Resume orchestration

| # | File | Operation | Assignee | Why this profile |
| :--- | :--- | :--- | :--- | :--- |
| C1 | `src/whatsapp_chat_extractor/__main__.py` | modify | `implementer_agent` | Source authorship. Highest-risk unit: 421 lines with pre-existing complexity debt |
| C2 | `tests/test_export_all.py` | modify | `implementer_agent` | Test authorship |
| C3 | `tests/test_resume.py` | create | `implementer_agent` | Test authorship |

### Block E — Corpus contract v6

| # | File | Operation | Assignee | Why this profile |
| :--- | :--- | :--- | :--- | :--- |
| E1 | `src/whatsapp_chat_extractor/session.py` | modify | `implementer_agent` | Source authorship. Playwright launch options, not environment management — `devops_agent` holds no `Write` |
| E2 | `src/whatsapp_chat_extractor/timestamps.py` | create | `implementer_agent` | Source authorship |
| E3 | `tests/test_timestamps.py` | create | `implementer_agent` | Test authorship |
| E4 | `src/whatsapp_chat_extractor/history.py` | modify | `implementer_agent` | Source authorship |
| E5 | `src/whatsapp_chat_extractor/writers.py` | modify | `implementer_agent` | Source authorship. Schema break v5 → v6 |
| E6 | `tests/test_history.py` | modify | `implementer_agent` | Test authorship |
| E7 | `tests/test_writers.py` | modify | `implementer_agent` | Test authorship |

### Block D — Documentation

| # | File | Operation | Assignee | Why this profile |
| :--- | :--- | :--- | :--- | :--- |
| D1 | `docs/decisions/ADR-0006-run-journal-and-resume.md` | create | `doc_orchestrator` | ADR authorship (`rules/documentation_standard.md`) |
| D2 | `docs/decisions/ADR-0007-corpus-contract-v6.md` | create | `doc_orchestrator` | ADR authorship |
| D3 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | `doc_orchestrator` | Blueprint maintenance (`RA-05`) |
| D4 | `docs/0_SYSTEM_OVERVIEW.md` | modify | `doc_orchestrator` | Documentation Entry Point maintenance |

---

## Roles that are deliberately absent

Recorded rather than omitted: a role missing without a reason reads as an
oversight (`pipeline_workflow.md` Phase 4 note).

| Role | Why it holds no unit here |
| :--- | :--- |
| `devops_agent` | Phase 2 ran and passed (`.venv`, 224 passed / 1 skipped, `ruff` exit `0`). No Docker, no database, no `.env` in this sprint. It authors nothing (`ADR-0009`) |
| `orchestrator` | Owns `SPRINT_LOG.md`, already written at Phase 3 (`8203712`), and transcribes the Phase 7 gate rows. Holds no execution unit |
| `qa_agent` / `tester_agent` | Phase 7 only. They emit verdicts; they write no file (`ADR-0008`) |
| `skill_architect` | No skill is forged (Phase 4.2). It has no unit when the ladder does not reach a forge |
| `topology_mapper` | No structural directory is scaffolded; `docs/sprints/009-backend-extractor/` already exists |
| `agent_orchestrator` | Author of this file. Assigns; does not execute |
| `principal_agent` | Phases 1, 5 and 8. Holds the Approval Gate, writes no code |
