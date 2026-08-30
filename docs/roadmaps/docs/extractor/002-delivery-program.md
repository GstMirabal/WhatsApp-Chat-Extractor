# Roadmap: WhatsApp Chat Extractor — delivery program

Program authority: [ADR-0001](../../decisions/ADR-0001-product-scope-whatsapp-web.md),
[ADR-0002](../../decisions/ADR-0002-delivery-program-and-layout.md),
[ADR-0003](../../decisions/ADR-0003-media-placeholders-in-export.md).

| Phase | Sprint | Status | Goal |
| :--- | :--- | :--- | :--- |
| P0 | 002 | CLOSED | Seal product + delivery ADRs, overview, this roadmap |
| P1 | 003 | CLOSED | Spike: one chat via WhatsApp Web → text JSON in `data/` |
| P2 | 004 | CLOSED | Happy path: full-history harvest, pseudonymous JSON, `/wa-export` |
| P2.5 | **005** | **NEXT** | Corpus fidelity + operator surface: media placeholders, Cursor entry, README, LICENSE |
| P3a | 006 | PLANNED | One chat, **proven** complete: uncapped run, `chat_start` verified, resume after failure |
| P3b | 007 | PLANNED | All chats: enumeration, per-chat failure policy, run manifest |
| P4 | 008 | GATED | Platform hardening — blocked until the repository is public |
| — | — | OUT OF REPO | AI analysis (solicitudes, sentimiento), learning server, bot |

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

## Sprint 008 — P4 Platform hardening (GATED)

Blocked by plan limits, not by engineering. See
[docs/PLATFORM_HARDENING.md](../../PLATFORM_HARDENING.md).

| # | Deliverable | Blocker |
| :--- | :--- | :--- |
| 1 | CI actually executing | Actions minutes are billed on private repositories |
| 2 | Branch protection with the four required checks | Needs a public repository or GitHub Pro |
| 3 | `/agents:harden`: secret scanning, Dependabot alerts, private vulnerability reporting | Same |
| 4 | `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `NOTICE` | None — can be done any time |
| 5 | Nucleus PRs for `UPSTREAM_FINDING_004` and `_005` | None — needs a separate `.agents` clone |

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
| P4 | Platform controls and upstream contributions | Product features |
