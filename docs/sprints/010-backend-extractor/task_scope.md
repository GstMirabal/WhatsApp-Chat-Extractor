# 🔒 Task Scope: Sprint #010

**Plan**: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)

One physical file per unit. No two units share a file.

## Model and Effort

`config/model_tiers.json` under `claude_code`:

| Tier | Model | Effort | Profiles |
| :--- | :--- | :--- | :--- |
| `author` | `sonnet` | `medium` | `implementer_agent`, `doc_orchestrator` |
| `gate` | `opus` | `high` | `qa_agent`, `tester_agent` |

No unit is escalated: nothing here is high-risk. `consolidate.py` is a new,
pure, fixture-testable module; the `__main__.py` change is wiring only.

## Work table

| # | File | Operation | Risk | Assignee | Model | Effort | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| A1 | `src/whatsapp_chat_extractor/consolidate.py` | create | medium | `implementer_agent` | sonnet | medium | ⏳ |
| A2 | `tests/test_consolidate.py` | create | low | `implementer_agent` | sonnet | medium | ⏳ |
| B1 | `src/whatsapp_chat_extractor/__main__.py` | modify | low | `implementer_agent` | sonnet | medium | ⏳ |
| B2 | `tests/test_consolidate_cli.py` | create | low | `implementer_agent` | sonnet | medium | ⏳ |
| C1 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | sonnet | medium | ⏳ |
| C2 | `docs/walkthroughs/EXTRACTOR_WALKTHROUGH.md` | modify | low | `doc_orchestrator` | sonnet | medium | ⏳ |

A row moves to `✅ <sha>` as its commit lands.

## Dependency order

| Wave | Units | Blocked by | Why |
| :--- | :--- | :--- | :--- |
| 1 | A1 | — | New module, no dependency |
| 2 | A2, B1 | A1 | A2 imports the module; B1 wires the CLI to it |
| 3 | B2 | B1 | Asserts against the `consolidate` subcommand |
| 4 | C1, C2 | A1, B1 | An ADR/blueprint written before the code describes an intention |

## File-collision audit (`no_interference`)

6 units, 6 distinct paths, zero shared. `EXTRACTOR_BLUEPRINT.md` and
`EXTRACTOR_WALKTHROUGH.md` were touched by Sprint 009's Phase 8 closeout;
that work is committed at `8128086` and these edits are additive to it.

## Rule audit

| Rule | Applies to | Verdict |
| :--- | :--- | :--- |
| `jurisdictional_lock` (1 file per subagent task) | All 6 | ✅ one path per row, none repeated |
| `no_interference` | All 6 | ✅ see audit above |
| `max_lines_per_func` 50 / `max_indentation` 3 | A1, B1 | ⚠️ enforced at the Quality Gate — the rule that rejected Sprint 009 three times |
| `ephemeral` (no `TODO`/`FIXME`) | A1, B1 | ⚠️ enforced at the Quality Gate |
| `code_logic` — strictly English | All 6 | ⚠️ plan is Spanish by permission; every unit's code, docstring, log line and commit is English |
| `path_type` — relative only | A1, B1 | ⚠️ `DEFAULT_DATA_DIR = Path("data")` is relative; introduce no absolute path |
| `secret_sovereignty` / `RA-09` | All 6 | ✅ no unit reads `.env` |
| `ADR-0001` — no real names in `data/` | A1, A2 | ⚠️ the corpus stays pseudonymous; no `chat_index` merge |
| `RA-08` — atomic commits | All 6 | ✅ one commit per unit |
