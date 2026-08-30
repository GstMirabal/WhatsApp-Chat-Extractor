# Task Scope — Sprint 005 (`backend-extractor`, P2.5)

Phase 4.3 of `workflows/pipeline_workflow.md`. Source: `IMPLEMENTATION_PLAN.md`
`## Work`.

**Mode.** `session_tool: cursor`, `delegation_mode: sequential`. Cursor cannot
spawn the eight pipeline roles, so the `Assignee` column names **which profile's
ruleset governed each write**, not a dispatched subagent. Zero subagents were
instantiated.

> **This file was written during the close, after the work it scopes.**
> Stated plainly rather than backdated. `jurisdictional_lock` and
> `no_interference` are applied by *reading* this file during execution, so for
> Sprint 005 they were not in force — they were satisfied by the fact that a
> single sequential worker held every file, which is a property of the mode, not
> of this artifact. The check that would have caught the omission
> (`close_workflow.md` Phase 2.6) is what produced this file, one sprint late.
> Recorded as `KI-005-C`.

## Units

| # | File | Operation | Risk | Assignee | Model | Effort | Isolation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| W2 | `probe_kind.py` (scratchpad, outside the repository) | create | medium | `implementer_agent` | opus-5 | high | Sole holder. Never committed: it is measurement, not a deliverable |
| W3 | `src/whatsapp_chat_extractor/export_one.py` | modify | high | `implementer_agent` | opus-5 | high | Sole holder. Blocked until W2 output existed (`KI-004-A`) |
| W4 | `src/whatsapp_chat_extractor/writers.py` | modify | medium | `implementer_agent` | opus-5 | medium | Sole holder |
| W5 | `src/whatsapp_chat_extractor/history.py` | modify | medium | `implementer_agent` | opus-5 | medium | Sole holder. Risk raised from the plan's `low`: the plan's stated rationale was wrong and the fix moved to `export_one._row_id` |
| W6 | `tests/test_row_fields.py` | modify | low | `implementer_agent` | opus-5 | medium | Sole holder |
| W7 | `tests/test_writers.py` | modify | low | `implementer_agent` | opus-5 | low | Sole holder |
| W7b | `tests/test_history.py` | modify | low | `implementer_agent` | opus-5 | low | Sole holder. **Not in the approved plan**: the plan's own Tests table demanded a media-dedup check and named no file for it |
| W8 | `.cursor/commands/wa-export.md` | create | low | `skill_architect` | opus-5 | low | Sole holder |
| W8b | `.gitignore` | modify | low | `skill_architect` | opus-5 | low | Sole holder. Required by W8: the directory exclusion made the new file untrackable |
| W9 | `README.md` | create | low | `doc_orchestrator` | opus-5 | medium | Sole holder. `readme-standardizer` skill invoked |
| W10 | `LICENSE` | create | low | `doc_orchestrator` | opus-5 | low | Sole holder |
| W11 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | opus-5 | medium | Sole holder |
| W11b | `docs/walkthroughs/EXTRACTOR_WALKTHROUGH.md` | modify | low | `doc_orchestrator` | opus-5 | low | Sole holder. `RA-05` requires it; the plan's Work table omitted it while its own Documentary-impact table listed it |
| W12 | `CHANGELOG.md` | modify | low | `doc_orchestrator` | opus-5 | low | Sole holder |

No unit shares a file with another. No unit ran concurrently: execution was
strictly sequential in one session, which is what `delegation_mode: sequential`
declares.

## Rule audit

| Rule | Applies to | Verdict |
| :--- | :--- | :--- |
| `jurisdictional_lock` | Every unit | Satisfied by mode. One physical file per unit; see the note above on why this file did not enforce it |
| `no_interference` | Every unit | No concurrent subtask existed to collide with |
| `code_craft` / `max_lines_per_func` | W3–W7b | New functions are 3–42 lines. Three pre-existing functions exceed 50 and were **not** touched — recorded, not fixed (Gate-1 `RECORD`) |
| `ephemeral` (`TODO`/`FIXME`) | W3–W12 | Clean; `grep` over `src/`, `tests/`, the command, README and LICENSE returns nothing |
| `code_logic` (English only) | W3–W12 | Source, tests, commits and shipped artifacts are English. Spanish is confined to this sprint's plan and the chat (`§1 user_chat`) |
| `secret_sovereignty` | All | No `.env` read. No credential in any diff |
| `path_type` (relative only) | W3–W12 | No absolute path in committed source. The W2 probe used one and is not committed |
| `strict_rule` / `jurisdiction` | All | `git -C .agents status --porcelain` empty at every commit |
| `historical_log` | All commits | Conventional Commits with the `#005` suffix |

## Out of scope, enforced

| Excluded | Where it went |
| :--- | :--- |
| Downloading or referencing media content | Prohibited by ADR-0001 and ADR-0003 §2 |
| Transcribing voice notes | ADR-0003 option D; would send customer audio to a third party |
| Uncapped run / `complete: true` | Sprint 006 |
| Identifying the 6 `unknown` rows | Needs a fresh DOM probe; Sprint 006 |
| Synthesizing a date for media rows | Deliberately not done; a fabricated date is indistinguishable from a measured one |
| `open_chat_by_query` defect | Finding 4; hotfix or Sprint 006, human decides |
| Nucleus PRs for `UPSTREAM_FINDING_004`/`_005`/`_006` | Separate `.agents` clone, Sprint 008 |
