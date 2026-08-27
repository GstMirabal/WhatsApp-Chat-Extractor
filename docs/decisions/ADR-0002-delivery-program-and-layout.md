# ADR-0002: Delivery program and host layout
**Status**: `Accepted`
**Date**: 2026-08-27
**Triggers**: 2, 4 (`rules/documentation_standard.md §3.1`)

---

## 1. Context

ADR-0001 fixed **what** the product does. This ADR fixes **how we deliver it**
and **where files live** in the host repo, so later sprints do not reopen
topology while building the spike and the Cursor-orchestrated export.

WhatsApp Web automation is high risk: a full scaffold without a proven export of
even one chat wastes sprints. The delivery program is therefore phased:
document → spike → happy path → harden. Analysis/bot remain outside this repo.

## 2. Decision

### 2.1 Delivery phases (project plan)

| Phase | Sprint (planned) | Goal | Exit criterion |
| :--- | :--- | :--- | :--- |
| **P0 — Seal decisions** | **002** (this) | ADRs + overview + roadmap written from the chat debate | ADR-0001/0002 Accepted; overview Level 2 matches; roadmap lists phases |
| **P1 — Spike** | **003** | Prove Web export on the Mac for **one** chat → text JSON in `data/` | Scripted path: session (QR) → one chat → JSON file; notes on blockers |
| **P2 — Happy path** | **004** | Cursor agent command/skill + scripts for a usable dump | Agent can orchestrate a dump; scripts do browser/traverse/write; human only for QR/confirm |
| **P3 — Harden** | **005+** | Full history across chats, scroll/retry, partial-failure reporting | Documented limits; dump covers all chats textually within agreed failure policy |
| **P4 — Consumers** | **out of repo** | Sentiment / solicitudes / learning server / bot | Separate project(s) reading `data/` JSON — not built here |

Phase numbering is the program order. Sprint IDs may slip, but **P1 must not be
skipped** before large P2 investment.

### 2.2 Host layout (create dirs when the owning phase needs them)

| Path | Role | When |
| :--- | :--- | :--- |
| `data/` | Export JSON (and local run artifacts). **gitignored** | P0: ignore rule; P1+: writes |
| `data/.gitkeep` | **Not used** — entire `data/` ignored so customer data cannot be committed by mistake | — |
| `src/whatsapp_chat_extractor/` | Python package: Playwright/Web automation + export writers | P1 scaffold |
| `tests/` | Pytest for scripts/package (fixtures; no live WA in CI by default) | P1+ |
| `pyproject.toml` | Packaging, CLI entrypoints invoked by the agent/scripts | P1 |
| `.cursor/commands/` or project skill | Cursor entry (“run dump”) that orchestrates scripts | P2 |
| `docs/` | Host docs, ADRs, sprints (already present) | — |
| `.agents/` | Framework submodule (already present) | — |

### 2.3 `code_containers`

Do **not** declare `code_containers` until `src/` exists on disk (P1). Intended
declaration:

```json
"code_containers": [
  {"stack": "backend", "root": "src/"}
]
```

### 2.4 Runtime tooling (intent for P1+)

- **Playwright** (Python) for WhatsApp Web browser control.
- Agent calls **deterministic scripts** (via package CLI or `python -m …`); it
  does not scrape the DOM itself when a script exists.

## 3. Consequences

| Easier | Harder |
| :--- | :--- |
| P1 kill-switch if Web automation is unusable | Full dump delayed until P3 |
| Clear folder ownership for exports vs code | `data/` never in git → backups are the operator's problem |
| Matches ADR-0001 Cursor + scripts split | Playwright + WA Web still a hard external dependency |

## 4. Deciders

Gustavo (product owner) · Sprint 002 chat (“plan de proyecto por fases”) · session documentation

## 5. Considered Options

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **A — Phased: document → spike → happy path → harden (chosen)** | De-risks Web; matches operator intent | Longer calendar before “all chats” |
| **B — Scaffold full app then integrate Web** | Feels productive early | High chance of wrong structure if spike fails |
| **C — Flat `extractor/` at repo root** | Shorter paths | Crowds root next to `docs/` / `.agents/` |
| **D — Monorepo apps/packages from day one** | Future API-ready | Overbuilt for a single Mac dump tool |
| **E — Commit exports under `data/` tracked** | Easy share | Leaks customer chat history — rejected |

---
*Immutable once Accepted — a changed decision gets a new ADR that supersedes this one, never an in-place edit (`rules/documentation_standard.md §3`). File lives at `docs/decisions/ADR-0002-delivery-program-and-layout.md`.*
