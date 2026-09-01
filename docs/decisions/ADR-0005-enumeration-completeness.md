# ADR-0005: The run manifest states enumeration completeness as three explicit values
**Status**: `Accepted`
**Date**: 2026-09-01
**Supersedes**: the `enumeration_complete` semantics introduced by Sprint 007 (`manifest.py:68`)
**Extends**: [ADR-0004](ADR-0004-completeness-criterion.md), which established the same epistemology for a single chat's harvest
**Triggers**: 1, 2 (`rules/documentation_standard.md §3.1`)

---

## 1. Context

The run manifest carries a boolean `enumeration_complete` (`manifest.py:68`),
set from `sweep_reached_bottom(page)` — whether the chat-list pane was at its
foot when the sweep ended.

That is a true statement about the pane. It is not the statement the field's
name makes, and Sprint 007 measured the gap after both quality gates had already
approved the branch.

`sweep_chat_list` advances the pane by one `client_height` per pass and
deduplicates by digest. When the chat list reorders mid-sweep — one arriving
message does it — a conversation can move from below the sweep position to above
it and never be rendered into any pass. Measured against the real geometry (899
conversations, a 70-row window, ~76px rows):

| Reorder rate | Conversations found | Duplicates |
| :--- | :--- | :--- |
| One per 5 reads | 882 of 899 | 0 |
| One per 2 reads | 856 of 899 | 0 |

Reproduce with
`python3 -m pytest tests/test_chat_list.py::test_a_reordering_list_makes_the_sweep_UNDERCOUNT_silently -q`.

The digest key guarantees no conversation is visited twice, so the failure is
pure loss. And `enumeration_complete` reports `true` throughout, because the pane
foot genuinely **was** reached. Forty-three conversations can be missing from a
run whose manifest declares the enumeration complete.

This is [ADR-0004](ADR-0004-completeness-criterion.md)'s defect at a different
altitude. There, a boolean `complete` could not distinguish a conversation read
to its beginning from one cut off halfway. Here, a boolean
`enumeration_complete` cannot distinguish a list seen whole from a list that
moved underneath the reader. Both are booleans reporting a proxy for the question
the consumer is actually asking.

**What is not claimed**: that repeated sweeping observes every conversation. A
conversation can, in principle, evade any finite number of sweeps. What is
established is that a single sweep loses conversations at a measured rate while
reporting success.

## 2. Decision

| Topic | Decision |
| :--- | :--- |
| New field | `enumeration`, with exactly three values: `converged`, `unconverged`, `truncated` |
| `converged` | The pane foot was reached **and** the final two sweeps each contributed no conversation not already seen |
| `unconverged` | The pane foot was reached, but sweeps were still contributing new conversations when the sweep budget ran out |
| `truncated` | The pane foot was never reached — the pass cap ended the sweep |
| Fail-closed rule | A state that matches none of the above is `truncated`, never `converged`. An unrecognised stop is not evidence of success |
| Companion field | `sweeps`, the integer number of full sweeps performed. It makes `converged` auditable rather than asserted |
| `enumeration_complete` (boolean) | **Removed**, not derived |
| Schema | `MANIFEST_SCHEMA_VERSION` bumped `1` → `2` |
| Export schema | Untouched. `writers.SCHEMA_VERSION` stays at v5 — this decision changes no exported chat file |

**`converged` deliberately does not mean `proven`.** Agreement between two sweeps
is statistical evidence, not a demonstration: a conversation can evade both. This
is why the value set does not reuse ADR-0004's `proven` / `unproven` names. There,
`proven` was retained though unreachable, because a future WhatsApp Web could
render a start marker and make it reachable. Here there is no such future signal:
no observation of a virtualized list can ever prove that nothing moved behind the
reader. A value the implementation can never emit would be noise in the schema,
so it is not defined.

**`enumeration_complete` is removed rather than derived.** ADR-0004 kept
`complete` as a derived boolean because v4 exports already existed in `data/` and
a consumer reading the boolean must not break on a v5 file. That reasoning does
not transfer: the manifest was introduced in Sprint 007, has exactly one schema
version in the wild, and its only consumer is the operator. Keeping a boolean
whose `true` was demonstrably compatible with losing 43 conversations would
preserve precisely the misreading this ADR exists to end.

## 3. Consequences

| Easier | Harder |
| :--- | :--- |
| A run that lost conversations is distinguishable from one that did not | Enumeration costs roughly one extra sweep: ~3m39s per additional pass against a ~15h whole-account run |
| `sweeps` makes the convergence claim checkable from the manifest alone | Consumers must read a three-valued field instead of a boolean |
| The classification is a pure function of the sweep loop's own counters, so it is testable against a fixture with no browser | `converged` is still an inference; the honest name does not remove the uncertainty, it only stops hiding it |
| `truncated` separates a pass-cap abort from a completed sweep, which the boolean conflated | A manifest at schema v2 is not comparable field-for-field with the v1 manifests already in `data/` |

**Privacy is unchanged.** `enumeration` and `sweeps` describe the sweep, not the
conversations. No new content, name, or identifier reaches disk.

## 4. Deciders

Human (product owner), 2026-09-01, at the Sprint 008 Approval Gate. Approved as
part of the Sprint 008 Implementation Plan (`50b8f83`), whose Design §2 carries
this decision and its rejected alternative.

## 5. Considered Options

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **A — Status quo, boolean only** | No change; no schema break | Rejected **by measurement**: `true` is compatible with losing 43 of 899 conversations, so the field does not answer the question its name asks |
| **B — Keep the boolean, fix only the sweep** | Smallest change; the undercount shrinks | Rejected. It leaves a field that claims certainty the method cannot deliver. Convergence is evidence, not proof, and reporting it through a boolean is the error `ADR-0004` Option B was already rejected for in production |
| **C — Three explicit states (chosen)** | Names the inference as an inference; `sweeps` makes it auditable; `truncated` separates a pass-cap abort from a real sweep | Schema break; consumers handle three values |
| **D — Reuse ADR-0004's `proven` / `unproven` / `truncated`** | One vocabulary across both altitudes; nothing new to learn | Rejected. `proven` is unreachable here **with no path to becoming reachable**, unlike in ADR-0004 where a future start marker would supply it. A permanently dead value invites a consumer to branch on a case that cannot occur |

Option D was the closest alternative and the reason for rejecting it is narrow:
the vocabularies differ because the epistemics differ, and naming them alike
would imply a symmetry that does not hold.

---
*Immutable once Accepted — a changed decision gets a new ADR that supersedes this one, never an in-place edit (`rules/documentation_standard.md §3`). File lives at `docs/decisions/ADR-0005-enumeration-completeness.md`.*
