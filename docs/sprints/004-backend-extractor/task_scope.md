# Task Scope — Sprint 004 (`backend-extractor` / P2)

**Branch**: `ai-sprint/004` · **Base**: `main` at `b090ed3`
**Plan**: `docs/sprints/004-backend-extractor/IMPLEMENTATION_PLAN.md`
**Phase**: 5 sealed (approved 2026-08-29) → Phase 6 Execution

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
| W0 | `docs/sprints/004-backend-extractor/IMPLEMENTATION_PLAN.md` | create | low | `doc_orchestrator` | session | high | ✅ `b0747b1` |
| W1 | `src/whatsapp_chat_extractor/history.py` | create | medium | `implementer_agent` | session | high | ✅ `5cf5a6a` |
| W2 | `src/whatsapp_chat_extractor/export_one.py` | modify | high | `implementer_agent` | session | high | ✅ `dba1c08` |
| W3 | `src/whatsapp_chat_extractor/writers.py` | modify | low | `implementer_agent` | session | high | ✅ `96eeef7` |
| W4 | `src/whatsapp_chat_extractor/__main__.py` | modify | low | `implementer_agent` | session | high | ✅ `6a745b8` |
| W5 | `tests/test_history.py` | create | low | `implementer_agent` | session | high | ✅ `b58735d` |
| W6 | `tests/test_writers.py` | modify | low | `implementer_agent` | session | high | ✅ `1a9fc37` |
| W7 | `.claude/commands/wa-export.md` | create | low | `skill_architect` | session | high | ✅ `71456f6` |
| W8 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | session | high | ✅ `e1a644e` |
| W9 | `CHANGELOG.md` | modify | low | `doc_orchestrator` | session | N/A | ✅ `ac0eae9` |
| W10 | `.ruff.toml` (+ `pyproject.toml`) | create | low | `implementer_agent` | session | N/A | ✅ `6b8db5e` |
| W11 | `docs/walkthroughs/EXTRACTOR_WALKTHROUGH.md` | modify | low | `doc_orchestrator` | session | high | ✅ `9f1667b` |

Note: Writes performed by sequential Cursor session; assignees name the
Write-capable profile for `check_task_scope.py`. W0 was first attributed to
`principal_agent`, which holds no `Write`/`Edit`; `check_task_scope.py` rejected
it and the plan artifact is recorded against `doc_orchestrator`.

### Units added during execution (not in the approved Work table)

| # | Why it was not foreseen |
| :--- | :--- |
| W10 | The plan's own `ruff check .` reported on the `.agents` submodule, whose lint debt `strict_rule` forbids this host from fixing. Config moved to `.ruff.toml` because a `[tool.*]` key added to `pyproject.toml` trips the commit gate's dependency detector (`UPSTREAM_FINDING_005`). |
| W11 | Declared in the plan's Documentary impact table but omitted from the Work table. |

---

## Isolation notes

- One physical file per implementer task unit.
- W1 must land before W2: the harvest loop owns the iteration, `export_one.py`
  keeps only single-pass primitives. Editing both in one commit would put the
  loop in two places.
- Live WhatsApp Web only on the operator Mac; tests use synthetic pass sequences
  and never open a browser.
- Customer exports stay under gitignored `data/`.
- No writes inside `.agents/` (`agents.md §3 strict_rule`). The framework defect
  found at session start is recorded at
  `docs/audits/UPSTREAM_FINDING_004_SESSION_START_BOOT_ROOT.md` and travels
  upstream from a separate clone.
