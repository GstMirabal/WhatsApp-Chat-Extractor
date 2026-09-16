# System Overview: WhatsApp Chat Extractor
**Last Audit Sprint**: #012
**Last Audit Date**: 2026-09-16
**Last Audit Commit SHA**: `5cc95b7` (`ai-sprint/012` tip; `main` is at `6259d5e`, sealed `v0.10.0`)

This is the **Documentation Entry Point**. `agents.md §0 (Entry Point)` requires every session to read this file before anything else. It is intentionally short — for the full component inventory, see `.agents/docs/architecture/topology_map.md`.

**Note on staleness (found and corrected 2026-09-15):** this anchor's header still named Sprint #008/`v0.8.1` after Sprints 009, 010 and 011 had each closed and each touched structure — three sprints of drift against `close_workflow.md` Phase 2 `history_sync`. Sprint 009 closed with the append-only run journal, `--resume`/`recover` and corpus contract v6; Sprint 010 closed 2026-09-13 with `wa-extract consolidate`; both sealed together as `v0.9.0` on 2026-09-14 (`CHANGELOG.md`). Sprint 011 closed 2026-09-15 with the harvest wall-clock deadline, the journal header fix, the `commands.py` split, and the append-only chat-index journal. None of the three stamped this file; corrected 2026-09-15 — and drifted again the same day: Sprint 011's own deployment (sealed `v0.10.0` at `6259d5e`, same day) landed after that correction and this file was never updated to say so, so it kept reporting "deployment pending" against a `main` that had already moved. Corrected again here, at Sprint 012, which found it by comparing this file's claim against `git rev-parse main` rather than trusting the prose.

**Decisions:** [ADR-0001](decisions/ADR-0001-product-scope-whatsapp-web.md) (product) · [ADR-0002](decisions/ADR-0002-delivery-program-and-layout.md) (delivery + layout) · [ADR-0003](decisions/ADR-0003-media-placeholders-in-export.md) (media placeholders) · [ADR-0004](decisions/ADR-0004-completeness-criterion.md) (completeness) · [ADR-0005](decisions/ADR-0005-enumeration-completeness.md) (enumeration) · [ADR-0006](decisions/ADR-0006-run-journal-and-resume.md) (run journal + resume) · [ADR-0007](decisions/ADR-0007-corpus-contract-v6.md) (corpus contract v6)  
**Released:** `v0.10.0` — Sprint 011 sealed (`CHANGELOG.md`, tag at `6259d5e`): the harvest loop's wall-clock deadline (`--deadline-seconds`, `stopped_reason: "deadline"`, no longer blocks a fully unattended run), the journal header regression (`read_journal` now keeps the first `--resume` header, not the last), `__main__.py` split into CLI wiring plus a new `commands.py` (854→277 lines), and the title index rewritten append-only (`chat_index_<run_id>.ndjson`, replacing the batched writer). Before that, `v0.9.0` sealed Sprints 009+010: an append-only run journal with `--resume` and a browserless `recover` subcommand (`ADR-0006`), corpus contract v6 (`ADR-0007`), and `wa-extract consolidate` folding every per-chat export into one `data/corpus_<run_id>.ndjson`, verified live against 1018 real files. **In flight:** Sprint 012 (`ai-sprint/012`) — everything blocking publishing the repository and routine unattended use: the `SEARCH_RESULT_SELECTORS` defect and its regression test, the `--deadline-seconds`/F-4 coverage gap (both closed), README/doc drift against the shipped code, the four absent platform docs, an unattended-run runbook, and — once merged and gated — the GitHub-side public-repository actions. Full plan: `docs/sprints/012-backend-extractor/IMPLEMENTATION_PLAN.md`.  
**Blueprint:** [EXTRACTOR_BLUEPRINT.md](architecture/EXTRACTOR_BLUEPRINT.md)  
**Program roadmap:** [docs/roadmaps/docs/extractor/002-delivery-program.md](roadmaps/docs/extractor/002-delivery-program.md)

---

## 1. What this is

**WhatsApp Chat Extractor** produces a **text JSON dump** of customer-support chats from **one** business WhatsApp number, taken via **WhatsApp Web**, so a **separate** AI pipeline can later study requests, behaviour, and sentiment for a care bot.

Since Sprint 007 a single invocation covers the whole account: `export-all` enumerates every conversation and writes a run manifest stating the outcome of each. Measured on 2026-08-31 against 910 conversations. Since Sprint 008 that enumeration sweeps until two consecutive sweeps agree, because a single sweep silently lost conversations whenever the list reordered under it (`ADR-0005`).

