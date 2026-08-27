# Implementation Plan: Sprint 002 — docs-structure (P0)

**Canonical path**: `docs/sprints/002-docs-structure/IMPLEMENTATION_PLAN.md`
**Branch**: `ai-sprint/002` · **Base**: `main` at `805b13039cad5693ca0b5e60f1e353b2b61d2a96`
**Status**: `APPROVED`

> Spanish permitted (`agents.md §1 user_chat`). Program phases: ADR-0002.

---

## Context

El debate en chat (Sprint 002) aclaró el producto y la forma de desarrollarlo.
Este sprint es **P0**: dejar eso escrito (ADRs, overview, roadmap). **Sin código
de extracción.** El spike Web es Sprint 003 (P1).

| Figura | Valor | Reproduce |
| :--- | :--- | :--- |
| Base SHA | `805b130…` | `git merge-base main HEAD` / plan base |
| ADRs | `ADR-0001`, `ADR-0002` | `ls docs/decisions/ADR-000*.md` |

---

## Design

| Decision | Choice | Rejected |
| :--- | :--- | :--- |
| Alcance #002 | **P0 documentación** (ADRs + overview + roadmap + gitignore `data/`) | Implementar Playwright / volcado en #002 |
| Producto | ADR-0001 (Web, un número, historial texto, Cursor+scripts, JSON gitignored) | Business API; análisis/bot en este repo |
| Entrega | ADR-0002 fases P0→P3 + layout `src/` + `data/` | Scaffold completo antes del spike |
| Approval | Chat debate primero; plan se aprueba **después** de redactar | Ejecutar spike sin ADR |

---

## Work

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| W1 | `docs/decisions/ADR-0001-product-scope-whatsapp-web.md` | create | medium | session | ✅ |
| W2 | `docs/decisions/ADR-0002-delivery-program-and-layout.md` | create | medium | session | ✅ |
| W3 | `docs/roadmaps/docs/extractor/002-delivery-program.md` | create | low | session | ✅ |
| W4 | `docs/0_SYSTEM_OVERVIEW.md` | modify | medium | session | ✅ |
| W5 | `docs/roadmaps/docs/onboarding/001-greenfield-adoption.md` | modify | low | session | ✅ |
| W6 | `.gitignore` | modify (`data/`) | low | session | ✅ |
| W7 | `docs/sprints/002-docs-structure/IMPLEMENTATION_PLAN.md` | replace (this plan) | low | session | ✅ |
| W8 | `docs/active_state.json` | modify topology / gaps | low | session | ✅ |

---

## Dependencies

None

---

## Mechanisms

| Mechanism | Deterministic or agent judgment | Invoker |
| :--- | :--- | :--- |
| ADR / roadmap authoring | agent (one-shot from chat debate) | this plan |
| Spike / Playwright | deferred to Sprint 003 | ADR-0002 P1 |

---

## Cost

| Field | Value | Reproduce |
| :--- | :--- | :--- |
| Delegation | `sequential` | `docs/active_state.json` |
| Work units | 8 | Count Work rows |
| Subagents dispatched | `0` | Cursor sequential |
| Prior session ratio | n/a | — |

---

## Tests

| Check | Fails against current tree? |
| :--- | :--- |
| ADR-0001 and ADR-0002 exist and Status Accepted | **Yes** until committed |
| Overview links both ADRs and no longer says shape deferred to 002+ | **Yes** until overview update lands |
| `.gitignore` contains `data/` | **Yes** until W6 |
| No Playwright/product `src/` introduced in #002 | **No** — protect |

---

## Verification

| Command | Expected |
| :--- | :--- |
| `test -f docs/decisions/ADR-0001-product-scope-whatsapp-web.md && test -f docs/decisions/ADR-0002-delivery-program-and-layout.md && echo OK` | `OK` |
| `rg -n "ADR-0001|ADR-0002|WhatsApp Web" docs/0_SYSTEM_OVERVIEW.md` | Links + Web in Level 1/2 |
| `rg -n '^data/' .gitignore` | Match |
| `git -C .agents status --porcelain` | vacío |
| `test ! -d src/whatsapp_chat_extractor && echo no_src_ok` | `no_src_ok` |

---

## Documentary impact (T5)

| Artefacto | Qué cambia |
| :--- | :--- |
| `docs/decisions/ADR-0001-product-scope-whatsapp-web.md` | Producto |
| `docs/decisions/ADR-0002-delivery-program-and-layout.md` | Fases + layout |
| `docs/roadmaps/docs/extractor/002-delivery-program.md` | Plan de proyecto P0–P3 |
| `docs/0_SYSTEM_OVERVIEW.md` | Level 1–2 + topology |
| `docs/roadmaps/docs/onboarding/001-greenfield-adoption.md` | Puntero a programa extractor |
| `.gitignore` | `data/` |
| `docs/sprints/002-docs-structure/IMPLEMENTATION_PLAN.md` | Este plan P0 |
| `CHANGELOG.md` | Entrada #002 al close |

---

## Out of scope

| Exclusion | Destination |
| :--- | :--- |
| Spike Playwright / un chat | Sprint 003 (P1) |
| Skill Cursor de volcado | Sprint 004 (P2) |
| Historial completo robusto | Sprint 005+ (P3) |
| Sentimiento / bot / learning server | Fuera de repo (ADR-0001) |

---

## Acceptance (medible)

- [x] ADR-0001 y ADR-0002 Accepted en `docs/decisions/`
- [x] Roadmap de programa lista P0–P3
- [x] Overview alineado; debate “deferred to 002+” cerrado
- [x] `data/` en `.gitignore`
- [x] Sin `src/` de producto en este sprint
- [x] Human OK sobre este plan (Approval Gate)

---

## Abort criterion

Si Gustavo rechaza Web o el split Cursor+scripts, superseder ADR-0001 antes de abrir Sprint 003; no empezar el spike.

---

## Approval — `triple_lock` lock 1

| Field | Value |
| :--- | :--- |
| **Approved by** | Gustavo |
| **Date** | 2026-08-27 |
| **Plan commit at approval** | `5578cbe` (P0 seal) · tip at approval turn `61790d8` |
| **Remaining locks** | Active Sprint · QA + Tester · Human OK at close |

**Phase 5 Approval Gate:** OK explícito de Gustavo (2026-08-27) — P0 ADRs + plan de proyecto por fases.
