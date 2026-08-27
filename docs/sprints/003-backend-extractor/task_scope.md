# Task Scope — Sprint 003 (`backend-extractor` / P1)

**Branch**: `ai-sprint/003` · **Base**: `main` at `88d337c`
**Plan**: `docs/sprints/003-backend-extractor/IMPLEMENTATION_PLAN.md`
**Phase**: 5 sealed → ready for Phase 6 Execution

**Table shape (Work units).** `# | File | Operation | Risk | Assignee | Model | Effort | Status`

**Mode.** Cursor `delegation_mode: sequential`.

---

## Ownership map (who does what)

| Concern | Decides | Writes the artifact | Source of truth |
| :--- | :--- | :--- | :--- |
| Profile per unit | `agent_orchestrator` | `agent_assignment.md` | Phase 4.1 |
| File lock / risk / status | `rule_validator` | this file (Work tables) | Phase 4.3 |
| Tier escalation + Cursor model/effort | `token_economy_agent` | transcribed here | sequential session defaults |

## Cursor tier map (in force this session)

| Intent | Cursor | Effort |
| :--- | :--- | :--- |
| `author` / planning | session default (Composer) | high |
| `mechanical` | session default | N/A |
| `gate` | in-session RECORD (no separate Task) | N/A |

---

## Work

| # | File | Operation | Risk | Assignee | Model | Effort | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | `.agents` (gitlink) | pin v4.23.0 | low | `devops_agent` | session | N/A | pending |
| 1 | `pyproject.toml` | create | medium | `implementer_agent` | session | high | pending |
| 2 | `src/whatsapp_chat_extractor/__init__.py` | create | low | `implementer_agent` | session | N/A | pending |
| 3 | `src/whatsapp_chat_extractor/session.py` | create | high | `implementer_agent` | session | high | pending |
| 4 | `src/whatsapp_chat_extractor/export_one.py` | create | high | `implementer_agent` | session | high | pending |
| 5 | `src/whatsapp_chat_extractor/writers.py` | create | medium | `implementer_agent` | session | high | pending |
| 6 | `src/whatsapp_chat_extractor/__main__.py` | create | medium | `implementer_agent` | session | high | pending |
| 7 | `tests/test_writers.py` (+ fixture) | create | low | `implementer_agent` | session | high | pending |
| 8 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | create | medium | `doc_orchestrator` | session | high | pending |
| 9 | `docs/sprints/003-backend-extractor/SPIKE_NOTES.md` | create | medium | `doc_orchestrator` | session | high | pending |
| 10 | `docs/0_SYSTEM_OVERVIEW.md` | modify | low | `doc_orchestrator` | session | N/A | pending |
| 11 | `docs/roadmaps/docs/extractor/002-delivery-program.md` | modify | low | `doc_orchestrator` | session | N/A | pending |
| 12 | `docs/active_state.json` | modify | low | `topology_mapper` | session | N/A | pending |
| 13 | `docs/sprints/003-backend-extractor/IMPLEMENTATION_PLAN.md` | create | low | `doc_orchestrator` | session | high | ✅ |
| 14 | sprint scaffold (`SPRINT_LOG`, assignments) | create | low | `orchestrator` | session | N/A | ✅ |

Note: Writes performed by sequential Cursor session; assignees name the Write-capable profile for `check_task_scope.py`.

---

## Isolation notes

- One physical file per implementer task unit.
- Live WhatsApp Web only on operator Mac; CI uses fixtures only.
- Customer exports stay under gitignored `data/`.
- Do not mix `.agents` pin chore (W0) with Playwright product commits.