Since Sprint 009 a run survives a crash: an append-only journal records every outcome as it happens, `export-all --resume <run_id>` continues an interrupted run without re-exporting what already succeeded, and `recover` rebuilds a manifest from the journal with no browser. Since Sprint 010, `wa-extract consolidate` folds every per-chat export into one `data/corpus_<run_id>.ndjson` file for a downstream reader. Since Sprint 011 a per-conversation harvest is bounded in wall-clock time as well as pass count (`--deadline-seconds`), which removes the last item the roadmap named as blocking a fully unattended run.

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
[Operator / agent session] --> [Export package: src/whatsapp_chat_extractor/]
        |                              |
        | (QR / confirm)               v
        +---------------------> [Playwright → WhatsApp Web]
                                       |
                                       v
                     [data/ (gitignored): chat exports + run manifest]
```

`export-all` sweeps the chat list (virtualized: 910 conversations behind a 70-row
window), opens each conversation by verified identity, and harvests it with the
same loop `export-one` uses.

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
| `src/whatsapp_chat_extractor/chat_list.py` | Chat-list enumeration; opens a chat by verified identity | Present (#007) |
| `src/whatsapp_chat_extractor/manifest.py` | Run manifest; opt-in `chat_id` → name index, now an append-only `chat_index_<run_id>.ndjson` journal (`open_chat_index_journal`/`append_chat_index_entry`) rather than one batched write at run end | Present (#007), rewritten append-only (#011) |
| `src/whatsapp_chat_extractor/journal.py` | Append-only NDJSON run journal, `fsync` per record; recovery via `read_journal`, resume via `exported_chat_ids`; `read_journal` keeps the first `RECORD_HEADER` it sees, not the last (`T-8`) | Present (#009), header-selection fix (#011) |
| `src/whatsapp_chat_extractor/timestamps.py` | Locale-aware timestamp parsing (`parse_rendered` → ISO-8601); `undated_count` gap accounting | Present (#009) |
| `src/whatsapp_chat_extractor/consolidate.py` | Reads every `data/chat_*.json`, checks schema v6 + no repeated `chat_id`, writes one `data/corpus_<source_run>.ndjson` (`wa-extract consolidate`) | Present (#010) |
| `src/whatsapp_chat_extractor/commands.py` | The five `cmd_*` CLI handlers, extracted out of `__main__.py` (854→277 lines), including the harvest loop's `--deadline-seconds` wiring | Present (#011) |
| `scripts/probe_chat_start.py` | Start-marker probe (operator-run) | Present (#006) |
| `scripts/probe_chat_list.py` | Chat-list virtualization / index-stability probe (operator-run) | Present (#007) |
| `scripts/probe_unknown_rows.py` | DOM signatures of rows whose `sender` or `kind` is `unknown` (operator-run) | Present (#008) |
| `tests/` | Pytest (fixtures; no live WA) | Present (#003) |
| `pyproject.toml` | Packaging / CLI `wa-extract` | Present (#003) |
| `docs/architecture/EXTRACTOR_BLUEPRINT.md` | Extractor reference | Present (#003) |
| `docs/decisions/ADR-0001-*.md` | Product scope | Present (#002) |
| `docs/decisions/ADR-0002-*.md` | Delivery + layout | Present (#002) |
| `docs/decisions/ADR-0003-*.md` | Media placeholders (supersedes ADR-0001 coverage) | Present (#005) |
| `docs/decisions/ADR-0004-*.md` | Completeness as three values (supersedes ADR-0001 «full history») | Present (#007) |
| `docs/decisions/ADR-0005-*.md` | Enumeration completeness as three values (supersedes `enumeration_complete`) | Present (#008) |
| `docs/decisions/ADR-0006-run-journal-and-resume.md` | Append-only run journal and `--resume` contract | Present (#009) |
| `docs/decisions/ADR-0007-corpus-contract-v6.md` | Corpus contract v6: `message_id`, `timestamp_iso`, pinned locale + resolved timezone, `passes_used` | Present (#009) |
| `.github/workflows/ci.yml` | ruff, pytest, no-committed-chats guard | Present (#004), not executing — billing |
| `docs/PLATFORM_HARDENING.md` | Controls pending a public repository | Present (#004) |
| `docs/` / `.agents/` | Docs + framework | Present |

Framework map: `.agents/docs/architecture/topology_map.md`.
