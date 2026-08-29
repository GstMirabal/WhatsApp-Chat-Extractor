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
| W0 | `docs/sprints/004-backend-extractor/IMPLEMENTATION_PLAN.md` | create | low | `principal_agent` | session | high | ⏳ |
| W1 | `src/whatsapp_chat_extractor/history.py` | create | medium | `implementer_agent` | session | high | ⏳ |
| W2 | `src/whatsapp_chat_extractor/export_one.py` | modify | high | `implementer_agent` | session | high | ⏳ |
| W3 | `src/whatsapp_chat_extractor/writers.py` | modify | low | `implementer_agent` | session | high | ⏳ |
| W4 | `src/whatsapp_chat_extractor/__main__.py` | modify | low | `implementer_agent` | session | high | ⏳ |
| W5 | `tests/test_history.py` | create | low | `implementer_agent` | session | high | ⏳ |
| W6 | `tests/test_writers.py` | modify | low | `implementer_agent` | session | high | ⏳ |
| W7 | `.claude/commands/wa-export.md` | create | low | `skill_architect` | session | high | ⏳ |
| W8 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | session | high | ⏳ |
| W9 | `CHANGELOG.md` | modify | low | `doc_orchestrator` | session | N/A | ⏳ |

Note: Writes performed by sequential Cursor session; assignees name the
Write-capable profile for `check_task_scope.py`.

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
