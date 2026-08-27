# Skill Assignment — Sprint 001 (docs-onboarding)

Source: `docs/sprints/001-docs-onboarding/IMPLEMENTATION_PLAN.md`.
Phase 4.2 of `workflows/pipeline_workflow.md`. Drafted from this template.

Mode: **cursor**, `delegation_mode: sequential`.

After writing this file, run:
`python3 .agents/scripts/check_forge_ladder.py --sprint-dir docs/sprints/001-docs-onboarding`

---

## 1. Priority ladder (record every rung)

`rules/skills_and_integrations.md §1`:

| Rung | Source | Result (hit / miss / skipped) | Evidence |
| :--- | :--- | :--- | :--- |
| P1 | `skills/manifest_skills.json` | hit | `topology-scaffolder` catalogued; standards templates for overview/changelog/plan |
| P2 | `autoskills-3rd` | not escalated | No unresolved tool gap after P1 |
| P3 | `https://skills.sh/` | not queried | No unresolved tool gap after P1 |
| P4 | Three-File Skill Standard destination | not used | Existing catalog skills only; nothing authored this sprint |

---

## 2. Per-unit tool resolution

| Unit | Skill / tool | Destination | P1–P4 trail |
| :--- | :--- | :--- | :--- |
| 1 | None (plan prose) | N/A | P1: no plan-writer skill; session authored under principal ruleset |
| 2 | `topology-scaffolder` (procedures; manual mkdir) | N/A | P1 hit |
| 3–6 | template copy from `.agents/docs/standards/templates/` | N/A | P1 hit (templates) |
| 7 | git / `implementer_agent` | N/A | N/A |

---

## 3. Skills used

| Skill | Why |
| :--- | :--- |
| `topology-scaffolder` | Mandatory `docs/` tree injection guidance |
| Built-in `session_state.py claim` | Host anchor lock |

## 4. Skills considered and rejected

| Candidate | Why rejected |
| :--- | :--- |
| `readme-standardizer` | README render deferred until after identity debate / optional `render_readme.py` |
| `graphify` | Host <~25 sources; graph skipped (advisory) |

## 5. Gaps

None for Sprint 001 scope. Product extractor skills deferred to 002+.
