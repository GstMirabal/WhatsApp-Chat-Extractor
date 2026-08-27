# System Overview: WhatsApp Chat Extractor
**Last Audit Sprint**: #001
**Last Audit Date**: 2026-08-27
**Last Audit Commit SHA**: 

This is the **Documentation Entry Point**. `agents.md §0 (Entry Point)` requires every session to read this file before anything else. It is intentionally short — for the full component inventory, see `.agents/docs/architecture/topology_map.md`.

---

## 1. What this is

**WhatsApp Chat Extractor** extracts all chats from a WhatsApp account so they can be analyzed later with AI.

This repository uses the **Token-Optimized Agent Pipeline (`.agents`)** framework as a git submodule: a governance layer that determines how AI subagents plan, execute, and hand off work here.

## 2. Architecture at a glance (C4 Level 1-2)

**Level 1 — Context**: personal/business WhatsApp history in → structured corpus out → AI analysis consumers.

```
[WhatsApp account history]
        |
        v
[WhatsApp Chat Extractor] -----> [AI analysis tooling / notebooks / services]
        |
        v
[Structured export: JSON / JSONL (+ optional media refs)]
```

**Level 2 — Container** (provisional — product shape debate deferred to Sprint 002+):

```
Recommended direction (not implemented in #001):
  [Python CLI extractor] -> [local corpus store] -> [optional HTTP API later]
```

Component-level (Level 3) detail is deferred until `code_containers` are declared and application modules exist (`rules/documentation_standard.md §2.1`).

## 3. The governance hierarchy
| Layer | Location | Role |
| :--- | :--- | :--- |
| **Governance Rules** | `.agents/agents.md` | The absolute, transversal rules. Nothing overrides this. |
| **Rules** | `.agents/rules/*.md` | Domain-specific standards (QA, topology, skills, security, documentation). |
| **Workflows** | `.agents/workflows/*.md` | Step-by-step protocols, invoked as `/agents:<name>` slash commands. |
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
- `.agents/docs/` — the framework's own (separate) self-documentation; not this project's (its changelog is `.agents/CHANGELOG.md`, a different jurisdiction).

## 6. Full inventory
For the detailed framework component map, read `.agents/docs/architecture/topology_map.md`.
Host application topology will be recorded here after the Sprint 002+ structure debate.
