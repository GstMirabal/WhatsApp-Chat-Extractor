# Task Scope: Sprint 011 — backend-extractor

**Canonical path**: `docs/sprints/011-backend-extractor/task_scope.md`
**Phase**: 4.3 (Rule Audit), authored by `rule_validator`.
**Source**: `docs/sprints/011-backend-extractor/IMPLEMENTATION_PLAN.md` §Work (13 rows).
**Session**: `session_tool: claude-code`, `delegation_mode: native` (`docs/active_state.json`).
This is a Claude Code session, not Cursor — the `session_tool: cursor` branch of
`agents.md §Phase 2 tier_transcription` does not apply. No `make cursor-tiers` run
is required and none was performed.

`jurisdictional_lock` / `no_interference` are applied by reading this file: a
file listed by an in-progress subtask below is locked for every other subtask.
Rows 9 and 12 each name more than one physical file because they are a single
coherent test-repointing/coverage pass, not independent structural edits, per
the Implementation Plan's own `jurisdictional_lock` note under the Work table —
`agent_orchestrator` may split them into one commit per file at Phase 4.1 if it
prefers strict one-file units.

## Model/Effort transcription

`.agents/config/model_tiers.json` `tiers.author.profiles` includes
`implementer_agent`; for `claude_code` that tier resolves to
`model: sonnet, effort: medium`. Every row below is plain author-tier work
under Claude Code — none of the 13 units is a gate (`opus`/`high`) or
mechanical (`haiku`/`low`) profile — so `Model = sonnet` and `Effort = medium`
are transcribed unchanged for every row, per that catalogue. This is a
transcription of the existing `claude_code` column, not an invented tier.

## Work

| # | File | Operation | Risk | Assignee | Model | Effort | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `src/whatsapp_chat_extractor/history.py` | modify | medium | `implementer_agent` | sonnet | medium | ✅ 06fc694 (trimmed to the 50-line cap in 7be5672) |
| 2 | `src/whatsapp_chat_extractor/__main__.py` (CLI flag wiring only, Block A) | modify | low | `implementer_agent` | sonnet | medium | ✅ 754b52c |
| 3 | `tests/test_history.py` | modify | low | `implementer_agent` | sonnet | medium | ✅ a32f8a8 |
| 4 | `src/whatsapp_chat_extractor/journal.py` | modify | low | `implementer_agent` | sonnet | medium | ⏳ |
| 5 | `tests/test_journal.py` | modify | low | `implementer_agent` | sonnet | medium | ⏳ |
| 6 | `src/whatsapp_chat_extractor/commands.py` (new, Block C extraction) | create | high | `implementer_agent` | sonnet | medium | ⏳ |
| 7 | `src/whatsapp_chat_extractor/__main__.py` (strip `cmd_*`, Block C) | modify | high | `implementer_agent` | sonnet | medium | ⏳ |
| 8 | `src/whatsapp_chat_extractor/export_one.py` | modify | medium | `implementer_agent` | sonnet | medium | ⏳ |
| 9 | `tests/test_export_all.py` / `test_resume.py` / `test_consolidate_cli.py` (repoint patches, Block C) | modify | medium | `implementer_agent` | sonnet | medium | ⏳ |
| 10 | `src/whatsapp_chat_extractor/manifest.py` | modify | medium | `implementer_agent` | sonnet | medium | ⏳ |
| 11 | `tests/test_manifest.py` | modify | low | `implementer_agent` | sonnet | medium | ⏳ |
| 12 | `tests/test_consolidate.py` / `test_consolidate_cli.py` (`T-1`–`T-7`) | modify | low | `implementer_agent` | sonnet | medium | ⏳ |
| 13 | `tests/test_export_search.py` or new `tests/test_timezone.py` (`T-2`) | create/modify | low | `implementer_agent` | sonnet | medium | ⏳ |

Status starts at `⏳` (not started) for every row, matching the Implementation
Plan's Work table at Phase 3 extraction — no unit has begun execution yet.

## Rule Audit (Phase 4.3)

Audited the Implementation Plan's Design section against `rules/code_craft.md`
and `agents.md §1` (`max_lines_per_func` 50, `max_indentation` 3, no
`TODO`/`FIXME`, mandatory type hints, `snake_case`/`PascalCase`) ahead of this
sprint proceeding.

- **Block A** (`history.py`: `deadline_seconds` threaded through
  `harvest_history` → `_one_pass` → `_observe_and_decide` → `decide_stop`,
  checked against `time.monotonic()`): adds one parameter and one comparison
  per function on an existing call chain. This does not add a nesting level
  (the check is a guard/return, not a new branch nested inside existing ones)
  and does not add a name to a function already near either ceiling; no new
  violation of `max_indentation` or `max_lines_per_func` is introduced by the
  stated design. No `TODO`/`FIXME` marker is proposed. Concern: the plan does
  not name which of the four touched functions receives the new parameter
  closest to its existing line count — `implementer_agent` should re-measure
  line count on `history.py` after threading the parameter through, before
  closing row 1, since the plan itself flags this file's neighborhood
  (`export_one.py`) as already carrying pre-existing over-length functions.
- **Block C** (`__main__.py` / `export_one.py`: extract `cmd_*` handlers into
  `commands.py`; extract `cmd_login`'s depth-4 block and `export_one.py`'s two
  depth-4 / two over-length functions into named helpers): this block is
  explicitly designed to **reduce** existing `max_lines_per_func` and
  `max_indentation` violations recorded in `docs/active_state.json`
  `acknowledged_gaps.preexisting_complexity_violations`, not to introduce new
  code shaped by a new requirement — extraction of existing bodies into named
  helpers is the sanctioned fix for both ceilings and carries no default risk
  of re-violating them, provided each extracted helper is itself measured
  post-extraction (already required by the plan's Verification table: the AST
  walk command re-checks `export_one.py`, `__main__.py`, `commands.py` for
  0 functions over 50 lines / depth 3). No violation of `rules/code_craft.md`
  is introduced by Block C's stated design; the Verification table already
  carries the check that would catch a regression, so no additional row is
  needed here.
- **No other block** (B, D, E) touches source code shape in a way
  `rules/code_craft.md` governs — B is a one-line guard fix, D is a rewrite of
  one function's write strategy (batched → append-only) with no stated length
  or nesting change, E is test-only with zero production code changes.

**Conclusion**: no rule violation found in the plan's stated approach. One
non-blocking concern noted above (Block A line-count re-measurement) for
`implementer_agent` to carry into row 1, not a defect in the plan itself.
