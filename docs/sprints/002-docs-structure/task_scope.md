# Task Scope — Sprint 002 (`docs-structure` / P0)

**Branch**: `ai-sprint/002` · **Base**: `main` at `805b130`
**Plan**: `docs/sprints/002-docs-structure/IMPLEMENTATION_PLAN.md`
**Phase**: 4.3 (Rule Audit)

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

**No escalations.** Docs-only.

---

## Work

| # | File | Operation | Risk | Assignee | Model | Effort | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `docs/decisions/ADR-0001-product-scope-whatsapp-web.md` | create | medium | `doc_orchestrator` | session | high | ✅ `5578cbe` |
| 2 | `docs/decisions/ADR-0002-delivery-program-and-layout.md` | create | medium | `doc_orchestrator` | session | high | ✅ `5578cbe` |
| 3 | `docs/roadmaps/docs/extractor/002-delivery-program.md` | create | low | `doc_orchestrator` | session | high | ✅ `5578cbe` |
| 4 | `docs/0_SYSTEM_OVERVIEW.md` | modify | medium | `doc_orchestrator` | session | high | ✅ `5578cbe` |
| 5 | `docs/roadmaps/docs/onboarding/001-greenfield-adoption.md` | modify | low | `doc_orchestrator` | session | N/A | ✅ `5578cbe` |
| 6 | `.gitignore` | modify | low | `implementer_agent` | session | N/A | ✅ `5578cbe` |
| 7 | `docs/sprints/002-docs-structure/IMPLEMENTATION_PLAN.md` | modify | low | `doc_orchestrator` | session | high | ✅ approval seal |
| 8 | `docs/active_state.json` | modify | low | `topology_mapper` | session | N/A | ✅ (gitignored) |

Note: Writes performed by sequential Cursor session; assignees name the Write-capable profile for `check_task_scope.py`.

---

## Isolation notes

- Docs-only P0; no product `src/`.
- Customer exports deferred to gitignored `data/` (no files written this sprint).
