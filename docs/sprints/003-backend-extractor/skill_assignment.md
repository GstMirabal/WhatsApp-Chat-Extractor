# Skill Assignment — Sprint 003 (`backend-extractor` / P1)

Source: `docs/sprints/003-backend-extractor/IMPLEMENTATION_PLAN.md`.
Phase 4.2 of `workflows/pipeline_workflow.md`.

Mode: **cursor**, `delegation_mode: sequential`.

After writing this file, run:
`python3 .agents/scripts/check_forge_ladder.py --sprint-dir docs/sprints/003-backend-extractor`

---

## 1. Priority ladder (record every rung)

`rules/skills_and_integrations.md §1`:

| Rung | Source | Result (hit / miss / skipped) | Evidence |
| :--- | :--- | :--- | :--- |
| P1 | `skills/manifest_skills.json` | hit | `python-quality-auditor`, `env-shielding-auditor`, BLUEPRINT / plan templates |
| P2 | `autoskills-3rd` | not escalated | No unresolved tool gap after P1 for docs; Playwright is a dependency not a skill |
| P3 | `https://skills.sh/` | skipped | No unresolved tool gap after P1 |
| P4 | Three-File Skill Standard destination | not used | No new framework skill this sprint (Cursor dump skill = P2) |

---

## 2. Per-unit tool resolution

| Unit | Skill / tool | Destination | P1–P4 trail |
| :--- | :--- | :--- | :--- |
| 0 | git / submodule pin | `.agents` | N/A |
| 1–6 | Playwright (pip) + session code | `src/whatsapp_chat_extractor/` | P1 hit (dependency; no skill forge) |
| 7 | `pytest` + `python-quality-auditor` (lint later) | `tests/` | P1 hit |
| 8–11 | templates + `doc_orchestrator` | `docs/` | P1 hit |
| 12 | topology / session_state | `docs/active_state.json` | N/A |

---

## 3. Skills used

| Skill | Why |
| :--- | :--- |
| Built-in standards templates | IMPLEMENTATION_PLAN / BLUEPRINT structure |
| `python-quality-auditor` | Ruff/mypy/bandit when package lands |
| `env-shielding-auditor` | No secrets in profile path / commits |

## 4. Skills considered and rejected

| Candidate | Why rejected |
| :--- | :--- |
| New Cursor “run dump” skill | Belongs to Sprint 004 (P2) |
| Browser MCP for export | ADR-0002: deterministic scripts own the DOM path |

## 5. Gaps

None that block P1. Graphify after `src/` exists (~25 sources threshold advisory).
