# Skill Assignment — Sprint 011 (backend-extractor)

Source: `docs/sprints/011-backend-extractor/IMPLEMENTATION_PLAN.md`.
Phase 4.2 of `workflows/pipeline_workflow.md`. Drafted from this template.

Mode: **claude-code**, `delegation_mode: native`.

After writing this file, run:
`python3 .agents/scripts/check_forge_ladder.py --sprint-dir docs/sprints/011-backend-extractor`
(exit `2` rejects an empty forge destination or submodule contamination.)

---

## 1. Priority ladder (record every rung)

`rules/skills_and_integrations.md §1`:

No skill search was needed for this sprint. All 13 rows in the Implementation
Plan's `## Work` table are ordinary Python source and test edits — a
wall-clock-timeout parameter threaded through an existing loop, a one-line
guard fix in a journal reader, extraction of five CLI handler functions into a
new module, a function-length/nesting-depth cleanup, conversion of a batched
JSON writer to an append-only NDJSON writer, and new unit tests covering
existing gaps. Every one of these thirteen units is resolved by tools already
present in this session — `Read`, `Edit`, `Write`, `Bash`, `ruff`, and
`pytest` — with no reusable, cross-project capability among them (`agents.md
§3 topological_order` skills exist for capabilities an agent invokes across
projects; these units are domain code specific to this extractor). The ladder
therefore terminates ahead of the first rung, and every rung below is recorded
as not reached rather than queried and found empty.

| Rung | Source | Result | Evidence |
| :--- | :--- | :--- | :--- |
| P1 | `skills/manifest_skills.json` | Not reached | Ladder terminated ahead of this rung; see paragraph above |
| P2 | `autoskills-3rd` | Not reached | Ladder terminated ahead of this rung; see paragraph above |
| P3 | `https://skills.sh/` (WebSearch/WebFetch) | Not reached | Ladder terminated ahead of this rung; see paragraph above |
| P4 | Three-File Standard at Destination | Not reached | No new tool was drafted for this sprint |

---

## 2. Per-unit tool resolution

| Unit | Skill / tool | Destination | P1–P4 trail |
| :--- | :--- | :--- | :--- |
| 1 (`history.py`, Block A deadline param) | `Edit` + `pytest` | N/A | N/A (no skill needed) |
| 2 (`__main__.py`, CLI flag wiring, Block A) | `Edit` | N/A | N/A (no skill needed) |
| 3 (`tests/test_history.py`) | `Edit` + `pytest` | N/A | N/A (no skill needed) |
| 4 (`journal.py`, Block B guard fix) | `Edit` | N/A | N/A (no skill needed) |
| 5 (`tests/test_journal.py`) | `Edit` + `pytest` | N/A | N/A (no skill needed) |
| 6 (`commands.py`, new, Block C extraction) | `Write` + `ruff` | N/A | N/A (no skill needed) |
| 7 (`__main__.py`, strip `cmd_*`, Block C) | `Edit` + `ruff` | N/A | N/A (no skill needed) |
| 8 (`export_one.py`, complexity fix) | `Edit` + `ruff` | N/A | N/A (no skill needed) |
| 9 (`test_export_all.py` / `test_resume.py` / `test_consolidate_cli.py`, repoint patches) | `Edit` + `pytest` | N/A | N/A (no skill needed) |
| 10 (`manifest.py`, Block D NDJSON conversion) | `Edit` | N/A | N/A (no skill needed) |
| 11 (`tests/test_manifest.py`) | `Edit` + `pytest` | N/A | N/A (no skill needed) |
| 12 (`tests/test_consolidate.py` / `test_consolidate_cli.py`, `T-1`–`T-7`) | `Write`/`Edit` + `pytest` | N/A | N/A (no skill needed) |
| 13 (`tests/test_export_search.py` or new `tests/test_timezone.py`, `T-2`) | `Write` + `pytest` | N/A | N/A (no skill needed) |

`Destination` for a drafted skill would be `host:.claude/skills/<name>/`
(default), `profile:<path>`, or `nucleus:PR` — not applicable here, since no
unit resolves to a skill.

---

## 3. Skills used

| Skill | Why |
| :--- | :--- |
| None | The plan's own `## Verification` table already names the exact commands each unit needs — `ruff check .` and `python3 -m pytest tests/ -q` — invoked directly as shell commands. No unit requires an installed skill's wrapper or procedural logic on top of that. |

---

## 4. Skills considered and rejected

| Candidate | Why rejected |
| :--- | :--- |
| `python-quality-auditor` | Its `SKILL.md` describes an agnostic Python health-check wrapping Ruff, Mypy, and Bandit. This sprint's Verification table already pins the single command that matters (`ruff check .`, exit `0`); routing that same call through the skill's script would add an indirection layer with no corresponding task in the Work table, and `RA-16` would then require a declared invoker for a mechanism the plan never names. Rejected in favor of the direct command already specified. |

---

## 5. Gaps

None.
