# Roadmap: WhatsApp Chat Extractor — delivery program

**Last Audit Sprint**: #008
**Last Audit Date**: 2026-09-02
**Last Audit Commit SHA**: `e0e1a4f` (`v0.8.0`)

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
| P5 | 009 | **PROPOSED** | Corpus confidence and run resilience — see below. Not a capability gap: `export-all` already satisfies `ADR-0001` |
| — | — | OUT OF REPO | AI analysis (solicitudes, sentimiento), learning server, bot |

**The product scope is complete.** P0 through P3b are closed and `wa-extract
export-all` does what `ADR-0001` asked: one invocation exports every
conversation and the manifest states the outcome of each. What P5 proposes is
confidence in the corpus and survivability of a long run, not new capability.

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

## Sprint 009 — P5 Corpus confidence and run resilience (PROPOSED)

Not yet planned or approved. Two units, and the ordering matters: the first
produces the data the second does not need, so they are independent and either
can be dropped.

| # | Deliverable | Why now |
| :--- | :--- | :--- |
| 1 | Run `scripts/probe_unknown_rows.py` live, then classify | `sender: unknown` at 3.9% (5 of 129) and `kind: unknown` at 9.6% (30 of 311) in the #007 live run, causes unmeasured. `KI-004-A` forbids classifying without the data; the instrument exists and is operator-gated |
| 2 | Resume after a mid-run failure | Sprint 006's deliverable 3, never implemented. `manifest.py` says so in its own docstring: the data model allows it, the code does not do it. A whole-account run is **~15 hours**, and the manifest is written only at the end — so a crash at hour 12 leaves the exported files orphaned with no record of which is which |

Carried, not scheduled: test gaps `F-4` (`cmd_export_all` exit condition, needs
a Playwright harness) and `F-6`; five pre-existing complexity violations in
`export_one.py` and `__main__.py`; the nucleus PR.

**What no sprint will fix.** `ADR-0004` established that `complete: true` is
unreachable — no conversation can demonstrate it reached its beginning. That is
a property of WhatsApp Web's DOM, not an outstanding task, and `ADR-0005`
extends the same honesty to enumeration: convergence is evidence, never proof.

**Before making the repository public**: no exported conversation is committed
(`data/` gitignored since Sprint 003, verified by `git log --all --diff-filter=A -- data/`),
but contact names remain in the commit history and in Sprint 003/004 records.
That review is a person's job and is a prerequisite, not a formality.

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

**P4's exclusion did not hold, and saying so is the point.** The row reads *"Out:
Product features"*, and Sprint 008 shipped `sweep_until_stable`, `ADR-0005` and
a manifest schema break — product work by any reading. It was the right call: an
enumerator that loses conversations in silence invalidates the corpus the whole
program exists to produce, and deferring it to hold a phase boundary would have
protected the boundary at the expense of the product. Recorded as a deliberate
departure rather than quietly reworded, because a phase table edited to match
whatever happened stops constraining anything.
