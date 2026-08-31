# 📝 Sprint Log: #007

**Session Tracker**: `20260831T053506Z-60338` (session #12; succeeds
`20260830T165951Z-13948`, which suspended cleanly at Sprint 006 close)
**Role Active**: Principal Agent (`session_tool: claude-code`, `delegation_mode: native`)

---

## 🚦 Session Metadata

| Parameter | Value |
| :--- | :--- |
| **Active Layer** | backend / extractor |
| **Strategic Goal** | P3b «All chats»: enumerate every conversation, export each, and state each outcome in a run manifest — carrying `ADR-0004`, the completeness contract Sprint 006's Approval Gate withheld |
| **Intelligence State** | No knowledge graph. `graphify` cannot start in this host (`.agents/venv_skillopt` absent) — carried since #004 |
| **Start Time** | 2026-08-31T05:35:06Z |
| **Base** | `main` at `c3e827a` (v0.6.0) |
| **Branch** | `ai-sprint/007` |
| **Framework pin** | `.agents` v4.23.0 → **v4.24.0**, committed as `5f9ac3e` |

---

## 🏁 Sprint Progression

- [x] **Objective 0 — Open the sprint**
    - `[x]` Session claimed from the host root. `session_start.py --boot` again
      could not claim a host anchor (`UPSTREAM_FINDING_008`, re-verified unfixed
      at pin `v4.24.0`: `session_start.py:46` still resolves the root as the
      parent of `scripts/` and every subprocess still runs with `cwd=root`)
    - `[x]` Drift check exit `0` — `main` matches the sealed close `c3e827a`
    - `[x]` Bridge locks refreshed for both targets. `install.sh` deliberately
      **not** run: `UPSTREAM_FINDING_012` is unfixed at `v4.24.0` and re-running
      it deletes the tracked host command `.cursor/commands/wa-export.md`
    - `[x]` Framework pin bumped to `v4.24.0` and committed (`5f9ac3e`), the one
      crossover entry `agents.md §0` allows between the two ledgers
    - `[x]` `IMPLEMENTATION_PLAN.md` written at the canonical path and committed
      (`dd815a6`) — `triple_lock` lock 1
    - `[x]` **Phase 1 plan audit reproduced for the first time in this host**:
      `python3 skills/token-saver-auditor/scripts/audit_plan.py …` → `[OK]`,
      exit `0`. Sprint 006 could not run it and recorded so honestly; the script
      was never at `.agents/scripts/` — it ships inside the
      `token-saver-auditor` skill, which resolves the anchor's `audit_plan_missing`
    - `[x]` Phase 2 environment: `ruff check .` clean, `pytest tests/ -q` →
      **116 passed, 1 skipped** (the sprint-open baseline)
    - `[x]` **Harness misrecorded and corrected mid-session.** The anchor was
      claimed `cursor`/`sequential`; the session is Claude Code. Cause is the
      Sprint 041 defect fixed in the very bump this session applied —
      `commands/start.md` hardcoded `--tool cursor` for both harnesses until
      `v4.24.0`, and the command text arrived from the `v4.23.0` mirror. Anchor
      now reads `claude-code`/`native`; `RA-18` does not apply; Phase 4 model
      tiers rewritten off `config/model_tiers.json` `claude_code`
    - `[x]` **Approval Gate (Phase 5) — FULL APPROVAL, human, 2026-08-31**:
      all four blocks (W1–W15) authorized, and `ADR-0004` confirmed as Option C
