# Task Scope — Sprint 007 (`backend-extractor`, P3b)

Phase 4.3 of `workflows/pipeline_workflow.md`. Source: `IMPLEMENTATION_PLAN.md`
`## Work`.

**Mode.** `session_tool: claude-code`, `delegation_mode: native`. `Assignee` names
the profile whose ruleset governs each write and which may be dispatched as a
subagent.

**This file was first written for the wrong harness and is corrected here.** The
anchor was claimed as `cursor`/`sequential` because `commands/start.md` hardcoded
`--tool cursor` for both harnesses until framework `v4.24.0`, and this session
received the command text from the `v4.23.0` mirror — minutes before
`sync_agents_pin.py` applied the bump that fixes it. Consequences reverted with
the correction: `RA-18` does **not** apply to this sprint, and the Model column
below no longer carries Cursor model ids.

**Isolation.** `jurisdictional_lock` and `no_interference` are applied by
*reading* this file during execution. It is written **before** Phase 6.

## Model tiers

Source under Claude Code is `config/model_tiers.json`, `claude_code` column — the
tiers the harness applies natively through each profile's `model:` field:

```
$ python3 -c "import json; d=json.load(open('.agents/config/model_tiers.json')); \
  print({k: v['claude_code'] for k, v in d['tiers'].items()})"
gate         -> {'model': 'opus',   'effort': 'high'}
author       -> {'model': 'sonnet', 'effort': 'medium'}
mechanical   -> {'model': 'haiku',  'effort': 'low'}
```

`audit_cursor_models.py` and `make cursor-tiers` are **not** the source here:
they derive the `cursor` column from Cursor's on-disk catalogue, and this is not
a Cursor session. `F-20260825-027` prohibits copying `claude_code` aliases into a
*Cursor* `task_scope.md`; under Claude Code that column is the correct source and
the prohibition does not invert.

`Model` and `Effort` are required on every Work table from Sprint 28 onward under
**every** harness, not only Cursor (`scripts/check_task_scope.py:38`
`MODEL_FROM_SPRINT = 28`).

## Scope

| # | File | Operation | Risk | Assignee | Model | Effort | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| W1 | `docs/decisions/ADR-0004-completeness-criterion.md` | create | high | `doc_orchestrator` | `opus` | `high` | ⏳ |
| W2 | `src/whatsapp_chat_extractor/history.py` | modify | high | `implementer_agent` | `opus` | `high` | ⏳ |
| W3 | `src/whatsapp_chat_extractor/writers.py` | modify | high | `implementer_agent` | `opus` | `high` | ⏳ |
| W4 | `tests/test_completeness.py` | create | medium | `implementer_agent` | `sonnet` | `medium` | ⏳ |
| W5 | `scripts/probe_chat_list.py` | create | medium | `implementer_agent` | `sonnet` | `medium` | ⏳ |
| W6 | `docs/sprints/007-backend-extractor/CHAT_LIST_PROBE_NOTES.md` | create | low | `doc_orchestrator` | `haiku` | `low` | ⏳ |
| W7 | `src/whatsapp_chat_extractor/chat_list.py` | create | high | `implementer_agent` | `opus` | `high` | ⏳ |
| W8 | `tests/test_chat_list.py` | create | medium | `implementer_agent` | `sonnet` | `medium` | ⏳ |
| W9 | `src/whatsapp_chat_extractor/manifest.py` | create | high | `implementer_agent` | `opus` | `high` | ⏳ |
| W10 | `tests/test_manifest.py` | create | medium | `implementer_agent` | `sonnet` | `medium` | ⏳ |
| W11 | `src/whatsapp_chat_extractor/__main__.py` | modify | high | `implementer_agent` | `opus` | `high` | ⏳ |
| W12 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | `haiku` | `low` | ⏳ |
| W13 | `README.md` | modify | low | `doc_orchestrator` | `haiku` | `low` | ⏳ |
| W14 | `docs/0_SYSTEM_OVERVIEW.md` | modify | low | `doc_orchestrator` | `haiku` | `low` | ⏳ |
| W15 | `CHANGELOG.md` | modify | low | `doc_orchestrator` | `haiku` | `low` | ⏳ |

**Status legend.** ⏳ authorized, not started · 🟡 written, awaiting the operator's
probe run · ✅ `<sha>` landed · 🔒 not authorized by the Approval Gate.

**Approval Gate (Phase 5) — FULL APPROVAL, human, 2026-08-31.** All four blocks
(W1–W15) authorized, and `ADR-0004` confirmed as Option C. No row is `🔒`. W5's
probe run and any `export-all` invocation still require the operator present —
that is a physical constraint, not a withheld authorization.

Block order remains binding: A → W1–W4 (offline). B → W5–W6 (operator present).
C → W7–W11 (needs B's numbers). D → W12–W15.

## Escalation notes

Required wherever a row's risk exceeds the mechanical tier's reach.

| # | Escalated from | Why the mechanical tier is not enough |
| :--- | :--- | :--- |
| W1 | `haiku` | The ADR closes the choice between two completeness models and must record why the rejected ones were rejected. That is judgment, and `history.py:38-44` shows the cost of getting it wrong: 217 messages labelled complete |
| W2 | `haiku` | The classification is the single point where an inference could be recorded as proof. The whole sprint exists because this field is constant today |
| W3 | `haiku` | Schema change v4 → v5: a field that reaches the written corpus and cannot be corrected retroactively without re-running the export |
| W4, W8, W10 | `haiku` | The tests must fail against the current tree to be worth anything (`KI-H001-B`); a test that passes either way is the failure mode here |
| W5 | `haiku` | The probe runs against a live third-party DOM in the operator's real session. `KI-004-D` records a harvester that clicked links inside message bubbles; a careless selector does damage no test catches |
| W7 | `haiku` | Chat identity. If enumeration duplicates or skips a conversation it does so **silently** — the same class of failure as H-001, which shipped and needed a hotfix |
| W9 | `haiku` | The only unit that can write a real person's name to disk (`--write-index`). `ADR-0001` prohibits names in `data/` by default |
| W11 | `haiku` | The failure policy lives here: a wrong abort rule wastes a manual login and a partial corpus |

Rows W6 and W12–W15 stay mechanical (`haiku` / `low`): they transcribe measured evidence and
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
