# ADR-0004: The export states completeness as three explicit values
**Status**: `Accepted`
**Date**: 2026-08-31
**Supersedes**: the `complete` semantics of [ADR-0001](ADR-0001-product-scope-whatsapp-web.md) §2 ("full history")
**Triggers**: 2, 4 (`rules/documentation_standard.md §3.1`)

---

## 1. Context

The export payload carries a boolean `complete` (`writers.py:58`) whose meaning is
fixed by `COMPLETE_REASONS = (STOP_CHAT_START,)` in `history.py:45`: a harvest is
complete only if it stopped because a start-of-conversation marker was observed.

Sprint 006 was opened to establish whether that marker exists. It measured, and
the answer is that it does not appear:

| Evidence | Value |
| :--- | :--- |
| Conversations walked | 5, from the chat list, no search |
| Runs | 2 (probe runs 3 and 4), the second after the stall defect `W4a` was fixed |
| Harvests that stopped on `chat_start` | **0** |
| Harvests that stopped on `stalled` | 10 of 10 |
| Chrome inventories with a non-empty `data-icon` | **0 of 5** |
| Chats reproducing pass **and** row counts exactly across both runs | 3 of 5 |

Reproduce with `python3 scripts/probe_chat_start.py --from-list 5`; the reports are
`chat_start_probe_20260830T221517Z.json` and `chat_start_probe_20260830T224020Z.json`,
and the analysis is `docs/sprints/006-backend-extractor/DOM_PROBE_NOTES.md` §3.

The consequence is not that the export is wrong. It is that the field is
**constant**: every export ever produced says `complete: false`, so it cannot
distinguish a conversation read to its beginning from one cut off halfway. A
field that cannot vary carries no information, and this file is a training corpus
whose consumer has no other way to know what it is holding.

What is **not** claimed: that the marker does not exist. No harvest reached a
provable beginning, so its absence is an inference. What is established — and all
this decision needs — is that `complete: true` is unreachable in practice.

## 2. Decision

| Topic | Decision |
| :--- | :--- |
| New field | `completeness`, with exactly three values: `proven`, `unproven`, `truncated` |
| `proven` | The harvest stopped on `chat_start`. The beginning was **observed** |
| `unproven` | The harvest stopped on `stalled` **and** the panel was not loading on the final pass. The panel stopped producing history and nothing indicated more was coming |
| `truncated` | The harvest stopped on `max_passes`, **or** on `stalled` while the panel was still loading. The harvest ended before the conversation did |
| `complete` (boolean) | **Retained**, derived as `completeness == "proven"`. Not removed |
| Schema | Bumped to v5; `completeness` is required on every export |
| Inference labelling | An inferred value is never recorded in the shape of a measured one. `unproven` is named for what it is |

`unproven` is the honest name for the state the product is actually in today, and
naming it is the whole point. `proven` is retained although it is currently
unreachable: the day WhatsApp Web renders a start marker, the export must be able
to say so without another schema change.

`complete` is kept for compatibility, not indecision. Exports at schema v4 already
exist in `data/`, and a consumer that reads the boolean must not break on a v5
file. It is derived, never set independently — there is one source of truth.

## 3. Consequences

| Easier | Harder |
| :--- | :--- |
| A truncated export is distinguishable from one that reached a quiet top | Consumers must learn a three-valued field instead of a boolean |
| `truncated` makes the `max_passes` cap and the mid-fetch abandonment visible instead of silent | Counts and completeness are not comparable with v4 exports of the same chat |
| The classification is a pure function of `stopped_reason` and the loading signal, so it is testable without a browser | The `unproven` / `truncated` split depends on WA Web's loading markup, which needs the same probe-first discipline as direction (`KI-004-A`) |
| A future start marker upgrades a chat to `proven` with no schema change | Three states invite a fourth; the value set is closed deliberately |

**Privacy is unchanged.** `completeness` describes the harvest, not the
conversation. No new content, name, or identifier reaches disk.

## 4. Deciders

Sprint 006's Approval Gate deliberately withheld this decision so it would be
made **against** the measurement rather than alongside it — the ordering argued
for in that sprint's plan §D1. The measurement arrived first, and this ADR is
written on it.

Human (product owner), 2026-08-31, at the Sprint 007 Approval Gate: Option C
confirmed, full scope authorized.

## 5. Considered Options

The four options were tabulated in Sprint 006's plan §D2 before any evidence
existed. They are judged here against the evidence.

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **A — Status quo, boolean only** | No change; no schema break | Rejected **by measurement, not preference**: the field is constant `false`, so it is indistinguishable from having no field |
| **B — Treat a stall as complete** | Restores a varying boolean cheaply | Rejected, and **already proven wrong in production**: it produced a `complete: true` export of 217 messages from a conversation the operator knew to be far longer (`history.py:38-44`). An inference must not be recorded as proof |
| **C — Third explicit state (chosen)** | Does not feign certainty; separates "reached the beginning" from "cannot demonstrate it"; keeps the boolean working | Schema break; consumers handle three values |
| **D — Composite positive evidence** | Uses the strongest signal actually available: stable scroll height, no new rows, no loading indicator | **Absorbed into C rather than rejected.** Sprint 006 made it conditional on (H2), and (H2) held. It is the criterion separating `unproven` from `truncated` — and it never yields `proven`, because it remains an inference |

Option D standing alone was the real alternative to C, and it fails on one point:
without a named third state it must report its inference through the boolean, and
that is exactly what B did wrong.

---
*Immutable once Accepted — a changed decision gets a new ADR that supersedes this one, never an in-place edit (`rules/documentation_standard.md §3`). File lives at `docs/decisions/ADR-0004-completeness-criterion.md`.*
