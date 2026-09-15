# Implementation Plan: Sprint 011 — backend-extractor

**Canonical path**: `docs/sprints/011-backend-extractor/IMPLEMENTATION_PLAN.md`
**Branch**: `ai-sprint/011` · **Base**: `main` at `136c1e1c5240e9876041eb48ea3334b48df54f2c`
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

Sprint 010 closed successfully and is already merged and sealed as `v0.9.0` on
`main` (`last_close_commit` in `docs/active_state.json` matches `HEAD` exactly —
`git log 136c1e1..HEAD` is empty, verified 2026-09-15). The product scope
(`ADR-0001`) is complete: `wa-extract export-all` exports every conversation and
`wa-extract consolidate` already joins every `data/chat_*.json` into one
`data/corpus_<run_id>.ndjson` (the user's initial ask this session — confirmed
already shipped, no new script needed).

What remains is the backlog carried, unscheduled, across Sprints 009-010. The
user asked to bundle **everything currently open** into Sprint 011 rather than
opening it item by item. Every figure below is measured against `HEAD` today
(2026-09-15), not copied from the sprint records that first found it:

| Item | Measured now | Source |
| :--- | :--- | :--- |
| `KI-009-H` | No wall-clock deadline in `harvest_history` (`history.py`) — only `max_passes` (iteration count) bounds it. `set_default_timeout` does not govern the `ElementHandle` calls the loop uses. **Blocks a fully unattended run** — the only carried item the roadmap marks as blocking | Sprint 009 `PHASE_REGISTER.md` |
| `T-8` | `journal.py:229` `read_journal` sets `header = record` on **every** `RECORD_HEADER` line with no guard — a journal holding two `--resume` headers reconstructs `started_at` from the *last* resume, not the run's true start. 570 of 1018 real conversations in this repo's own corpus predate the date their manifest claims | Sprint 010 `SPRINT_LOG.md` |
| `§D6` | `__main__.py` is now **854 lines** (was 793 at the last measurement, 421 at Sprint 008). `cmd_login` is at block depth 4 (limit 3, `agents.md §1 max_indentation`) | `wc -l`, AST walk run 2026-09-15 |
| Pre-existing complexity | `export_one.py`: `open_chat_by_query` 52 lines, `scroll_one_pass` 51 lines (limit 50, `agents.md §1 max_lines_per_func`); `_open_first_result` and `_click_load_earlier` at depth 4 | AST walk run 2026-09-15 (same figures as `active_state.json`'s `preexisting_complexity_violations`, reconfirmed unchanged) |
| `§D5` | `manifest.write_chat_index` still writes one batched JSON object at the end of a run — a crash before that call loses every title gathered during the run, unlike the outcomes journal's append-on-every-record discipline | Sprint 009 `SPRINT_LOG.md` |
| `T-2` | `_request_timezone` / `_confirm_timezone` (`__main__.py:377,395`) have no test | Sprint 009, carried twice |
| `T-1`…`T-7` | Seven mutation-proven coverage gaps in `consolidate.py` / its CLI (manifest selection, glob pinning, schema-abort scope, missing regression pin for `F-1`) | Sprint 010 `PHASE_REGISTER.md` |

**Deliberately not in this sprint** (see Out of scope): the nucleus PR for 11
framework-class upstream findings — `agents.md §3 jurisdiction` requires that
work in a **separate clone**, never a host sprint commit; the platform-docs gap
(`CONTRIBUTING.md` etc.) — owned by `/agents:harden`; hotfix candidate H-002
(search-selector reorder) — its own `hotfix/` track per `RA-03`; the systemic
"wall-clock-bound" rule amendment (`H-003 §5`) — framework-class, goes in the
same upstream PR, not into this host's `agents.md`.

---

## Design

**Block A — `KI-009-H` (priority: this is the one blocking item).**
Add a `deadline_seconds` parameter threaded through `harvest_history` →
`_one_pass` → `_observe_and_decide` → `decide_stop`, checked against
`time.monotonic()` captured at harvest start. A new `STOP_DEADLINE` reason is
added alongside `STOP_MAX_PASSES` (not added to `COMPLETE_REASONS`, so it falls
through to `truncated` in `classify_completeness` — consistent with how
`STOP_LOADING_UNRESOLVED` already fails closed). Rejected alternative: lowering
`max_passes` — already tried in spirit by `DEFAULT_LOADING_GRACE` (H-003) and
rejected there for the same reason it would be wrong here: a real conversation
can legitimately need more passes than a time-based cap would allow, and
`max_passes` exists precisely to guarantee termination on iteration count, not
wall time. The two bounds are complementary, not substitutes. Default value:
left as a CLI flag (`--deadline-seconds`) with no default enforced (`None` /
unbounded) unless the human sets one, because H-003's own measurement (13
passes max across 250 conversations) is not evidence for a **global** wall-clock
default — only for the grace period H-003 already bounds. Stating a default
here would be inventing a figure the corpus does not support.

