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
| W1 | `docs/decisions/ADR-0004-completeness-criterion.md` | create | high | `doc_orchestrator` | `opus` | `high` | ✅ `5447312` |
| W2 | `src/whatsapp_chat_extractor/history.py` | modify | high | `implementer_agent` | `opus` | `high` | ✅ `7a94f73` |
| W3 | `src/whatsapp_chat_extractor/writers.py` | modify | high | `implementer_agent` | `opus` | `high` | ✅ `08b03ee` |
| W3a | `tests/test_writers.py` | modify | medium | `implementer_agent` | `sonnet` | `medium` | ✅ `cbceafb` |
| W4 | `tests/test_completeness.py` | create | medium | `implementer_agent` | `sonnet` | `medium` | ✅ `f27da4b` |
| W5 | `scripts/probe_chat_list.py` | create | medium | `implementer_agent` | `sonnet` | `medium` | ✅ `f0e2dda` `0d0d0b6` `2b33712` `01b7f37` |
| W5b | `tests/test_probe_chat_list.py` | create | medium | `implementer_agent` | `sonnet` | `medium` | ✅ `f30cb48` |
| W6 | `docs/sprints/007-backend-extractor/CHAT_LIST_PROBE_NOTES.md` | create | low | `doc_orchestrator` | `haiku` | `low` | ✅ `497edae`+ |
| W7 | `src/whatsapp_chat_extractor/chat_list.py` | create | high | `implementer_agent` | `opus` | `high` | ✅ `cb2783b` |
| W8 | `tests/test_chat_list.py` | create | medium | `implementer_agent` | `sonnet` | `medium` | ✅ `1fdef57` |
| W9 | `src/whatsapp_chat_extractor/manifest.py` | create | high | `implementer_agent` | `opus` | `high` | ✅ `772aad8` |
| W10 | `tests/test_manifest.py` | create | medium | `implementer_agent` | `sonnet` | `medium` | ✅ `7c4ac69` |
| W11a | `src/whatsapp_chat_extractor/__main__.py` | modify | high | `implementer_agent` | `opus` | `high` | ✅ `ea3a878` |
| W11 | `src/whatsapp_chat_extractor/__main__.py` | modify | high | `implementer_agent` | `opus` | `high` | ✅ `d7ebc94` |
| W11b | `tests/test_export_all.py` | create | medium | `implementer_agent` | `sonnet` | `medium` | ✅ `a5e6da8` |
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

## Units added during execution

Two rows were not in the Phase 4.3 table and are recorded rather than absorbed,
following the `W1b` precedent of Sprint 006.

| # | Why it was not planned | Why it is not new scope |
| :--- | :--- | :--- |
| W3a `tests/test_writers.py` | The plan's Tests table named `test_writers.py` only as a regression to protect, having missed that eleven of its cases **assert the v4 contract literally** — `SCHEMA_VERSION == 4` and `build_export(complete=…)` | It is W3's test surface. A schema change that leaves the tests of the old schema in place has not been made |
| W11a `src/whatsapp_chat_extractor/__main__.py` | `build_export` lost its `complete=` argument, so the CLI call site stopped compiling the moment W3 landed | A **partial unlock of W11**, exactly as `W4a` was of `W4` in Sprint 006. It covers only the call site and the exit-code semantics that `ADR-0004` forces; the `export-all` subcommand stays ⏳ in block C |
| W5b `tests/test_probe_chat_list.py` | The Phase 4.3 table shipped W5 with no test row — the identical omission Sprint 006 made for W1, which `hooks/on_commit.py` caught then and did not catch now (this is a `feat(` commit, and the hook guards `fix(`) | It is W5's test surface. `virtualization_verdict` decides the enumerator's whole design from two integers, and an untested verdict function is the weakest link in the block |

**W11a is a behaviour fix, not a mechanical port.** Under the v4 boolean the
`if not harvest["complete"]` branch fired on **every export ever produced**,
because `complete` was never True: the operator was told each run had failed and
advised to raise a `--max-passes` cap that was not the cause. Only `truncated`
now exits `EXIT_INCOMPLETE`.

## Units added during execution — block C

| # | Why it was not planned | Why it is not new scope |
| :--- | :--- | :--- |
| W5c (`01b7f37`) | The plan treated the probe and the enumerator as separate files. They need the same selectors, the same title reader and the same bottom test, and `rules/code_craft.md §1` puts the extraction threshold at the second call site | The canonical copy moved into `chat_list.py` and the probe imports it. Two copies would let the instrument and the product measure different DOMs, which is the one thing a probe must never permit |
| W11b (`a5e6da8`) | The Phase 4.3 table gave W11 no test row, the third time this sprint | The plan's Tests table names the failure policy explicitly (*«un fallo en un chat no aborta la corrida»*). It is W11's test surface, not new work |

**Two functions were split because this sprint pushed them over
`agents.md §1 max_lines_per_func`.** `build_parser` reached 103 lines and
`cmd_export_one` 58; both were already long and both were made worse here.
`build_parser` is now three `_add_<command>` registrars plus a shared
`_add_harvest_args`, and `report_completeness` is extracted from
`cmd_export_one`. No function in the package exceeds 50 lines, measured by AST
rather than asserted.

## Block A verification

Run at the block tip `ea3a878`, host root:

| Command | Result |
| :--- | :--- |
| `.venv/bin/ruff check .` | `All checks passed!`, exit `0` |
| `.venv/bin/pytest tests/ -q` | **128 passed, 1 skipped** (116 at sprint open) |

The five block-A commits are one physical file each (`jurisdictional_lock`), so
the suite is green at the block tip rather than at every intermediate commit: the
contract spans `history.py` and `writers.py` and cannot change in one of them
alone. Recorded here rather than left for a bisect to discover.

## Blocks B and C verification

Run at `a5e6da8`, host root:

| Command | Result |
| :--- | :--- |
| `.venv/bin/ruff check .` | `All checks passed!`, exit `0` |
| `.venv/bin/pytest tests/ -q` | **191 passed, 1 skipped** (116 at sprint open) |
| `python3 -m whatsapp_chat_extractor export-all --help` | exit `0`; `--write-index` and `--limit` present |
| `grep -rn "TODO\|FIXME" src/ scripts/ tests/` | no matches |
| AST scan for functions over 50 lines | none |

**Not yet verified against a browser.** `export-all` has never run against
WhatsApp Web. The plan's operator verification (`export-all --limit 3`) is
outstanding, and no documentation should describe behaviour that has only been
exercised against doubles.

## Conflicts

No file appears twice in the Scope table, so `jurisdictional_lock` (one structural
file per task) holds for every row and `no_interference` has nothing to refuse.

Two adjacencies are worth naming because they are *not* conflicts:

- **W2 and W3** both change the completeness contract, in two different files.
  W2 classifies, W3 serializes. They are sequential commits, never concurrent.
- **W5 and W7** both read the chat list. W5 only measures and W7 only acts on
  what W5 measured; W7 does not start until W6 records numbers.
