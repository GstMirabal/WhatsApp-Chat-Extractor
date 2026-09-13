# Roadmap: WhatsApp Chat Extractor — delivery program

**Last Audit Sprint**: #010
**Last Audit Date**: 2026-09-13
**Last Audit Commit SHA**: `ai-sprint/009` tip; deployment pending for both Sprint 009 and 010

Program authority: [ADR-0001](../../decisions/ADR-0001-product-scope-whatsapp-web.md),
[ADR-0002](../../decisions/ADR-0002-delivery-program-and-layout.md),
[ADR-0003](../../decisions/ADR-0003-media-placeholders-in-export.md).

| Phase | Sprint | Status | Goal |
| :--- | :--- | :--- | :--- |
| P0 | 002 | CLOSED | Seal product + delivery ADRs, overview, this roadmap |
| P1 | 003 | CLOSED | Spike: one chat via WhatsApp Web → text JSON in `data/` |
| P2 | 004 | CLOSED | Happy path: full-history harvest, pseudonymous JSON, `/wa-export` |
| P2.5 | 005 | CLOSED | Corpus fidelity + operator surface: media placeholders, Cursor entry, README, LICENSE |
| P3a | 006 | **CLOSED (partial)** | Completeness criterion. **Measured**: `complete: true` is unreachable — `COMPLETE_REASONS` never fired across 5 conversations with the harvester's stall defect corrected. The goal as originally worded ("`chat_start` verified") turned out to be unachievable, which is the finding. `ADR-0004` and the schema change it governs were gate-withheld and carry into 007 |
| P3b | **007** | **CLOSED** | All chats: `export-all` enumerates the whole list, exports each and writes a run manifest. **Measured**: the chat list virtualizes (899 conversations behind a 70-row window), position is stable across a sweep and no two chats share a title, so the digest is the enumerator's key. `ADR-0004` decided completeness as three values and schema v5 carries it. Live-verified with `--limit 3`: 3 exported, 0 failed, 907 skipped of 910. **A whole-account run is ~15 hours**, which P4 should address before it is routine |
| P4 | **008** | **CLOSED (partial)** | Platform hardening, plus an unplanned defect fix that took the sprint's centre. **Measured**: the single-pass enumeration silently lost conversations whenever the chat list reordered (882 of 899 at one reorder per 5 reads, 856 at one per 2, no duplicates) while `enumeration_complete` reported `true`. `sweep_until_stable` recovers **899 of 899** at both rates; `ADR-0005` replaces the boolean with three values and manifest schema v2 carries it. Platform: the Actions **billing block cleared** and CI now executes for real, so `v0.8.0` is the first release with independent verification behind it — but branch protection still returns `403` on a private free-plan repository, so `ci_gate.py` still refuses. Released as `v0.8.0` |
| P5 | 009 | **CLOSED (partial)** | Corpus confidence and run resilience. **Delivered**: append-only run journal, `run_id` threading, `manifest_from_journal`, `--resume`, the `recover` subcommand and corpus contract v6 — 19 of 19 units, QA `APPROVED`, Tester `RECORD`. **Carried to 010**: `§D5`'s second append-only title journal (no unit assigned) and `§D6`'s intent that `__main__.py` not grow (421 → 793 lines). Hotfix `H-003` bounded a spinner stall that cost 8.3 hours per affected conversation, found in production |
| P6 | 010 | **CLOSED (partial)** | `wa-extract consolidate` folds every `data/chat_*.json` into one `data/corpus_<run_id>.ndjson`, verbatim, header-reconciled by construction after a Phase 7 fix. QA `RECORD` (two rounds), Tester `RECORD`. **Verified live against 1018 real files**: zero duplicate `chat_id`, exact provenance. **Found, not fixed**: `T-8` — the manifest's `started_at` is its last `--resume` pass, not the run's true start; 56% of conversations predate it. **Still carried**: `§D5`, `§D6`, `T-2`, `KI-009-H` — the plan deliberately excluded them, this row previously did not say so |
| — | — | OUT OF REPO | AI analysis (solicitudes, sentimiento), learning server, bot |

**The product scope is complete.** P0 through P3b are closed and `wa-extract
export-all` does what `ADR-0001` asked: one invocation exports every
conversation and the manifest states the outcome of each. P5 delivered
confidence in the corpus and survivability of a long run; P6 delivered the one
artifact a downstream reader can open instead of 1018 separate files. Neither
is new product capability. `§D5`, `§D6`, `T-2`, `KI-009-H` and `T-8` remain
carried and unscheduled — none blocks using the tool, and `KI-009-H` is the
only one that blocks a fully unattended run.