**Block B — `T-8`.** One-line-guard fix: `if header is None: header = record`
in `journal.py:read_journal`. Regression test pins first-header-wins against a
synthetic two-header journal (the exact shape that produced the real defect).

**Block C — `§D6` + pre-existing complexity.** Extract the five `cmd_*`
handlers (`cmd_login`, `cmd_export_one`, `cmd_export_all`, `cmd_recover`,
`cmd_consolidate`) out of `__main__.py` into a new `commands.py` module;
`__main__.py` keeps `build_parser`/`_add_*`/`main()` only. This is the module
of its own the roadmap asked to "decide" on. Regression risk: existing tests
that patch functions via `whatsapp_chat_extractor.__main__.cmd_*` must be
repointed to `whatsapp_chat_extractor.commands.cmd_*` — `test_export_all.py`,
`test_resume.py`, `test_consolidate_cli.py` are the candidates (confirm by
`grep -rn "__main__\." tests/` before moving). `cmd_login`'s depth-4 block and
`export_one.py`'s two depth-4 / two over-length functions are fixed by
extracting their innermost `try`/`for` bodies into named helpers — no behavior
change, so the existing test suite is the regression guard, not new tests.

**Block D — `§D5`.** Convert `manifest.write_chat_index` from one batched
write to an append-only `data/chat_index_<run_id>.ndjson`, mirroring
`journal.append_outcome`'s discipline exactly (same module pattern, same
crash-tolerance argument). Resolves the sprint 009 open question in favor of
the NDJSON journal, not the batched-writer alternative: the batched writer is
the thing losing data on a crash, which is the defect this item exists to
close. No change to the privacy boundary — `--write-index` remains the gate,
`ADR-0001` is unaffected because titles never entered the pseudonymous run
journal either way.

**Block E — `T-2`, `T-1`–`T-7` (test-only, no behavior change).** Add the
missing unit tests named in Sprint 009/010's own gate records. Zero production
code changes; each test must be shown failing against `HEAD` before the row is
closed (see Tests table) — a test that already passes proves nothing.

**Sequencing and partial-close.** Blocks are ordered by priority (A first).
This project's own history (Sprints 006, 008, 009, 010) shows every ambitious
sprint here has closed `CLOSED (partial)` rather than fully — that pattern is
accepted precedent, not a plan defect. If Quality Gate budget runs out after
Block C, Blocks D and E carry to Sprint 012 named explicitly, exactly as `§D5`
and `T-2` themselves have already carried twice. This plan does not pretend
otherwise in advance.

---

## Work

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `src/whatsapp_chat_extractor/history.py` | modify | medium | `implementer_agent` | ⏳ |
| 2 | `src/whatsapp_chat_extractor/__main__.py` (CLI flag wiring only, Block A) | modify | low | `implementer_agent` | ⏳ |
| 3 | `tests/test_history.py` | modify | low | `implementer_agent` | ⏳ |
| 4 | `src/whatsapp_chat_extractor/journal.py` | modify | low | `implementer_agent` | ⏳ |
| 5 | `tests/test_journal.py` | modify | low | `implementer_agent` | ⏳ |
| 6 | `src/whatsapp_chat_extractor/commands.py` (new, Block C extraction) | create | high | `implementer_agent` | ⏳ |
| 7 | `src/whatsapp_chat_extractor/__main__.py` (strip `cmd_*`, Block C) | modify | high | `implementer_agent` | ⏳ |
| 8 | `src/whatsapp_chat_extractor/export_one.py` | modify | medium | `implementer_agent` | ⏳ |
| 9 | `tests/test_export_all.py` / `test_resume.py` / `test_consolidate_cli.py` (repoint patches, Block C) | modify | medium | `implementer_agent` | ⏳ |
| 10 | `src/whatsapp_chat_extractor/manifest.py` | modify | medium | `implementer_agent` | ⏳ |
| 11 | `tests/test_manifest.py` | modify | low | `implementer_agent` | ⏳ |
| 12 | `tests/test_consolidate.py` / `test_consolidate_cli.py` (`T-1`–`T-7`) | modify | low | `implementer_agent` | ⏳ |
| 13 | `tests/test_export_search.py` or new `tests/test_timezone.py` (`T-2`) | create/modify | low | `implementer_agent` | ⏳ |

`jurisdictional_lock` note: rows 9 and 12 each touch more than one physical
file because they are a single coherent test-repointing/coverage pass, not
independent structural edits — `agent_orchestrator` may split them into one
commit per file at Phase 4.1 if it prefers strict one-file units.

---

## Dependencies

