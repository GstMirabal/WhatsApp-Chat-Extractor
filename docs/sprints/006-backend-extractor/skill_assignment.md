# Skill Assignment — Sprint 006 (`backend-extractor`, P3a)

Phase 4.2 of `workflows/pipeline_workflow.md`. Source: `IMPLEMENTATION_PLAN.md`
`## Work`.

## Skills used

| # | File | Skill | Why |
| :--- | :--- | :--- | :--- |
| W1 | `scripts/probe_chat_start.py` | `python-quality-auditor` | Ruff/Mypy/Bandit pass on a new script before it touches a live session |
| W2 | `DOM_PROBE_NOTES.md` | `doc-orchestrator` conventions | Measured tables, no prose inference |
| W3 | `ADR-0004-completeness-criterion.md` | `documentation_standard` §3.1 | ADR trigger criteria and shape |
| W4, W6 | `history.py`, `writers.py` | `python-quality-auditor` | Type hints, ≤50 lines, ≤3 indent (`agents.md §1`) |
| W5 | `tests/test_completeness.py` | `qa_and_testing` rules | In-memory only; no live session in the suite |
| W8 | `README.md` | `readme-standardizer` | Mandatory whenever a README is created or updated |

## Skills deliberately not used

Recorded beside those used, because an unexplained absence is indistinguishable
from an oversight.

| Skill | Why not |
| :--- | :--- |
| `graphify` | Cannot start in this host — `.agents/venv_skillopt` is absent. Carried as a known gap since Sprint 004; `graph_sovereignty` is unsatisfiable here and targeted reads substitute for it |
| `omni-context-minimizer` | `history.py` is the only file near the 200-line threshold; partial reads with offset/limit on the affected functions are sufficient and cheaper |
| `skillopt` | Requires explicit human authorization per invocation, and no skill prompt is being optimized this sprint |
| `django-*`, `frontend-design`, `tailwind-css-patterns`, `vercel-*` | No Django, no frontend, no React in this repository |
| `env-shielding-auditor` | No new secret surface: the sprint adds no credential path and reads no `.env` (`RA-09`) |

## Forge decision (P3 trail)

**No skill was forged**, and the ladder was walked before concluding it:

1. **P1 — existing local skills**: `python-quality-auditor` and
   `readme-standardizer` already cover the quality and documentation surface.
2. **P2 — a script instead of a skill**: W1 is a one-shot DOM probe run manually
   under operator supervision, once. `rules/skills_and_integrations.md` reserves
   the Three-File Standard for reusable capability; a single-use probe is a
   script in `scripts/`, and forging a skill around it would be scaffolding noise
   (`three_file_standard` prohibits exactly this padding).
3. **P3 — third-party search**: not run. The capability needed is reading a
   specific WhatsApp Web DOM marker, which is inherently project-specific; no
   general skill can encode a private third party's markup, and `KI-004-A`
   forbids adopting anyone's assumption about it in place of a measurement.
