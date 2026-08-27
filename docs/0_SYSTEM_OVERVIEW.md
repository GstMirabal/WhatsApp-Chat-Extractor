# System Overview: WhatsApp Chat Extractor
**Last Audit Sprint**: #002
**Last Audit Date**: 2026-08-27
**Last Audit Commit SHA**: `5578cbe`

This is the **Documentation Entry Point**. `agents.md §0 (Entry Point)` requires every session to read this file before anything else. It is intentionally short — for the full component inventory, see `.agents/docs/architecture/topology_map.md`.

**Decisions:** [ADR-0001](decisions/ADR-0001-product-scope-whatsapp-web.md) (product) · [ADR-0002](decisions/ADR-0002-delivery-program-and-layout.md) (delivery + layout)  
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

Component-level (Level 3) stays advisory until `code_containers` are declared when `src/` exists.

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
| `data/` | Export JSON (gitignored) | Ignore rule in #002; writes from #003+ |
| `src/whatsapp_chat_extractor/` | Playwright/Web export package | Planned #003+ |
| `tests/` | Pytest | Planned #003+ |
| `pyproject.toml` | Packaging / CLI for scripts | Planned #003+ |
| `docs/decisions/ADR-0001-*.md` | Product scope | Present (#002) |
| `docs/decisions/ADR-0002-*.md` | Delivery + layout | Present (#002) |
| `docs/` / `.agents/` | Docs + framework | Present |

Framework map: `.agents/docs/architecture/topology_map.md`.