| Package | Version | Why the standard library and the existing dependencies do not suffice |
| :--- | :--- | :--- |
| None | — | Every change uses `time.monotonic` (stdlib) and existing project modules |

---

## Mechanisms

| Mechanism | Deterministic or agent judgment | Invoker (`RA-16`) |
| :--- | :--- | :--- |
| None proposed | — | This sprint adds no new recurring mechanism |

---

## Cost

| Field | Value | Reproduce |
| :--- | :--- | :--- |
| Delegation | `native` | `docs/active_state.json` `delegation_mode` |
| Work units | 13 | Count of rows in Work table |
| Subagents dispatched | 0 (not yet executing) | — |
| Prior session ratio | 3.1x (most recent cycle), under both soft (5x) and hard (15x) thresholds | `python3 .agents/scripts/session_cost.py --from-anchor --json` |

---

## Tests

| Check | Fails against the current tree? |
| :--- | :--- |
| New: harvest stops with `STOP_DEADLINE` when `deadline_seconds` elapses, synthetic clock | **Yes** — no such reason exists yet |
| New: `read_journal` keeps the first header when two `RECORD_HEADER` lines are present | **Yes** — current code returns the last |
| Existing suite after `commands.py` extraction | **No** — regression guard; must still pass 100% post-move |
| New: `_request_timezone` / `_confirm_timezone` covered | **Yes** — no test references either name today (`grep -rn "_request_timezone\|_confirm_timezone" tests/` returns nothing) |
| New: `T-1`–`T-7` per Sprint 010 `PHASE_REGISTER.md` list | **Yes** — each names a specific untested branch |
| New: `write_chat_index` survives a crash mid-run (append-only) | **Yes** — batched writer currently loses everything before the final write |

---

## Verification

| Command | Expected |
| :--- | :--- |
| `ruff check .` | exit `0` |
| `python3 -m pytest tests/ -q` | all pass, 0 regressions vs. current baseline count |
| `python3 -c "import ast,pathlib; ..."` (the AST walk used to measure `§D6`/complexity above) | 0 functions over 50 lines / depth 3 in `export_one.py`, `__main__.py`, `commands.py` |
| `python3 -m whatsapp_chat_extractor export-one --deadline-seconds 5 ...` (manual, needs a live session) | Harvest stops at `STOP_DEADLINE` when the phone never answers, in ~5s not 8+ hours |

---

## Documentary impact (T5)

| Artefacto | Qué cambia |
| :--- | :--- |
| `docs/roadmaps/docs/extractor/002-delivery-program.md` | `KI-009-H`, `T-8`, `§D5`, `§D6`, `T-2`, `T-1`-`T-7` rows move from carried to closed (or re-carried, named, if a block does not land) |
| `docs/architecture/EXTRACTOR_BLUEPRINT.md` | New `commands.py` module documented; `history.py` deadline parameter documented |
| `CHANGELOG.md` | `[Unreleased]` entry at Sprint Closeout |

---

## Out of scope

| Exclusion | Why, and where it goes instead |
| :--- | :--- |
| 11 upstream findings nucleus PR | Framework-class, `agents.md §3 jurisdiction` requires a separate clone, not a host sprint commit |
| Systemic wall-clock-bound rule amendment (`H-003 §5`) | Framework-class; bundled into the same upstream PR above |
| Platform docs (`CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `NOTICE.md`) | Owned by `/agents:harden`, not a sprint |
| Hotfix candidate H-002 (search-selector reorder) | Production defect but not blocking; its own `hotfix/H-00N` branch per `RA-03` if prioritized |
| `composer_write_risk` hardening | Not an observed defect — hardening candidate only, no measured failure to fix |

---

## Abort criterion

Abort Block C (the `commands.py` extraction) specifically, reverting to the
pre-extraction `__main__.py`, if the post-move test suite shows any regression
that is not a simple import-path fix (i.e., a behavioral difference, not just a
patch target rename). Blocks A, B, D, E do not depend on Block C landing and
continue independently. Do not abort the whole sprint on one block's failure —
close the sprint `(partial)` and name what carried, per this project's own
established pattern.

---

## Approval — `triple_lock` lock 1

| Field | Value |
| :--- | :--- |
| **Approved by** | gst.mirabal@gmail.com (human, explicit "ok" in chat) |
| **Date** | 2026-09-15 |
| **Plan commit at approval** | `13aa85c` |
| **Remaining locks** | Active Sprint · QA + Tester verdicts · Human OK at close |

*Phase 5 is a single attended human authorization. It MUST NOT be wrapped inside an
unattended `/loop` (`workflows/pipeline_workflow.md`, `rules/loop_governance.md`).
Any `/loop` this sprint does run — Phases 6-8 only — is governed by
`scripts/loop_guard.py start`, which fails closed.*
