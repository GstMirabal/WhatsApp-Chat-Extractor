# 📝 Sprint Log: #009

**Stack / Layer**: `backend` / `extractor`
**Branch**: `ai-sprint/009` · **Base**: `main` at `d0cdbb4` (`v0.8.1`)
**Plan**: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — committed at `a4a22df`, approval pending Phase 5

---

## 🚦 Session Metadata

| Field | Value |
| :--- | :--- |
| Session tool | `claude-code` |
| Delegation mode | `native` |
| Anchor session | `20260902T085030Z-72792` (session #15, block A+E) · `20260902T114129Z-26951` (session #16, resumed at the block B boundary) |
| Context ratio | `4.1` at Phase 1 open → `7.8` at Phase 3 close (peak 192.467) |
| Baseline suite at branch point | 224 passed, 1 skipped, `ruff check .` exit `0` |
| Boot | `session_start.py --boot` refused again (`UPSTREAM_FINDING_004` / `_008`, third and fourth instance at session #15; fifth at session #16, same dead nucleus lock `20260827T154222Z-45916`). Binding steps run individually from the host root, both times |

**Boot detail.** `--boot` refused with a session lock held by
`20260827T154222Z-45916`, a Cursor session **in the nucleus checkout** dated
2026-08-27 whose PID is dead. That lock is unrelated to this project: `--boot`
resolves `repo_root()` as the parent of `scripts/` and forces `cwd=root` on every
child, so in submodule mode it reads and writes `.agents/docs/active_state.json`
rather than the host anchor. No `--takeover` was issued — it would have seized
the wrong anchor. The host anchor was claimed directly with
`session_state.py claim` from the host root.

---

## 🏁 Sprint Progression

| Block | Units | Subject | Status |
| :--- | :--- | :--- | :--- |
| A | A1–A2 | Append-only NDJSON run journal with `fsync` | ✅ |
| E | E1–E8 | Corpus contract v6: `message_id`, `timestamp_iso`, pinned locale, recorded timezone, `passes_used`, `undated_messages` | ✅ |
| B | B1–B2 | Manifest reconstruction from a journal; `run_id` threading | ✅ |
| C | C1–C3 | `--resume`, the `recover` subcommand, and the crash-to-journal orchestration | ✅ |
| D | D1–D4 | `ADR-0006`, `ADR-0007`, Blueprint, System Overview | ✅ |

**19 of 19 units landed.** Suite 277 passed / 1 skipped, from a 224/1 baseline
(`+53`, none removed); `ruff check .` exit `0`. Phase 6 Execution is complete;
Phase 7 has not run.

**Two parts of the approved plan did not ship, and unit `D1` found both while
writing the ADR that was supposed to record them.** Neither is a defect in the
code that landed; both are gaps between the plan the human approved at Phase 5
and the work the units were given.

| Plan | What §D1-§D10 specified | What shipped |
| :--- | :--- | :--- |
| `§D5` | A second append-only journal, `data/chat_index_<run_id>.ndjson`, written under `--write-index` with the same append discipline as the outcomes journal | `manifest.write_chat_index` still writes one batched JSON object at the end of the run. A crash before that call loses the whole pass's titles, not a torn last line. **No work unit was ever given this to build**: `A1`'s row names `open_journal`, `write_header`, `append_outcome` and `read_journal` and no chat-index journal, so the design note had no implementer |
| `§D6` | The large files "only call" the new modules | `journal.py` and `timestamps.py` exist and `export_one.py` was left untouched as planned, but `__main__.py` grew from 421 to 793 lines. Only the line-level journal I/O moved out; the CLI orchestration landed in the file the note was written to protect |

`C1`'s `_titles_for_index` is a consequence of the first: with no append journal
for titles, threading `run_id` into the batched writer made every pass of one
run truncate the same file, and that fold-in is the repair.

**Both are carried to Sprint 010 by human decision at session #16**, taken with
the gaps described as they are above. Neither is closed in Sprint 009, and
neither plan text is amended to match the code — `§D5` and `§D6` stand as
written, with this log recording that the sprint did not reach them. Phase 8
carries both into `docs/roadmaps/docs/extractor/002-delivery-program.md` under
`RA-05`:

| Carried | What Sprint 010 must decide |
| :--- | :--- |
| `§D5` | Whether the title index becomes the append-only `chat_index_<run_id>.ndjson` the note specifies, and whether `_titles_for_index` is then withdrawn as redundant |
| `§D6` | Whether the run orchestration leaves `__main__.py` for a module of its own, and what line ceiling the file is held to afterwards |

**Unit `C1` deviated from its row in five places**, each because the file
disagreed with the plan, and each recorded in the commit body of `b068d1a`
rather than left to be inferred from the diff. Four are corrections the row
would have wanted: a second `build_export` call in `cmd_export_one` that the
row did not mention and that would otherwise have written v6 files with
`passes_used=0`; a title-index fold that repairs a defect threading `run_id`
introduced; `_latest_per_chat`, without which a resumed conversation counts as
failed and exported at once; and exit `3` for a run that recorded fewer
conversations than it enumerated.

**The fifth is a limitation and is recorded as one.** `--timezone` cannot
impose a zone: `session.launch_context` accepts no `timezone_id` and
`session.py` belongs to unit `E1`, so the flag asks through the environment
Chromium inherits and may do nothing. Nothing false can be recorded from it —
`source_timezone` always states what the page resolved, and a mismatch warns —
but an operator learns the request was ignored only from that warning. A true
imposition needs a `timezone_id` parameter on `launch_context`, which is a
change to another unit's file and belongs to Sprint 010.

Execution paused at the block E boundary with the context ratio at `12.9`, below
the `15×` hard threshold rather than after it (`rules/token_economy.md` §3). The
reasoning is in `IMPLEMENTATION_PLAN.md` § Cost: `C1` is the sprint's only
high-risk resume unit, and writing it across the hard threshold is the one place
degradation would cost most.

Unit-level state lives in [`task_scope.md`](task_scope.md); a row moves to
`✅ <sha>` as its commit lands.

**Scope was renegotiated once, deliberately, between Phase 1 and Phase 3.** The
plan opened as resume only (10 units). The operator asked whether the corpus
schema should join it, and the answer was yes for a bounded subset: what lands
immediately after resume is a whole-account run writing 910 files, so every
missing field costs another ~15 hours to retrofit. Groups, quoted replies and
reactions were refused in the same breath — unmeasured, and `KI-004-A` forbids
correcting what has not been measured. **A third widening is out of order** and
goes to Sprint 010 (`IMPLEMENTATION_PLAN.md` § Cost).

---

## 🔍 Phase 7 — Double-Gate Review

Gates emit; the Orchestrator transcribes (`config/artifact_registry.json`).

| Gate | Round | Verdict | Class | Notes |
| :--- | :--- | :--- | :--- | :--- |
| QA (structural) | 1 | `REJECTED` | `charter` | `manifest.py::manifest_from_journal` 54 lines against `max_lines_per_func` 50, new this sprint and undisclosed. **Scan covered three files and returned a verdict as if it had covered the sprint** |
| QA (structural) | 2 | `REJECTED` | `charter` | `tests/test_resume.py` test function 51 lines. Scan widened to all modules and all touched tests |
| QA (structural) | 3 | `APPROVED` | `charter` | 470 functions across 25 files, both axes of the rule. Zero sprint-introduced violations; the three remediations verified as pure extractions |
| Tester (functional) | 1 | `RECORD` | `testifying` | 277 / 1 with zero regression against `d0cdbb4`; `recover`-without-Playwright and all four exit-code cases reproduced independently. Two coverage gaps recorded, neither bouncing a green suite |

**The tester verified rather than read.** It shadowed `playwright` with a module
raising `ImportError`, confirmed the real package is installed and importable
first, and only then ran `recover` under the shadowed path — so "no browser
needed" is an observation, not an inference from where an import statement
sits. It called `_run_exit_code` directly with four constructed manifests. And
it checked the 11 removed test lines one hunk at a time to confirm each was
replaced by an equal or stronger assertion, since a loosened test is a
regression the suite cannot report.

### Gate 2 findings — two coverage gaps

| # | Mechanism | Consequence if it breaks |
| :--- | :--- | :--- |
| `T-1` | `__main__.py::_latest_per_chat` (lines 440-458) — no test references it | **Proven by mutation.** A journal holding `exported(Ana)`, `failed(Beto)`, `exported(Beto)` — a conversation that failed and then succeeded on retry — collapses correctly to 2 chats, 0 failed, exit `0`. Replacing `_latest_per_chat` with the identity function yields 3 chats, 1 failed, **exit `3`**: a run that succeeded reports as failed, and nothing in the suite notices |
| `T-2` | `__main__.py::_request_timezone` and `_confirm_timezone` (371-408) | A broken mismatch comparison, or a failure to set `os.environ["TZ"]`, passes the full suite. Both are as mockable as `sweep_until_stable` already is in `tests/test_resume.py` |

`T-1` is the sprint's headline capability left unexercised: retrying a
conversation that failed is the reason `--resume` exists, and the one path that
distinguishes a resumed run from a fresh one is the path no test walks.

**`T-1` is closed at `998603c`; `T-2` is carried to Sprint 010.** `RECORD` does
not block, so closing `T-1` was a human decision at session #16 rather than a
requirement — taken because the sprint's headline capability was untested and a
whole-account run was about to start on top of it. The new case drives the real
`cmd_export_all` rather than the private helper, and was verified by mutation
twice independently: replacing `_latest_per_chat` with the identity fails that
test alone and leaves the other 277 green. Suite 278 passed / 1 skipped.

`T-2` goes to Sprint 010 with a reason, not by default: it covers the two
timezone functions that Sprint 010 will rewrite outright when `launch_context`
gains a `timezone_id` parameter (`§D7`, carried above). Tests written now would
have a known expiry date.

**`KI-009-F` was examined and found inert, not merely accepted.** The tester
checked whether the skip-ordering caveat has a reachable consequence and
established it does not: outcomes are written by a single sequential walk over
`enumerated_refs` in index order, so the only reachable gap is a trailing one,
where append-at-end and append-at-gap are the same list; and `read_journal`
raises rather than continuing past a corrupted mid-file line, so corruption
cannot manufacture a middle gap either. `KI-009-G` was likewise confirmed to
fail closed — `recover --run-id nonexistent_run` exits `1` with a clear message
rather than crashing or reporting false success.

**Model tier deviation.** `task_scope.md` records the gate tier as `opus`/`high`.
The first `opus` attempt was killed mid-run by an API session limit, and every
gate round after it ran on `sonnet`. Recorded rather than left to be inferred
from a timestamp: a gate that ran below its declared tier is a fact about the
certification, not about the code. Each round stated that no finding it made
required escalated-tier judgment — all reduced to AST measurement, signature
inspection or a diff against `d0cdbb4`.

**Three violations of one rule, and what found them.** All three were
`max_lines_per_func`, which `ruff` cannot catch because this project arms no
function-length rule — the check lives on the gate for exactly that reason.

| # | Function | Lines | Introduced by | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `manifest.py::manifest_from_journal` | 54 | `B1`, this session | `1f82981` — extracted `_with_reconstructed_skips`; 44 |
| 2 | `writers.py::build_export` | 59 | `E5`, session #15 | `ab8454a` — extracted `_derive_computed_fields` and `_assemble_export_payload`; 47 |
| 3 | `tests/test_resume.py` resume case | 51 | `C3`, this session | `68c550d` — extracted a `browserless_run` fixture; 25 |

**Number 2 is the one worth remembering.** It was not found by a gate. Round 1
scanned `manifest.py`, `__main__.py` and `export_one.py`, and `writers.py` was
not among them; the Orchestrator found it while verifying round 1's finding and
widening the scan. `build_export` was 40 lines at `d0cdbb4` and reached 59 when
`E5` added the v6 fields, so the violation had already survived a block close, a
diff review and one gate. **A verdict over an undeclared subset is worse than no
verdict, because it reads as if it covered everything.** Rounds 2 and 3 were
required to enumerate the files they scanned; round 3 scanned 25 and listed all
25.

No remediation weakened anything to satisfy a line count. Both source fixes were
pure extractions with the suite unchanged at 277 / 1, and the test fix kept all
six of its assertions — the one way that repair could have gone wrong.

`RA-17`: each row emits `APPROVED` | `REJECTED` | `RECORD` with class
`charter` / `instructing` / `testifying`. `RECORD` does not count toward the
three-strike escalation to `remediation_workflow.md`.

---

## 🧠 Rule Amendments & Heuristic Harvest

Indexed into `memory_index.json` at the close, each carrying a `routing_class`.

| # | Finding | Class | Destination |
| :--- | :--- | :--- | :--- |
| `KI-009-A` | Both boot defects were re-derived from scratch before anyone checked `docs/audits/` — the findings were already written, in this repository, by earlier sprints of this same project | `host` | `memory_index.json` |
| `KI-009-B` | `UPSTREAM_FINDING_003` and `_004` were observed against pin `v4.23.0` and persist under `v4.24.0`; a pin bump is not evidence a finding was addressed | `nucleus` | Recurrence line appended to both existing drafts |
| `KI-009-C` | A field computed for internal use and discarded at the serialization boundary is invisible to every reviewer who reads only the payload type (`message_id`, `history.py:166-179`) | `host` | `memory_index.json` |
| `KI-009-D` | Renegotiating scope after the plan is written costs more than planning the wider scope once: ratio 4.1 → 7.8 in a single phase | `host` | `memory_index.json` |
| `KI-009-G` | `_manifest_from_journal_file` reports a journal that does not exist as one that "holds no header record", so an operator who mistypes a `run-id` is told the file is malformed rather than absent. Found while verifying `C1`; unit `C3` was told to assert on the exception type and never on that wording, so no test pins a message that should be corrected | `host` | `memory_index.json` |
| `KI-009-F` | `manifest_from_journal` appends reconstructed skips in enumeration order **after** the recorded outcomes, not at the position each gap occupies. Identical to insertion order for the trailing gap a crash produces, and only observable if a journal ever held a non-contiguous gap — which `_export_every_chat` appending once per iteration cannot produce unless an append itself failed. Recorded because a later unit may assume the list is in enumeration order and would be wrong for a reason no test covers | `host` | `memory_index.json` |
| `KI-009-E` | `detect_drift.py` exits `2` on every resume of an in-flight sprint: it splits `last_close_commit..HEAD` against **sealing tags** only, and a sprint's own commits are uncovered by construction until Phase 8 writes the ledger entry and deployment seals it. Observed at session #16 start — 19 commits, all `#009`, all on `ai-sprint/009`, all recorded in this log, reported as "outside the protocol". The verdict is structurally unreachable in the healthy mid-sprint case, which is the state `session_state.py claim` calls `SUSPENDED` and resumes | `nucleus` | New upstream finding draft at `extract` |

*Rows are candidates recorded as they are found; the harvest closes at Phase 8.*
