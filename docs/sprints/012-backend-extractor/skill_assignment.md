# Skill Assignment — Sprint 012 (backend-extractor)

Source: `docs/sprints/012-backend-extractor/IMPLEMENTATION_PLAN.md`.
Phase 4.2 of `workflows/pipeline_workflow.md`.

Mode: **claude-code**, `delegation_mode: native`.

---

## 1. Priority ladder (record every rung)

`rules/skills_and_integrations.md §1`:

No unit in this sprint's Work table forges a new skill. The ladder is
recorded per the one unit (row 4, `README.md`) where an existing skill
applies; every other unit is a direct file edit needing no skill lookup.

| Rung | Source | Result | Evidence |
| :--- | :--- | :--- | :--- |
| P1 | `skills/manifest_skills.json` | Hit — `readme-standardizer` | `manifest_skills.json` entry: "Use this Skill ALWAYS whenever you are asked to create, generate, standardize, or update a project's README.md." |
| P2 | `autoskills-3rd` | Not reached | P1 already resolved the one row that needed a skill |
| P3 | `https://skills.sh/` | Not reached | P1 already resolved the one row that needed a skill |
| P4 | Three-File Standard at Destination | Not reached | No skill is being forged this sprint |

---

## 2. Per-unit tool resolution

| Unit | Skill / tool | Destination | P1–P4 trail |
| :--- | :--- | :--- | :--- |
| 1 | None — `Edit` on `export_one.py` | N/A | Not applicable; direct source edit |
| 2 | None — `Write`/`Edit`, `pytest` | N/A | Not applicable; direct test authoring |
| 3 | None — `Edit`, `pytest` | N/A | Not applicable; direct test authoring |
| 4 | `readme-standardizer` | N/A (existing skill, not forged) | P1 hit, see above |
| 5 | None — `Edit` | N/A | Not applicable; direct doc edit |
| 6 | None — `Edit` | N/A | Not applicable; direct doc edit |
| 7 | None — `Edit` | N/A | Not applicable; direct config edit |
| 8 | None — `Edit` | N/A | Not applicable; direct config edit |
| 9 | None — `Edit` | N/A | Not applicable; direct anchor edit (untracked, `.gitignore:37`) |
| 10 | None — `Write` | N/A | Not applicable; no skill covers `CONTRIBUTING.md` authorship for this project's own conventions |
| 11 | None — `Write` | N/A | Not applicable; same as row 10 |
| 12 | None — `Write` | N/A | Not applicable; same as row 10 |
| 13 | None — `Write` | N/A | Not applicable; same as row 10 |
| 14 | None — `Write` | N/A | Not applicable; `docs/RUNBOOK.md` is project-specific operational documentation, no generic skill covers it |

---

## 3. Skills used

| Skill | Why |
| :--- | :--- |
| `readme-standardizer` | Row 4 updates `README.md`; the skill's own trigger is unconditional ("ALWAYS ... update") |

---

## 4. Skills considered and rejected

| Candidate | Why rejected |
| :--- | :--- |
| `python-quality-auditor` | Owned by the Phase 7 QA Gate (`agents.md §1 linter_command`), not Phase 4.2 authoring; rows 1-3 still get `ruff check .` and the AST complexity walk at Verification/Phase 7, unchanged |
| `omni-context-minimizer` | Every file this sprint touches is under 200 lines except none identified over the threshold at plan time; re-check per file at Phase 6 if a target turns out longer (`agents.md §2 ast_skeleton`) |
| `env-shielding-auditor` | No `.env`/secret-shaped file is created or modified by any Work row |
| `mass-standardizer` | Applies to the `skills/` library itself; this sprint forges no skill |

---

## 5. Gaps

None. Every Work row resolves to a direct tool call (`Read`/`Edit`/`Write`/
`Bash`) or one existing skill; no forge is proposed, so
`scripts/check_forge_ladder.py`'s empty-destination/contamination checks
have nothing to reject.
