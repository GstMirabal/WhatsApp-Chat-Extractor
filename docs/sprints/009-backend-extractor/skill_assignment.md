# 🛠️ Skill Assignment: Sprint #009

**Phase 4.2** (`skill_architect`) · Plan: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)
**Check**: `python3 .agents/scripts/check_forge_ladder.py --sprint-dir docs/sprints/009-backend-extractor`

Every unit has its tooling resolved below. Skills deliberately **not** used are
recorded beside those used, because a skill absent without a reason is
indistinguishable from a skill nobody looked for
(`pipeline_workflow.md` Phase 4.2).

---

## Tool resolution ladder

**No new skill is authored in this sprint, and the ladder stopped at rung 2 —
it did not run to the end and report nothing.** Stating where it stopped, and
why, is the point of this section.

| Rung | Question | Result |
| :--- | :--- | :--- |
| 1 — host `scripts/` | Does this project already carry a script for it? | **Not covered.** `scripts/` holds three operator-run probes (`probe_chat_list.py`, `probe_chat_start.py`, `probe_unknown_rows.py`). None journals, resumes, or parses timestamps |
| 2 — framework `skills/` | Does the installed library cover it? | **Not covered.** 34 skills present, zero match the computational subject |
| 3 — external registry | Does `autoskills-3rd` / `skills.sh` carry one? | **Not reached.** No registry query was issued, so no registry result is reported here |
| 4 — new skill | Should this sprint author one? | **No.** Decided on the reasoning below, not on a registry answer |

Rung 2 was actually run, and its command is quoted so the result is
reproducible:

```
cd .agents/skills && grep -rli "ndjson\|journal\|append-only\|fsync\|resume" \
  --include="SKILL.md" .        # returns nothing across 34 skills
```

**Why rung 3 was never reached.** A registry query answers *"does a reusable
tool for this exist?"*, and that question only matters once the work is agreed
to be tool-shaped. This sprint's computational work is not: it is ordinary
application code inside the host package — an append-only writer over `json` and
`os.fsync`, and a `datetime` parse of one known format under one pinned locale
(`§D7`). A skill is something an agent invokes across projects; `journal.py` and
`timestamps.py` are domain code that only this extractor calls. Lifting them
into the shared library would put the host's business logic there, which is
exactly what `RA-15` exists to prevent.

So rung 4 is answered `No` by scope, and rung 3 is moot. Recorded this way
rather than as an unqueried registry result, because an unissued query has no
outcome to report — an earlier draft of this file claimed one, and
`check_forge_ladder.py` correctly rejected it.

---

## Tooling per unit

| # | Unit subject | Tooling resolved | Skill invoked |
| :--- | :--- | :--- | :--- |
| A1, E2 | New modules (`journal.py`, `timestamps.py`) | `Write`; `ruff check .` | `python-quality-auditor` at the Quality Gate |
| A2, B2, C2, C3, E3, E6, E7 | Test authorship | `Write`/`Edit`; `python3 -m pytest -q` | — (pytest is invoked directly, not through a skill) |
| B1, E4, E5 | Modules under 300 lines (`manifest.py` 261, `history.py` 405, `writers.py` 176) | `Read` with offset/limit; `Edit` | **`omni-context-minimizer` required for `history.py`** (405 lines > 200, `agents.md §2 ast_skeleton`) |
| C1 | `__main__.py`, 421 lines | `Read` with offset/limit; `Edit` | **`omni-context-minimizer` required** (`agents.md §2 token_saver`) |
| E1 | `session.py`, 129 lines | Full `Read` permitted (< 200 lines); `Edit` | — |
| D1–D4 | ADRs, Blueprint, System Overview | `Write`/`Edit` | `readme-standardizer` **not applicable** (no README changes); templates from `.agents/docs/standards/templates/` |
| All | Pre-commit | `Bash` | `env-shielding-auditor` at the Quality Gate — the sprint adds no secret, but `data/` must stay untracked |

**Already invoked this session**: `omni-context-minimizer` produced the AST
skeletons of `history.py` (406 lines → 21) and `export_one.py` (681 → 33) during
Phase 1, which is how `§D6` established that `export_one.py` needs no change.

---

## Skills deliberately not used

| Skill | Why not |
| :--- | :--- |
| `django-*` (5 skills), `nodejs-*`, `vercel-*`, `tailwind-css-patterns`, `typescript-advanced-types`, `vite`, `frontend-design`, `accessibility`, `seo` | Wrong stack. This is a Python CLI package with no web surface |
| `graphify` | No `graphify-out/` exists and the MCP server failed to connect this session (`ENOENT` on `.agents/venv_skillopt/bin/python`). `agents.md §2 graph_sovereignty` mandates it *before recursive grep research*; Phase 1 used targeted reads and AST skeletons instead, which is the sanctioned alternative. **Rebuild is due at Phase 8** (`make -f .agents/Makefile graphify-rebuild`) |
| `skill-creator`, `skillopt`, `mass-standardizer` | No skill is forged or optimized (P4 above) |
| `contract-writer` | Produces API contracts under `docs/contracts/`. This sprint changes a **file schema**, not an API surface; `ADR-0007` is the right artifact and `doc_orchestrator` owns it |
| `sprint-architect` | Its job is breaking a roadmap into a plan. Phase 1 is already closed and the plan is committed at `a4a22df` |
| `token-saver-auditor` | **Used, not skipped** — `audit_plan.py` gated the plan at Phase 1 (exit `0`). Listed here so its use is not mistaken for absence |
| `compliance-checker` | Overlaps `rule_validator` at Phase 4.3, which produces `task_scope.md` directly. Running both would audit the same rules twice |
| `readme-standardizer` | No `README.md` change in the 18 units |
| `topology-scaffolder` | The sprint directory exists; no structural scaffolding is due |
