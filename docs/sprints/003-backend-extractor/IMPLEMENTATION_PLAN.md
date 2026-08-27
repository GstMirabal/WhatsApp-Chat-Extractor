# Implementation Plan: Sprint 003 — backend-extractor (P1 spike)

**Canonical path**: `docs/sprints/003-backend-extractor/IMPLEMENTATION_PLAN.md`
**Branch**: `ai-sprint/003` · **Base**: `main` at `88d337cad4d87288112dc4d93abbc98e97aa614a` (v0.2.0)
**Status**: `APPROVED`

> Spanish permitted (`agents.md §1 user_chat`). Program phase: ADR-0002 §2.1 P1.

---

## Context

P0 (#002) sealed product (ADR-0001) and delivery/layout (ADR-0002). This sprint is
**P1**: prove WhatsApp Web export on the Mac for **one** chat → text JSON in
`data/`, with a minimal Python/Playwright package and BLUEPRINT. No Cursor dump
skill (that is P2 / #004).

| Figura | Valor | Reproduce |
| :--- | :--- | :--- |
| Base SHA | `88d337c…` | `git rev-parse HEAD` at branch create / `last_close_commit` |
| Exit criterion | QR/session → one chat → JSON file; blocker notes | ADR-0002 §2.1 P1 |
| Gaps | BLUEPRINT + Web spike + `code_containers` when `src/` exists | `docs/active_state.json` `acknowledged_gaps` |

---

## Design

| Decision | Choice | Rejected |
| :--- | :--- | :--- |
| Alcance #003 | **Spike mínimo**: package + Playwright + un chat → JSON | Scaffold “completo” o skill Cursor (P2) |
| Layout | `src/whatsapp_chat_extractor/`, `tests/`, `pyproject.toml`; writes en `data/` | `extractor/` en root (ADR-0002 opción C) |
| Runtime | Playwright Python; **Chromium embebido** (default Playwright) | Chrome del sistema como requisito |
| Sesión | Perfil de browser **persistente** local (reuso post-QR), path gitignored | Login QR en cada run |
| Selección del chat | **Humano elige** (nombre/URL/índice) en el spike | “Primer chat” sin confirmación |
| JSON mínimo | `chat_id`/`title`, mensajes `{sender, timestamp, body, order}` — solo texto | Media, reacciones, estados de entrega |
| CI | Pytest + fixtures JSON; **cero** WhatsApp live en CI | E2E WA en GitHub Actions |
| Docs | `docs/architecture/EXTRACTOR_BLUEPRINT.md` + overview/roadmap/ancla + `SPIKE_NOTES.md` | Diferir BLUEPRINT |
| Pin `.agents` | Chore atómico **antes** de commits de producto Playwright | Mezclar pin bump con código del spike |

---

## Work

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| W0 | `.agents` gitlink | pin v4.23.0 (chore, separate commit) | low | session | ✅ `d1a68cf` |
| W1 | `pyproject.toml` | create (pkg, CLI, playwright, pytest) | medium | implementer / session | ✅ |
| W2 | `src/whatsapp_chat_extractor/__init__.py` | create | low | implementer / session | ✅ |
| W3 | `src/whatsapp_chat_extractor/session.py` | create (browser + wait QR/ready) | high | implementer / session | ✅ |
| W4 | `src/whatsapp_chat_extractor/export_one.py` | create (abrir 1 chat + scroll texto) | high | implementer / session | ✅ |
| W5 | `src/whatsapp_chat_extractor/writers.py` | create (JSON → `data/`) | medium | implementer / session | ✅ |
| W6 | `src/whatsapp_chat_extractor/__main__.py` | create (entry: login / export-one) | medium | implementer / session | ✅ |
| W7 | `tests/test_writers.py` (+ fixture) | create | low | implementer / session | ✅ |
| W8 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | create | medium | doc_orchestrator / session | ✅ |
| W9 | `docs/sprints/003-backend-extractor/SPIKE_NOTES.md` | create (bloqueos, selectores, ToS) | medium | session | ✅ |
| W10 | `docs/0_SYSTEM_OVERVIEW.md` | modify (estado #003, audit stamp) | low | session | ✅ |
| W11 | `docs/roadmaps/docs/extractor/002-delivery-program.md` | modify (P1 → IN_PROGRESS; CLOSED al cierre) | low | session | ✅ |
| W12 | `docs/active_state.json` | modify (`current_sprint` 003, `code_containers` tras `src/`, gaps, topology) | low | topology_mapper / session | ✅ |
| W13 | `docs/sprints/003-backend-extractor/IMPLEMENTATION_PLAN.md` | create (this plan) | low | session | ✅ |
| W14 | sprint scaffold (`SPRINT_LOG`, `task_scope`, assignments) | create | low | session | pending |

---

## Dependencies

| Package | Why |
| :--- | :--- |
| `playwright` | Browser control for WhatsApp Web (stdlib insufficient) |
| `pytest` | Local/CI suite with fixtures |

---

## Mechanisms

| Mechanism | Deterministic or agent judgment | Invoker |
| :--- | :--- | :--- |
| Playwright session + export | agent (selectors / waits) + scripts | this plan W3–W6 |
| Writers + pytest fixtures | deterministic | this plan W5, W7 |
| Spike abort (≤2 documented attempts) | human + evidence in `SPIKE_NOTES.md` | Design / Abort |

---

## Cost

| Field | Value | Reproduce |
| :--- | :--- | :--- |
| Delegation | `sequential` | `docs/active_state.json` `delegation_mode` |
| Work units | 15 (W0–W14) | Count Work rows |
| Subagents dispatched | `0` | Cursor sequential |
| Prior session ratio | n/a | Cursor — no Claude jsonl |

---

## Tests

| Check | Fails against current tree? |
| :--- | :--- |
| `src/whatsapp_chat_extractor/` + `pyproject.toml` exist | **Yes** until W1–W2 |
| `python -m pytest tests/ -q` exit 0 without live WA | **Yes** until W7 |
| Manual CLI → QR → one chat → `data/*.json` | **Yes** until W3–W6 + operator run |
| `docs/architecture/EXTRACTOR_BLUEPRINT.md` exists | **Yes** until W8 |
| `code_containers` with `root: src/` only after `src/` exists | **Yes** until W12 post-scaffold |
| No Cursor dump skill / no sentiment code | **No** — protect (out of scope) |

---

## Verification

| Command | Expected |
| :--- | :--- |
| `test -d src/whatsapp_chat_extractor && test -f pyproject.toml && echo OK` | `OK` |
| `python -m pytest tests/ -q` | exit 0 |
| Manual path documented in `SPIKE_NOTES.md` | JSON under `data/`; blockers recorded |
| `test -f docs/architecture/EXTRACTOR_BLUEPRINT.md && echo OK` | `OK` |
| `rg -n 'code_containers' docs/active_state.json` | Present after `src/` exists |
| `git -C .agents status --porcelain` | vacío al close |

---

## Documentary impact (T5)

| Artefacto | Qué cambia |
| :--- | :--- |
| `pyproject.toml` + `src/whatsapp_chat_extractor/*` | Package + CLI spike |
| `tests/test_writers.py` (+ fixtures) | Offline verification |
| `docs/architecture/EXTRACTOR_BLUEPRINT.md` | Reference (Diátaxis) for extractor |
| `docs/sprints/003-backend-extractor/SPIKE_NOTES.md` | Spike evidence / blockers / ToS notes |
| `docs/0_SYSTEM_OVERVIEW.md` | Audit stamp + P1 status |
| `docs/roadmaps/docs/extractor/002-delivery-program.md` | P1 status |
| `docs/active_state.json` | Sprint 003 + topology + containers |
| `docs/sprints/003-backend-extractor/IMPLEMENTATION_PLAN.md` | Este plan |
| `CHANGELOG.md` | Entrada #003 al close |

---

## Out of scope

| Exclusion | Destination |
| :--- | :--- |
| Todos los chats / historial completo robusto | P3 (#005+) |
| Comando/skill Cursor “run dump” | P2 (#004) |
| Sentiment / bot / learning | fuera de repo (ADR-0001) |
| Media files | nuevo ADR si hace falta |
| WhatsApp Business API | rechazado ADR-0001 |

---

## Acceptance (medible)

- [ ] Package + Playwright path: session → one human-selected chat → text JSON in `data/`
- [ ] `SPIKE_NOTES.md` records result (or abort evidence)
- [ ] `EXTRACTOR_BLUEPRINT.md` exists; BLUEPRINT gap cleared or updated
- [ ] `python -m pytest tests/ -q` exit 0 (no live WA)
- [ ] `code_containers` declared once `src/` exists
- [ ] Human OK on this plan (Approval Gate) — **done 2026-08-27**
- [ ] Human OK at close (remaining triple_lock)

---

## Abort criterion

Si en **≤2 sesiones de intento documentadas** no se completa QR → un chat → JSON
(UI irreconocible, ban/ToS que Gustavo corte, o Playwright no controla WA Web de
forma reproducible), **se aborta el sprint de producto**, se deja evidencia en
`SPIKE_NOTES.md`, y **no** se abre inversión P2 hasta un ADR que superseda o un
plan B.

---

## Approval — `triple_lock` lock 1

| Field | Value |
| :--- | :--- |
| **Approved by** | Gustavo |
| **Date** | 2026-08-27 |
| **Plan commit at approval** | `0fb2e70` |
| **Remaining locks** | Active Sprint · QA + Tester · Human OK at close |

**Phase 5 Approval Gate:** OK explícito de Gustavo (2026-08-27) — P1 spike plan
(`backend-extractor`), rama `ai-sprint/003`, defaults: perfil persistente,
Chromium embebido, `EXTRACTOR_BLUEPRINT.md`.
