# Task Scope — Sprint 007 (`backend-extractor`, P3b)

Phase 4.3 of `workflows/pipeline_workflow.md`. Source: `IMPLEMENTATION_PLAN.md`
`## Work`.

**Mode.** `session_tool: cursor`, `delegation_mode: sequential`. Cursor cannot
spawn the eight pipeline roles, so `Assignee` names **which profile's ruleset
governs each write**, not a dispatched subagent.

**Isolation.** `jurisdictional_lock` and `no_interference` are applied by
*reading* this file during execution. It is written **before** Phase 6.

## Measured model tiers

Run in this session, immediately before writing the `Model` / `Effort` columns.
`make -f .agents/Makefile cursor-tiers` **now succeeds in this host**: Sprint 006
recorded it failing because `UPSTREAM_FINDING_011` leaves `cd $(AGENTS_DIR)`
unquoted and the repository path contained spaces. The directory was renamed to
`WhatsApp-Chat-Extractor` on 2026-08-30, so the target runs. The upstream defect
is unfixed at pin `v4.24.0` and still needs its nucleus PR — this host merely no
longer trips it.

```
$ make -f .agents/Makefile cursor-tiers
Models after hard filters (excl. default): 35
Map author cell: glm-5.2
Applied model (discrepancy): grok-4.6 — differs from map author glm-5.2

$ python3 scripts/audit_cursor_models.py --resolve mechanical
modelId=composer-2.5
effort=

$ python3 scripts/audit_cursor_models.py --resolve gate
modelId=claude-opus-5
effort=max
```

Values are transcribed from that measured block. No `claude_code` alias was
copied from `config/model_tiers.json` (`F-20260825-027`).

## Scope

| # | File | Operation | Risk | Assignee | Model | Effort | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| W1 | `docs/decisions/ADR-0004-completeness-criterion.md` | create | high | `doc_orchestrator` | `claude-opus-5` | `max` | ⏳ |
| W2 | `src/whatsapp_chat_extractor/history.py` | modify | high | `implementer_agent` | `claude-opus-5` | `max` | ⏳ |
| W3 | `src/whatsapp_chat_extractor/writers.py` | modify | high | `implementer_agent` | `claude-opus-5` | `max` | ⏳ |
| W4 | `tests/test_completeness.py` | create | medium | `implementer_agent` | `claude-opus-5` | `high` | ⏳ |
| W5 | `scripts/probe_chat_list.py` | create | medium | `implementer_agent` | `claude-opus-5` | `high` | ⏳ |
| W6 | `docs/sprints/007-backend-extractor/CHAT_LIST_PROBE_NOTES.md` | create | low | `doc_orchestrator` | `composer-2.5` | — | ⏳ |
| W7 | `src/whatsapp_chat_extractor/chat_list.py` | create | high | `implementer_agent` | `claude-opus-5` | `max` | ⏳ |
| W8 | `tests/test_chat_list.py` | create | medium | `implementer_agent` | `claude-opus-5` | `high` | ⏳ |
| W9 | `src/whatsapp_chat_extractor/manifest.py` | create | high | `implementer_agent` | `claude-opus-5` | `max` | ⏳ |
| W10 | `tests/test_manifest.py` | create | medium | `implementer_agent` | `claude-opus-5` | `high` | ⏳ |
| W11 | `src/whatsapp_chat_extractor/__main__.py` | modify | high | `implementer_agent` | `claude-opus-5` | `max` | ⏳ |
| W12 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | `composer-2.5` | — | ⏳ |
| W13 | `README.md` | modify | low | `doc_orchestrator` | `composer-2.5` | — | ⏳ |
| W14 | `docs/0_SYSTEM_OVERVIEW.md` | modify | low | `doc_orchestrator` | `composer-2.5` | — | ⏳ |
| W15 | `CHANGELOG.md` | modify | low | `doc_orchestrator` | `composer-2.5` | — | ⏳ |

**Status legend.** ⏳ not started · 🟡 written, awaiting the operator's probe run ·
✅ `<sha>` landed · 🔒 not authorized by the Approval Gate. Every row is ⏳ because
Phase 5 has not run: no unit is authorized yet.

**Blocks are the unit of authorization**, mirroring Sprint 006's partial gate.
A → W1–W4 (offline). B → W5–W6 (operator present). C → W7–W11 (needs B's
numbers). D → W12–W15.

## Escalation notes

Required wherever a row's risk exceeds the mechanical tier's reach.

| # | Escalated from | Why the mechanical tier is not enough |
| :--- | :--- | :--- |
| W1 | `composer-2.5` | The ADR closes the choice between two completeness models and must record why the rejected ones were rejected. That is judgment, and `history.py:38-44` shows the cost of getting it wrong: 217 messages labelled complete |
| W2 | `composer-2.5` | The classification is the single point where an inference could be recorded as proof. The whole sprint exists because this field is constant today |
| W3 | `composer-2.5` | Schema change v4 → v5: a field that reaches the written corpus and cannot be corrected retroactively without re-running the export |
| W4, W8, W10 | `composer-2.5` | The tests must fail against the current tree to be worth anything (`KI-H001-B`); a test that passes either way is the failure mode here |
| W5 | `composer-2.5` | The probe runs against a live third-party DOM in the operator's real session. `KI-004-D` records a harvester that clicked links inside message bubbles; a careless selector does damage no test catches |
| W7 | `composer-2.5` | Chat identity. If enumeration duplicates or skips a conversation it does so **silently** — the same class of failure as H-001, which shipped and needed a hotfix |
| W9 | `composer-2.5` | The only unit that can write a real person's name to disk (`--write-index`). `ADR-0001` prohibits names in `data/` by default |
| W11 | `composer-2.5` | The failure policy lives here: a wrong abort rule wastes a manual login and a partial corpus |

Rows W6 and W12–W15 stay mechanical: they transcribe measured evidence and
decisions already taken elsewhere, and none of them can put a wrong value into an
exported corpus.

## Conflicts

No file appears twice in the Scope table, so `jurisdictional_lock` (one structural
file per task) holds for every row and `no_interference` has nothing to refuse.

Two adjacencies are worth naming because they are *not* conflicts:

- **W2 and W3** both change the completeness contract, in two different files.
  W2 classifies, W3 serializes. They are sequential commits, never concurrent.
- **W5 and W7** both read the chat list. W5 only measures and W7 only acts on
  what W5 measured; W7 does not start until W6 records numbers.
