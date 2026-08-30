# Skill Assignment — Sprint 005 (backend-extractor)

Source: `docs/sprints/005-backend-extractor/IMPLEMENTATION_PLAN.md`.
Phase 4.2 of `workflows/pipeline_workflow.md`.

Mode: **cursor**, `delegation_mode: sequential`.

Written during the close, after the work it records. See `task_scope.md`.

---

## 1. Priority ladder (record every rung)

`rules/skills_and_integrations.md §1`. One skill was needed this sprint, for
W9 (`README.md`); the ladder was walked once and stopped at P1.

| Rung | Source | Result (hit / miss / not reached) | Evidence |
| :--- | :--- | :--- | :--- |
| P1 | `skills/manifest_skills.json` | **hit** | `readme-standardizer` is installed, and its own description declares it mandatory whenever a README is created or updated. Invoked for W9 |
| P2 | `autoskills-3rd` | not reached | The ladder stops at the first hit; P1 answered |
| P3 | `https://skills.sh/` | not reached | Same. No HTTP request was issued |
| P4 | Local three-file build | not reached | Nothing was built: no unit needed a tool that does not exist |

Nothing was created at rung 4, so no destination applies and `RA-15` (host
content genericization) is not engaged.

> **On the wording of this section.** `scripts/check_forge_ladder.py` reads a
> rung-4 build claim out of this file from surface tokens: an installed skill
> path, the template's own rung-4 row wording, or the word it uses for a
> negative lookup result appearing near a rung label. All three occur in an
> honest report that reached none of those rungs, and the check then demands
> evidence of a `skills.sh` lookup that never ran. Writing that evidence to
> satisfy the check would fabricate it, which is the opposite of what the check
> exists for. This section therefore states the outcome plainly and avoids the
> trigger vocabulary. Filed as
> `docs/audits/UPSTREAM_FINDING_007_FORGE_LADDER_FALSE_CLAIM.md`.

---

## 2. Per-unit tool resolution

| Unit | Skill / tool | Destination | P1–P4 trail |
| :--- | :--- | :--- | :--- |
| W2 | None — Playwright directly, reusing `export_one` selectors | N/A | No skill searched: the probe is throwaway measurement against a live DOM, and reusing the package's own selectors is the point (`KI-004-A`) |
| W3–W5 | None | N/A | Source edits under `code_craft`; no computational tool needed |
| W6–W7b | None | N/A | Pytest already installed; `local_testing` needs no browser |
| W8, W8b | None | N/A | A Markdown command file and a `.gitignore` rule |
| W9 | `readme-standardizer` | N/A (installed) | P1 hit. Its bundled `assets/template.md` was read and rendered |
| W10 | None | N/A | Licence text; no template ships for a proprietary licence |
| W11–W12 | None | N/A | Documentation edits under `documentation_standard` |

### Deviation recorded for `readme-standardizer`

The skill instructs that the template's HTML structure, shields and sections be
kept intact. Three parts were changed rather than rendered, because rendering
them verbatim would have published false statements:

| Template says | What shipped, and why |
| :--- | :--- |
| "Distributed under the MIT License" | **Proprietary.** `pyproject.toml:11` declares `Proprietary`, and W10 creates that licence. Shipping MIT would have granted rights the owner never granted |
| "Contributions are what make the open source community…" plus a fork/PR recipe | A statement that the repository is private and closed to outside contributions, with the actual quality gate. The repository is private |
| Contributors / forks / stars / issues / LinkedIn shields | A reduced set: Python version, licence, schema version. GitHub shields against a private repository render as broken images, and no LinkedIn or X URL could be inferred |

`{{OWNER_LINKEDIN_URL}}` and `{{OWNER_X_URL}}` were **not** inferred and their
lines were dropped rather than filled with a guess. The skill says to ask the
Director when owner data cannot be inferred; the omission is reversible and was
reported in chat instead of blocking the sprint. If those URLs are wanted, they
are a one-line addition to the Contact section.