- [x] **Objective 1 — Decide and pin the completeness contract (W1–W4)** — *landed*
    - `[x]` `ADR-0004` (`5447312`): Option C, `completeness: proven | unproven |
      truncated`, chosen against Sprint 006's measurement rather than alongside it
    - `[x]` `history.classify_completeness` (`7a94f73`) — pure, fails closed: an
      unrecognised stop reason is `truncated`, never `proven`
    - `[x]` `writers.py` schema v5 (`08b03ee`); `complete` retained and **derived**
      from `completeness == "proven"`, so the two cannot disagree
    - `[x]` `tests/test_completeness.py` (`f27da4b`), written first and observed
      failing (`ImportError`) before the implementation existed (`code_craft §6`)
    - `[x]` `tests/test_writers.py` migrated v4 → v5 (`cbceafb`, W3a) — eleven of
      its cases asserted the old contract literally
    - `[x]` `__main__.py` (`ea3a878`, W11a): **only `truncated` exits non-zero.**
      Under the v4 boolean this branch fired on every export ever produced,
      telling the operator each run had failed and to raise a cap that was not
      the cause
    - `[x]` Block tip verified: `ruff` clean, **128 passed, 1 skipped**
- [~] **Objective 2 — Measure the chat list (W5–W6)** — *code landed; the run is the operator's*
    - `[x]` `scripts/probe_chat_list.py` (`f0e2dda`): measures (Q1) whether
      `#pane-side` virtualizes and (Q2) whether a chat's index survives a
      re-reading. Reads titles only to hash them; no title, and no message body,
      reaches the report
    - `[x]` `tests/test_probe_chat_list.py` (`f30cb48`, W5b): the Phase 4.3 table
      shipped W5 with no test row — the identical omission Sprint 006 made for
      W1. The commit hook did not catch it this time because it guards `fix(`
    - `[x]` `CHAT_LIST_PROBE_NOTES.md` (`497edae`) with **empty** evidence
      tables. They stay empty until the probe runs
    - `[ ]` **Operator action required**: run
      `.venv/bin/python3 scripts/probe_chat_list.py --scroll-passes 20`. It cannot
      run unattended (real login, real conversations)
    - `[ ]` Fill §3 and §4 of the notes from the JSON report
- [🚧] **Objective 3 is blocked on Objective 2, by design.** `IMPLEMENTATION_PLAN.md`
  §D2 states that W7 is not written until W6 carries numbers. Writing the
  enumerator against an unmeasured DOM is `KI-004-A`, which this project has paid
  for three times
- [ ] **Objective 3 — Enumerate, export, declare (W7–W11)** — *gated on Objective 2*
    - `[ ]` `chat_list.py`, `manifest.py`, `export-all`, per-chat failure policy
- [ ] **Objective 4 — Document (W12–W15)**
    - `[ ]` Blueprint, README, System Overview, Master Ledger

---

## 🔍 Phase 7 — Double-Gate Review

Not run yet. Execution authorized 2026-08-31; gates run after the blocks land.

| Gate | Round | Verdict | Class | Notes |
| :--- | :--- | :--- | :--- | :--- |
| — | — | — | — | Pending execution |

---

## 🧠 Rule Amendments & Heuristic Harvest

| Friction Point | Resolution / Workaround | KI ID | routing_class |
| :--- | :--- | :--- | :--- |
| `audit_plan.py` was cited by three Sprint 006 artifacts and resolvable by none, because every citation pointed at `.agents/scripts/` | The script ships inside the `token-saver-auditor` skill. Cite `skills/token-saver-auditor/scripts/audit_plan.py`, which `pipeline_workflow.md` Phase 1 already does | `KI-007-A` | `host` |
| A pin bump applied at Phase 1 changed the harness contract mid-session: the `/agents:start` text was rendered from `v4.23.0` and claimed the anchor as the wrong tool, while `v4.24.0` — installed seconds later — was the release that fixed exactly that | Re-read the harness-sensitive command after any `sync_agents_pin.py` bump, before trusting a flag copied out of it. The pin moved between reading the instruction and acting on it | `KI-007-B` | `host` |

---

## ⚓ Documentation Entry Point Seal

**Strategic Lock**: `triple_lock` — plan written, committed and audited
(exit `0`) · Active Sprint `ai-sprint/007` · **Human OK granted 2026-08-31** ·
QA + Tester verdicts outstanding.

**Next Phase**: Phase 6 Execution is **paused on an operator action**, not on a
decision. Blocks A and B are committed; block C is gated on the probe run, and
that run requires the operator present (real login, real chats, real personal
data) and cannot be wrapped in an unattended routine.
