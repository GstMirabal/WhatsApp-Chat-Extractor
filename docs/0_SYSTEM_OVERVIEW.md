# System Overview: WhatsApp Chat Extractor
**Last Audit Sprint**: #006
**Last Audit Date**: 2026-08-31
**Last Audit Commit SHA**: `a62a34e`

This is the **Documentation Entry Point**. `agents.md §0 (Entry Point)` requires every session to read this file before anything else. It is intentionally short — for the full component inventory, see `.agents/docs/architecture/topology_map.md`.

**Decisions:** [ADR-0001](decisions/ADR-0001-product-scope-whatsapp-web.md) (product) · [ADR-0002](decisions/ADR-0002-delivery-program-and-layout.md) (delivery + layout) · [ADR-0003](decisions/ADR-0003-media-placeholders-in-export.md) (media placeholders)  
**Released:** `v0.4.0` — full-history export, pseudonymous JSON. **Next:** Sprint 005 (P2.5), plan in `DRAFT`; resume from [RESUME_NOTES.md](sprints/005-backend-extractor/RESUME_NOTES.md)  
**Blueprint:** [EXTRACTOR_BLUEPRINT.md](architecture/EXTRACTOR_BLUEPRINT.md)  
**Program roadmap:** [docs/roadmaps/docs/extractor/002-delivery-program.md](roadmaps/docs/extractor/002-delivery-program.md)

---

## 1. What this is

**WhatsApp Chat Extractor** produces a **text JSON dump** of customer-support chats from **one** business WhatsApp number, taken via **WhatsApp Web**, so a **separate** AI pipeline can later study requests, behaviour, and sentiment for a care bot.

This repository does **not** implement sentiment analysis, the learning server, or the bot.

Governance: Token-Optimized Agent Pipeline (`.agents` submodule).

## 2. Architecture at a glance (C4 Level 1-2)

**Level 1 — Context**

```
[WhatsApp Web — one business number]
        |
        v
[WhatsApp Chat Extractor]  (Cursor agent + scripts, Mac, manual)
        |
        v
[data/*.json — gitignored]
        |
        v
[External AI / learning / bot — out of this repo]
```

**Level 2 — Container** (per ADR-0001 / ADR-0002; code dirs from Sprint 003+)

```
[Cursor agent session] ---> [Export scripts: src/whatsapp_chat_extractor/]
        |                              |
        | (QR / confirm)               v
        +---------------------> [Playwright → WhatsApp Web]
                                       |
                                       v
                              [Local corpus: data/ (gitignored)]
```

Component-level (Level 3) stays advisory until density history exists; `code_containers` declared for `src/` in Sprint 003.

## 3. The governance hierarchy
| Layer | Location | Role |
| :--- | :--- | :--- |
| **Governance Rules** | `.agents/agents.md` | The absolute, transversal rules. Nothing overrides this. |
| **Rules** | `.agents/rules/*.md` | Domain-specific standards (QA, topology, skills, security, documentation). |
| **Workflows** | `.agents/workflows/*.md` | Step-by-step protocols, invoked as `/agents:*` slash commands. |
| **Subagents** | `.agents/agents/*.md` | The roles that execute workflow steps (Principal, Orchestrator, QA, Tester, etc.). |
| **Skills** | `.agents/skills/*/` | Concrete tools subagents call into (linters, scaffolders, auditors). |

## 4. How a session starts
Run `/agents:start`. It will:
1. Read `agents.md` and this file (Zero-Memory anchor).
2. Install/verify the Cursor/Claude bridge if not already done.
3. Claim the host session lock in `docs/active_state.json`.
4. Hand off to the Principal Agent for Planning.

## 5. Where state lives
- `docs/active_state.json` — this project's own session anchor (host-specific).
- `CHANGELOG.md` (root) — the **Master Ledger**: sprint entries at close, version seals at deployment.
- `docs/roadmaps/`, `docs/sprints/` — this project's own historical record.
- `data/` — export JSON (**gitignored**; never commit customer chats).
- `.agents/docs/` — the framework's own (separate) self-documentation; not this project's (its changelog is `.agents/CHANGELOG.md`, a different jurisdiction).

## 6. Host application topology

| Path | Role | Status |
| :--- | :--- | :--- |
| `data/` | Export JSON + browser profile (gitignored) | Writes from #003 |
| `src/whatsapp_chat_extractor/` | Playwright/Web export package | Present (#003) |
| `tests/` | Pytest (fixtures; no live WA) | Present (#003) |
| `pyproject.toml` | Packaging / CLI `wa-extract` | Present (#003) |
| `docs/architecture/EXTRACTOR_BLUEPRINT.md` | Extractor reference | Present (#003) |
| `docs/decisions/ADR-0001-*.md` | Product scope | Present (#002) |
| `docs/decisions/ADR-0002-*.md` | Delivery + layout | Present (#002) |
| `docs/decisions/ADR-0003-*.md` | Media placeholders (supersedes ADR-0001 coverage) | Present (#005) |
| `.github/workflows/ci.yml` | ruff, pytest, no-committed-chats guard | Present (#004), not executing — billing |
| `docs/PLATFORM_HARDENING.md` | Controls pending a public repository | Present (#004) |
| `docs/` / `.agents/` | Docs + framework | Present |

Framework map: `.agents/docs/architecture/topology_map.md`.
