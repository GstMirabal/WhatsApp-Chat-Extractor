# Implementation Plan: Sprint 001 — docs-onboarding

**Canonical path**: `docs/sprints/001-docs-onboarding/IMPLEMENTATION_PLAN.md`
**Branch**: `ai-sprint/001` · **Base**: `main` at `2336a6e0a735a7788a97d2eaa7525ff7d90c9b18`
**Status**: `APPROVED`

> Authored at Phase 1 (Planning) by `principal_agent`, extracted to this path at
> Phase 3, and **committed before Phase 5 approves it**: `agents.md §2 triple_lock`
> names the approved Implementation Plan as its first lock, and a lock cannot close
> over an artifact that does not exist.
>
> Spanish is permitted in this document (`agents.md §1 user_chat`). Every other
> pipeline artifact is English.

---

## Context

El host adoptó Token-Optimized Agent Pipeline `v4.22.0` (submódulo `.agents`) sin
árbol `docs/`, sin Master Ledger y sin ancla de sesión en el host. El producto
objetivo (acordado en Planning) es **extraer todos los chats de una cuenta de
WhatsApp para análisis posterior con IA**; la forma de la API y la estructura de
código se posponen a un debate en Sprint 002+.

Al cerrar este sprint deben existir: topología `docs/` mínima, `docs/0_SYSTEM_OVERVIEW.md`,
`docs/active_state.json` (host), `CHANGELOG.md` en la raíz, y este plan en la ruta canónica.
Sin código de aplicación.

---

## Design

| Decision | Choice | Rejected |
| :--- | :--- | :--- |
| Onboarding scenario | **A — Greenfield** | B (no hay legado agentic previo; solo bridge fresco) / C (no hay codebase) |
| Sprint 001 scope | Docs + ledger + host anchor only | Features de extracción / API |
| Runtime recommendation (producto, no este sprint) | **Python CLI** como núcleo de extracción → JSON/JSONL; API HTTP después | Empezar por API sin corpus local; scrapear WhatsApp Web como camino primario |
| `code_containers` | **Omitido** (Level 3 advisory) | Declarar roots inexistentes |
| Stack/Layer folder | `docs` / `onboarding` | Inventar stacks backend/frontend antes del debate |

---

## Work

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `docs/sprints/001-docs-onboarding/IMPLEMENTATION_PLAN.md` | create | low | `principal_agent` / session | ✅ |
| 2 | `docs/` tree (`architecture/`, `roadmaps/docs/onboarding/`, `walkthroughs/`, `sprints/`, `contracts/`, `decisions/`, `audits/`, `guides/`) | create | low | `topology_mapper` / session | ✅ |
| 3 | `docs/0_SYSTEM_OVERVIEW.md` | create from template | low | `doc_orchestrator` / session | ✅ |
| 4 | `docs/active_state.json` | create host anchor + claim | low | `topology_mapper` / session | ✅ |
| 5 | `CHANGELOG.md` | create Master Ledger (Scenario A seed) | low | session | ✅ |
| 6 | `identity.config.json` | fill from Planning answers + git identity | low | session | ✅ |
| 7 | Verify `main` exists + `.gitignore` present | verify | low | `git_sync_agent` | ✅ |

---

## Dependencies

None

---

## Mechanisms

| Mechanism | Deterministic or agent judgment | Invoker (`RA-16`) |
| :--- | :--- | :--- |
| Host docs scaffold | agent (one-shot greenfield) | this plan / `topology-scaffolder` skill |
| Session claim on host anchor | script | `python3 .agents/scripts/session_state.py claim --tool cursor` (cwd = host root) |

---

## Risks

| Risk | Mitigation |
| :--- | :--- |
| Claim pollution under `.agents/docs/` if boot runs with nucleus cwd | Claim only from host root after host `docs/active_state.json` exists; keep `git -C .agents status --porcelain` empty |
| Product scope creep into 001 | Explicit non-goals below; API/structure debate deferred to 002+ |

---

## Explicit non-goals

- Extracción WhatsApp, parsers, backups, media
- Diseño o implementación de API HTTP
- Declaración de `code_containers`
- Blueprints de módulos de aplicación / `/agents:revdoc`
- Commits de producto fuera del ledger de onboarding

---

## Acceptance

- [x] `docs/0_SYSTEM_OVERVIEW.md` present and readable as Documentation Entry Point
- [x] Host `docs/active_state.json` exists with `current_sprint.id = 1`, `session_tool = cursor`
- [x] Host `CHANGELOG.md` seeded with Adopted pipeline v4.22.0 (Scenario A)
- [x] Canonical plan path exists on `ai-sprint/001`
- [x] `git -C .agents status --porcelain` is empty
- [x] No application source introduced in this sprint

---

## Human approval

- **Scope OK (docs-only 001):** Gustavo, 2026-08-27 — product goal stated; API/structure debate deferred.
- **Phase 5 Approval Gate:** approved for execution of the Work table above (scaffold only).
