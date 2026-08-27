# Task Scope — Sprint 001 (`docs-onboarding`)

**Branch**: `ai-sprint/001` · **Base**: `main` at `2336a6e`
**Plan**: `docs/sprints/001-docs-onboarding/IMPLEMENTATION_PLAN.md`
**Phase**: 4.3 (Rule Audit) — after `agent_assignment.md` (4.1) and
`skill_assignment.md` (4.2).

**Table shape (Work units).** `# | File | Operation | Risk | Assignee | Model | Effort | Status`

**Status legend.** `⏳` pending Phase 6; `✅ <sha>` after execution.

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

**No escalations.** Docs-only; no mechanical+high without note.

---

## Work

| # | File | Operation | Risk | Assignee | Model | Effort | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `docs/sprints/001-docs-onboarding/IMPLEMENTATION_PLAN.md` | create | low | `doc_orchestrator` | session | high | ✅ `14dd0bf` |
| 2 | `docs/architecture/.gitkeep` (represents docs tree scaffold) | create | low | `topology_mapper` | session | N/A | ✅ `14dd0bf` |
| 3 | `docs/0_SYSTEM_OVERVIEW.md` | create | low | `doc_orchestrator` | session | high | ✅ `14dd0bf` |
| 4 | `docs/active_state.json` | create | low | `topology_mapper` | session | N/A | ✅ (gitignored; claimed) |
| 5 | `CHANGELOG.md` | create | low | `doc_orchestrator` | session | high | ✅ `14dd0bf` |
| 6 | `identity.config.json` | modify | low | `doc_orchestrator` | session | high | ✅ `14dd0bf` |
| 7 | `.gitignore` | modify | low | `implementer_agent` | session | N/A | ✅ `14dd0bf` |

Note: Unit 1 assignee in `agent_assignment` is `principal_agent` (ruleset); file Write performed by session under sequential mode. Listed here as `doc_orchestrator` for the mutating Write capability check (`check_task_scope.py`).

---

## Isolation notes

- `jurisdictional_lock`: greenfield batch landed as one onboarding commit `14dd0bf` (accepted for Scenario A first scaffold; subsequent sprints resume one-file commits).
- Product code and API design explicitly out of scope.
