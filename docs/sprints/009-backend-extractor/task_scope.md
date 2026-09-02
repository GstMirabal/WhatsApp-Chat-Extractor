# 🔒 Task Scope: Sprint #009

**Phase 4.3** (`rule_validator`) · Plan: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)
**Check**: `python3 .agents/scripts/check_task_scope.py --sprint-dir docs/sprints/009-backend-extractor`

This file is what `jurisdictional_lock` and `no_interference` actually read
(`agents.md §2`). While it is absent both rules are **disabled while appearing
enforced** — the wording the checker itself uses when it fails.

**One physical file per unit.** No two units share a file, so no subtask can
collide with another in progress. Verified below.

---

## Model and Effort

`config/model_tiers.json` under `claude_code`:

| Tier | Model | Effort | Profiles in this sprint |
| :--- | :--- | :--- | :--- |
| `author` | `sonnet` | `medium` | `implementer_agent`, `doc_orchestrator` |
| `gate` | `opus` | `high` | `qa_agent`, `tester_agent`, `principal_agent` (Phase 7 / Phase 5) |

**Two units are escalated above their tier**, and the reason is written per row
rather than left to the reader: `C1` and `E5` are the only `high`-risk rows.
Neither assignee is a mechanical profile, so no gate compels the escalation — it
is a judgment recorded so it can be argued with.

---

## Work table

| # | File | Operation | Risk | Assignee | Model | Effort | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| A1 | `src/whatsapp_chat_extractor/journal.py` | create | medium | `implementer_agent` | sonnet | medium | ✅ 3be2542 |
| A2 | `tests/test_journal.py` | create | low | `implementer_agent` | sonnet | medium | ✅ 530c4b2 |
| B1 | `src/whatsapp_chat_extractor/manifest.py` | modify | medium | `implementer_agent` | sonnet | medium | ✅ 512860d |
| B2 | `tests/test_manifest.py` | modify | low | `implementer_agent` | sonnet | medium | ✅ 07c3b95 |
| C1 | `src/whatsapp_chat_extractor/__main__.py` | modify | high | `implementer_agent` (escalated) | opus | high | ⏳ |
| C2 | `tests/test_export_all.py` | modify | low | `implementer_agent` | sonnet | medium | ⏳ |
| C3 | `tests/test_resume.py` | create | low | `implementer_agent` | sonnet | medium | ⏳ |
| E1 | `src/whatsapp_chat_extractor/session.py` | modify | medium | `implementer_agent` | sonnet | medium | ✅ 1e49aef |
| E2 | `src/whatsapp_chat_extractor/timestamps.py` | create | medium | `implementer_agent` | sonnet | medium | ✅ ef12083 |
| E3 | `tests/test_timestamps.py` | create | low | `implementer_agent` | sonnet | medium | ✅ 495a371 |
| E4 | `src/whatsapp_chat_extractor/history.py` | modify | medium | `implementer_agent` | sonnet | medium | ✅ 2badc79 + 6c3b00c |
| E5 | `src/whatsapp_chat_extractor/writers.py` | modify | high | `implementer_agent` (escalated) | opus | high | ✅ 7fdae2b |
| E6 | `tests/test_history.py` | modify | low | `implementer_agent` | sonnet | medium | ✅ 19b73d2 |
| E7 | `tests/test_writers.py` | modify | low | `implementer_agent` | sonnet | medium | ✅ cd9dd0e |
| E8 | `tests/test_completeness.py` | modify | low | `implementer_agent` | sonnet | medium | ✅ 9d1633a |
| D1 | `docs/decisions/ADR-0006-run-journal-and-resume.md` | create | low | `doc_orchestrator` | sonnet | medium | ⏳ |
| D2 | `docs/decisions/ADR-0007-corpus-contract-v6.md` | create | low | `doc_orchestrator` | sonnet | medium | ⏳ |
| D3 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | sonnet | medium | ⏳ |
| D4 | `docs/0_SYSTEM_OVERVIEW.md` | modify | low | `doc_orchestrator` | sonnet | medium | ⏳ |

A row moves to `✅ <sha>` as its commit lands (`RA-08`: atomic local commits,
squash only at close).

---

## Why the two escalations

| # | Risk | Why `opus` / `high` rather than the `author` tier |
| :--- | :--- | :--- | 
| C1 | high | `__main__.py` is 421 lines and carries pre-existing complexity violations (`002-delivery-program.md:128`). The unit threads a `run_id`, opens a journal at an exact point in the sequence, adds two CLI arguments and a whole subcommand, and must add **no** new function over 50 lines or 3 indent levels. It is the one unit where the plan's constraint and the file's existing debt pull against each other |
| E5 | high | A schema break. v5 files exist on disk, and `ADR-0004` requires `complete` to stay derived from `completeness` so the two can never disagree. Getting v6 wrong is not caught by a linter and would be discovered only after a 15-hour run had written 910 files under it |