Restructured 2026-08-30 after Sprint 004 closed. P3 was one undifferentiated
"harden" row; splitting it separates a risk that must be retired alone (does a
single chat ever finish?) from work that only makes sense afterwards (do all of
them?). Sprint 005 exists because Sprint 004's own review found four declared
items that were never built, plus a product decision the live probe forced.

---

## Sprint 005 — P2.5 Corpus fidelity + operator surface

The smallest sprint remaining, and the one that changes daily use. Nothing here
is exploratory.

| # | Deliverable | Why now |
| :--- | :--- | :--- |
| 1 | Media placeholders (`kind` field, schema v4) | ADR-0003. Without it the corpus teaches adjacencies that never happened |
| 2 | `.cursor/commands/wa-export.md` | ADR-0001 declares Cursor as the operator surface; Sprint 004 shipped only `.claude/commands/` |
| 3 | `README.md` | `pyproject.toml:9` declares `readme = "README.md"` and the file is absent |
| 4 | `LICENSE` | `pyproject.toml:11` declares `Proprietary` with no file behind it |

Exit criterion: an export of one chat contains a record for every message
including media, each carrying a `kind`; `/wa-export` runs from a Cursor
session; a non-editable package build succeeds.

## Sprint 006 — P3a One chat, proven complete

The open risk carried out of Sprint 004: **`complete: true` has never been
produced.** Every live run was capped at 6–12 passes, so no run has reached the
beginning of a conversation and `CHAT_START_SELECTORS` is unproven.

| # | Deliverable | Why now |
| :--- | :--- | :--- |
| 1 | One uncapped run to a real chat start | The only thing that validates the start markers |
| 2 | `CHAT_START_SELECTORS` corrected against what that run observes | Probe-first, per `KI-004-A` |
| 3 | Resume after a mid-harvest failure | A dropped session currently loses the whole run |
| 4 | Documented limits: passes, wall time, message ceiling observed | ADR-0002 P3 requires a stated failure policy |

Exit criterion: an export with `stopped_reason: chat_start` and
`complete: true`, and a documented recovery path for an interrupted run.

**This sprint is where surprises are most likely.** Sprint 004 found five
defects only by running the code, and this is the first run that goes all the
way. Budget for that rather than for a clean pass.

## Sprint 007 — P3b All chats

Only meaningful once one chat is proven to finish.

| # | Deliverable | Why now |
| :--- | :--- | :--- |
| 1 | Chat list enumeration | The remaining half of ADR-0001's "all stored chats" |
| 2 | Per-chat failure policy: continue, retry, or abort | ADR-0002 P3 exit criterion |
| 3 | Run manifest: which chats exported, which failed, why | A dump of unknown completeness is not usable |
| 4 | Pseudonymous chat index the operator can map back | `chat_id` is a digest; without a local index no one knows which file is which chat |

Exit criterion: one invocation exports every chat, and the manifest states the
outcome of each.

## Sprint 008 — P4 Platform hardening, and the defect that displaced it

Planned as platform work. What the sprint actually turned on was an open defect
carried out of Sprint 007's own review: the enumerator lost conversations in
silence. That took the centre, and the platform row was re-probed rather than
applied.

