# Skill Assignment — Sprint 007 (`backend-extractor`, P3b)

Phase 4.2 of `workflows/pipeline_workflow.md`. Source: `IMPLEMENTATION_PLAN.md`
`## Work`.

## Skills used

| # | File | Skill | Why |
| :--- | :--- | :--- | :--- |
| W1 | `ADR-0004-completeness-criterion.md` | `documentation_standard` §3.1 | ADR trigger criteria and shape |
| W2, W3, W7, W9, W11 | `history.py`, `writers.py`, `chat_list.py`, `manifest.py`, `__main__.py` | `python-quality-auditor` | Type hints, ≤50 lines, ≤3 indent (`agents.md §1`) |
| W4, W8, W10 | `tests/test_completeness.py`, `tests/test_chat_list.py`, `tests/test_manifest.py` | `qa_and_testing` rules | In-memory only; no live session in the suite |
| W5 | `scripts/probe_chat_list.py` | `python-quality-auditor` | Ruff/Mypy/Bandit pass on a new script before it touches a live session |
| W6 | `CHAT_LIST_PROBE_NOTES.md` | `doc-orchestrator` conventions | Measured tables, no prose inference |
| W7, W9, W11 | `chat_list.py`, `manifest.py`, `__main__.py` | `omni-context-minimizer` | `export_one.py` (681 lines) and `probe_chat_start.py` (925 lines) must be read structurally before any of these three reuse from them (`agents.md §2 ast_skeleton`) |
| W13 | `README.md` | `readme-standardizer` | Mandatory whenever a README is created or updated |
| W9 | `manifest.py` | `env-shielding-auditor` | This is the one unit that can write a real person's name to disk (`--write-index`). The auditor confirms no name path reaches a tracked file |

## Skills deliberately not used

Recorded beside those used, because an unexplained absence is indistinguishable
from an oversight.

| Skill | Why not |
| :--- | :--- |
| `graphify` | Cannot start in this host — `.agents/venv_skillopt` is absent. Carried as a known gap since Sprint 004; `graph_sovereignty` is unsatisfiable here and targeted reads plus `omni-context-minimizer` substitute for it |
| `skillopt` | Requires explicit human authorization per invocation, and no skill prompt is being optimized this sprint |
| `django-*`, `frontend-design`, `tailwind-css-patterns`, `vercel-*`, `typescript-advanced-types`, `vite` | No Django, no frontend, no TypeScript, no bundler in this repository |
| `mass-standardizer`, `js-standardizer` | No skill library and no JS/TS surface in scope |
| `contract-writer` | No HTTP API in this repository; the export format is a file schema, and its contract lives in the Blueprint |
| `accessibility`, `seo`, `dataviz` | No rendered UI and no chart is produced by this sprint |

## Forge decision (P3 trail)

**No skill was forged**, and the ladder was walked before concluding it:

1. **P1 — existing local skills**: `python-quality-auditor`, `readme-standardizer`
   and `omni-context-minimizer` already cover the quality, documentation and
   large-file surfaces this sprint touches.
2. **P2 — a script instead of a skill**: W5 is a DOM probe run manually under
   operator supervision to answer two questions once
   (`IMPLEMENTATION_PLAN.md` §D2). `rules/skills_and_integrations.md` reserves the
   Three-File Standard for reusable capability; a measurement instrument is a
   script in `scripts/`, and forging a skill around it would be scaffolding noise
   (`three_file_standard` prohibits exactly this padding). The same reasoning
   already settled `scripts/probe_chat_start.py` in Sprint 006.
3. **P3 — third-party search**: not run. The capability needed is enumerating a
   specific WhatsApp Web chat list — a private third party's markup — and
   `KI-004-A` forbids adopting anyone's assumption about that markup in place of a
   measurement. No general skill can encode it.