---

## Dependency order

Units are not independent, and the order below is a constraint on Phase 6, not a
suggestion. `no_interference` prevents two agents holding one file; this
prevents an agent holding a file whose dependency has not landed.

| Wave | Units | Blocked by | Why |
| :--- | :--- | :--- | :--- |
| 1 | A1, E2 | — | New modules with no dependency on the rest. Both are pure and fixture-testable in isolation |
| 2 | A2, E3 | A1, E2 | A test cannot import a module that does not exist |
| 3 | E1, E4, E5 | E2 | `E4` calls `timestamps.parse_rendered`; `E5` defines the v6 fields `E4` populates |
| 4 | E6, E7, E8 | E4, E5 | Assert against the v6 shape |
| 5 | B1 | A1 | `manifest_from_journal` consumes what `journal.read_journal` returns |
| 6 | B2 | B1 | — |
| 7 | C1 | A1, B1, E1, E5 | The orchestration point: it is the only unit that touches all four |
| 8 | C2, C3 | C1 | Assert against `--resume` and the journal-on-crash behaviour |
| 9 | D1–D4 | Every block above | An ADR written before the code it records describes an intention, not a decision |

**`E5` before `E4` inside wave 3** — `writers.py` defines `MessageRecord`, and
`history.py` populates it. Writing the consumer first means writing against a
type that does not yet have the fields.

---

## Amendment during Phase 6 — unit `E8`

`E8` was **not** in the approved table. It was added while executing `E5`, and
recording why matters more than the row itself.

`E5` raises `SCHEMA_VERSION` to 6. Two tests assert the literal `5`:
`tests/test_writers.py` (unit `E7`, planned) and `tests/test_completeness.py`
(**unplanned**). Phase 1 enumerated the test files by reasoning about which
ones touch the payload and missed the one whose subject is completeness but
which pins the schema number on the way past. Reproduce the full set:

```
grep -rln "SCHEMA_VERSION\|schema_version" tests/
```

This is **not** the third scope widening the plan's Cost section rules out. No
new capability is added: an approved unit necessarily breaks a file, and the
sprint cannot end green without it. The honest options were to amend this table
or to leave the suite red, and a lock file that omits a file the sprint edits is
the failure `task_scope.md` exists to prevent.

Total is now **19 units**, not 18. Every count in this file reflects that; the
Implementation Plan's Cost section is amended alongside it.

---

## File-collision audit (`no_interference`)

19 units, 19 distinct paths, zero shared:

```
python3 - <<'PY'
import re, pathlib
rows = re.findall(r'^\| [A-E]\d \| `([^`]+)`', pathlib.Path(
    'docs/sprints/009-backend-extractor/task_scope.md').read_text(), re.M)
print(len(rows), "rows;", len(set(rows)), "distinct paths")
PY
```

Expected: `19 rows; 19 distinct paths`.

---

## Rule audit

| Rule | Applies to | Verdict |
| :--- | :--- | :--- |
| `jurisdictional_lock` (1 file per subagent task) | All 19 | ✅ Satisfied — one path per row, no path repeated |
| `no_interference` | All 19 | ✅ Satisfied — see the audit above |
| `max_lines_per_func` 50 / `max_indentation` 3 | A1, C1, E2, E4, E5 | ⚠️ **Binding constraint, not a check.** `C1` is the risk: the plan forbids adding any function over 50 lines to a file that already violates it. Enforced at the Quality Gate |
| `ephemeral` (no `TODO`/`FIXME`) | All source units | ⚠️ Enforced at the Quality Gate — `ruff` does not reject these by itself |
| `code_logic` — strictly English | All 19 | ⚠️ The Implementation Plan is Spanish by permission (`§1 user_chat`); **every unit's code, docstring, log line and commit message is English** |
| `path_type` — relative only | A1, B1, E1 | ⚠️ `journal.py` and `session.py` both build paths under `data/`. `DEFAULT_DATA_DIR = Path("data")` is already relative; no absolute path may be introduced |
| `secret_sovereignty` / `RA-09` | All 19 | ✅ No unit reads `.env`. The sprint touches no credential |
| `RA-08` — atomic commits, squash at close | All 19 | ✅ One commit per unit on `ai-sprint/009` |
| `RA-12` — branch discipline | All 19 | ✅ Branch created at `d0cdbb4` before the first commit; no push to `main` during Execution |
| `historical_log` — `#009` suffix | All 19 | ✅ Enforced by `hooks/on_commit.py`, which requires `#\w+` |
| `ADR-0001` — no real names in `data/` | E5, and C1 via `--write-index` | ⚠️ **The one privacy-bearing constraint.** `§D5` keeps titles out of the run journal entirely; the title index stays a separate file behind `--write-index`. A v6 field carrying a title would breach this |