| # | Deliverable | Outcome |
| :--- | :--- | :--- |
| 1 | CI actually executing | **DONE** — the billing block cleared 2026-09-01. Run `33598297247` passed four jobs with real steps (5–23 s, 5–8 steps each) against the old 2–5 s zero-step failures |
| 2 | Branch protection with the four required checks | **STILL BLOCKED** — `403`, *"Upgrade to GitHub Pro or make this repository public"*. A plan limitation, **not** a token scope problem, which the state anchor had recorded wrongly for four sprints |
| 3 | `/agents:harden`: secret scanning, Dependabot alerts, private vulnerability reporting | **NOT APPLIED** — read-only probe only. Each write either returns `403` on this plan or changes the repository's public posture, which is the owner's decision |
| 4 | `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `NOTICE.md` | **NOT DONE** — all four still absent; `LICENSE` is present. Unblocked, and still owed |
| 5 | Nucleus PRs for the upstream findings | **DRAFTED, NOT SUBMITTED** — eleven drafts now on disk (`_003`–`_013`); six written this sprint. The PR is a separate act in a separate clone (`§3 jurisdiction`) |

### Unplanned, and the reason the sprint mattered

| # | Delivered | Evidence |
| :--- | :--- | :--- |
| 1 | `sweep_until_stable` — repeat the sweep from the head, union by digest, stop when two consecutive sweeps add nothing | 899/899 at `every=5` **and** `every=2`, in 4 sweeps; confirmed again against an irregular fixture, not just the rotating one |
| 2 | `ADR-0005` — `enumeration` is `converged` \| `unconverged` \| `truncated`, failing closed | Deliberately offers no `proven`: unlike `ADR-0004`, no future signal could make it reachable |
| 3 | Manifest schema v1 → v2 | `enumeration_complete` removed, not derived |
| 4 | `scripts/probe_unknown_rows.py` | Built and tested; the **live run was not taken** — it needs an authenticated session |
| 5 | The Phase 7 gate-evidence deadlock diagnosed | `UPSTREAM_FINDING_013`: a `SubagentStop` hook demanded a `SPRINT_LOG` row the gate agents hold no tool to write, and the forced continuation overwrote ~178k tokens of evidence |

**Before making the repository public**: no exported conversation is committed
(`data/` gitignored since Sprint 003, and the CI job proves no file under it is
tracked), but contact names remain in the commit history and in Sprint 003/004
records. That review is a person's job and is a prerequisite, not a formality.

## Sprint 009 — P5 Corpus confidence and run resilience

Planned as run resilience. Widened once at Phase 1, by operator decision, to
carry a bounded corpus-schema change in the same pass — the whole-account run
that lands immediately after resume writes 910 files, so every missing field
would cost another ~15-hour retrofit. Groups, quoted replies and reactions were
refused in the same breath (`KI-004-A`: no correction without measurement). 19
of 19 units landed; QA `APPROVED`, Tester `RECORD`; suite 224/1 → 277/1. Two
parts of the approved plan were never reached and carry to Sprint 010.

| # | Deliverable | Outcome |
| :--- | :--- | :--- |
| 1 | Run `scripts/probe_unknown_rows.py` live, then classify the `unknown` rates | **NOT DONE** — the plan opened resume-only and was widened to corpus contract v6 instead; the operator-gated probe run was not taken and is not scheduled |
| 2 | Resume after a mid-run failure | **DONE** — an append-only run journal with `fsync`, `run_id` threaded through the run, `manifest_from_journal` reconstruction, the `--resume` flag, the `recover` subcommand and crash-to-journal orchestration all shipped (`ADR-0006`, `ADR-0007`) |
| 3 | Corpus contract v6 (added to scope at Phase 1) | **DONE** — `message_id`, `timestamp_iso`, pinned locale, recorded timezone, `passes_used` and `undated_messages` now land on every exported record |

**Carried to Sprint 010** (`SPRINT_LOG.md` Phase 8, `RA-05`): `§D5` — the
second append-only title journal `data/chat_index_<run_id>.ndjson` the design
note specified and no work unit was assigned, so `manifest.write_chat_index`
still writes one batched object at the end of a run; `§D6` — `__main__.py` grew
421 → 793 lines when the CLI orchestration landed in the file the note was
written to protect; test gap `T-2` — `_request_timezone` and `_confirm_timezone`
have no tests, deferred because Sprint 010 may rewrite them; and `KI-009-H` —
the harvest loop has no wall-clock timeout.

### Unplanned — hotfix H-003

| # | Delivered | Evidence |
| :--- | :--- | :--- |
| 1 | `loading_grace` bounds the spinner suppression in `decide_stop`, and a new `loading_unresolved` stop reason ends the harvest honestly once the bound is exceeded | `panel_is_loading` stays true whenever the paired phone never answers a load-earlier request, so the stall branch could never fire and an affected conversation would burn 8.3 hours (2000 passes × 15 s) before the run moved on. Found in production on 2026-09-08, not in review — the suite runs without a browser and no test can hang on a live page. The run diagnosed was 4 h 24 m into one such stall at pass 890 (stall 889/3). Suite 278/1 → 283/1; branch `hotfix/H-003` → `1728519`, merged into `ai-sprint/009` at `d157676` |

**What no sprint will fix.** `ADR-0004` established that `complete: true` is
unreachable — no conversation can demonstrate it reached its beginning. That is
a property of WhatsApp Web's DOM, not an outstanding task, and `ADR-0005`
extends the same honesty to enumeration: convergence is evidence, never proof.

**Before making the repository public**: no exported conversation is committed
(`data/` gitignored since Sprint 003, verified by `git log --all --diff-filter=A -- data/`),
but contact names remain in the commit history and in Sprint 003/004 records.
That review is a person's job and is a prerequisite, not a formality.

## Sprint 010 — P6 Corpus consolidation

Approved and closed 2026-09-13. The plan the operator approved deliberately
narrowed scope to consolidation alone — its own "Out of scope" table names
`§D5`, `§D6`, `T-2` and `KI-009-H` and routes each back to a future sprint
rather than settling them here, which this row previously did not say.

| # | Deliverable | Outcome |
| :--- | :--- | :--- |
| 1 | `wa-extract consolidate`: reads every `data/chat_*.json`, checks all carry schema v6 with no repeated `chat_id`, writes one `data/corpus_<source_run>.ndjson` (header line, then one verbatim v6 export per line) | **DONE.** 6/6 units, QA `RECORD` (two rounds — a real `§D2` header/body reconciliation defect found by execution and fixed, then a `str.splitlines()` counting fragility in the proving test itself, also fixed), Tester `RECORD` (real-data run against all 1018 production files: zero duplicate `chat_id`, exact provenance, both aborts and both flags confirmed). Suite 283/1 → 294/1 |
| 2 | `§D5` — the title-index journal decision | **NOT DONE.** Explicitly out of scope in the approved plan; still carried |
| 3 | `§D6` — `__main__.py` orchestration size | **NOT DONE.** Same; still carried |
| 4 | `T-2` — timezone function tests | **NOT DONE.** Same; still carried, same reasoning (a rewrite may still be coming) |
| 5 | `KI-009-H` — wall-clock deadline for the harvest loop | **NOT DONE.** Same; still carried, still blocking a fully unattended run |
| 6 | Systemic wall-clock-bound amendment (`H-003 §5`) | **NOT DONE.** Still pending `constitutional_escalation` |

### Unplanned — `T-8`, found validating against real data

The Tester gate ran `consolidate` against the real 1018-file production corpus
and found the credited manifest's `started_at` is the timestamp of its
**last** `--resume` pass, not when the run began: `journal.read_journal`
overwrites `header` on every header record it walks, so a journal holding five
resume headers keeps only the most recent. **570 of 1018 conversations (56%)
carry an `exported_at` earlier than the date their own manifest claims the run
started.** No conversation's own content or identity is wrong — only the
run-level metadata. Carried, not hotfixed: unlike `H-003`, nothing operational
is blocked by it.

Exit criterion, met: `wa-extract consolidate` (no arguments) produced
`data/corpus_20260902T214002Z.ndjson` whose conversation count equaled the
1018 real `data/chat_*.json` files read, every line after the header validated
as a schema-v6 export, and no `chat_id` repeated across inputs.

---

## Phase notes

| Phase | In | Out |
| :--- | :--- | :--- |
| P0 | Decisions only (no product code) | Playwright, `src/`, live dump |
| P1 | Minimal package + Playwright proof on Mac | All-chats dump, Cursor skill polish |
| P2 | Agent orchestration command; scripts do the work; full history per chat | Sentiment/bot; perfect resilience; all-chats dump |
| P2.5 | Media placeholders, Cursor entry, packaging metadata | Any change to the harvest loop |
| P3a | Proving one chat completes; recovery | Enumerating chats |
| P3b | All chats; manifest; failure policy | Downstream AI products |
| P4 | Platform controls and upstream contributions | Product features — **the sprint departed from this** |
| P5 | Measuring the `unknown` rates; surviving a 15-hour run | New capability; anything `ADR-0001` did not ask for |
| P6 | Folding the v6 per-chat exports into one corpus file; the Sprint 009 carries, including a wall-clock bound for the harvest loop | Re-harvesting or re-exporting any conversation; new capability beyond consolidation |

**P4's exclusion did not hold, and saying so is the point.** The row reads *"Out:
Product features"*, and Sprint 008 shipped `sweep_until_stable`, `ADR-0005` and
a manifest schema break — product work by any reading. It was the right call: an
enumerator that loses conversations in silence invalidates the corpus the whole
program exists to produce, and deferring it to hold a phase boundary would have
protected the boundary at the expense of the product. Recorded as a deliberate
departure rather than quietly reworded, because a phase table edited to match
whatever happened stops constraining anything.
