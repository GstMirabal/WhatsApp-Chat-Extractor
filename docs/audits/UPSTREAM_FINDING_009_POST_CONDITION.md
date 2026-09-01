# Upstream finding draft — a post-condition check must distinguish the state it caused from the state that already held

**routing_class**: `nucleus`
**Severity**: MEDIUM (rule amendment, not a code defect)
**Host**: WhatsApp Chat Extractor · Hotfix `H-001` · 2026-08-29
**Pin observed**: `.agents` v4.23.0
**Related**: `docs/hotfixes/H-001-backend.md §5`, `agents.md §4 constitutional_escalation`, `rules/qa_and_testing.md`
**Proposes**: a new `RA-XX` amendment

## The failure that produced it

`open_chat_by_query` reported success having opened no chat. An export could
therefore be written for **whichever conversation was already on screen** and
exit `0`. Because `chat_id` is a digest of the title and the title is never
stored, the output file carried no evidence of its origin: a training corpus
attributed to the wrong person, with no signal anywhere that it was wrong.

Three separate post-conditions were in place. Every one of them was satisfied by
the page state that already held **before** the action ran:

| Post-condition | Why it could not fail |
| :--- | :--- |
| Wait for the message panel | The panel was already open from the previous chat |
| Click a search result | The selector also matches the ordinary chat list, which is always present |
| Read the conversation title | It was read and never compared to anything |

Each check was individually reasonable. Together they verified nothing, because
none of them could distinguish *the state the action was supposed to cause* from
*the state that preceded it*.

## Why this is framework-class, not host-class

Nothing above is about WhatsApp. The pattern is a general automation defect:

> A check that passes against the pre-action state is not a verification. It is
> a restatement of the precondition.

It applies to any agent or script that drives an external system it does not
control — a browser, a deploy target, an API, a container. The framework already
carries the sibling principle in `ADR-0003` terms at the host level (never
synthesize a value indistinguishable from a measured one); this is the same
error one level up, about states rather than values.

`agents.md §4 constitutional_escalation` routes systemic patterns into the
ruleset. `§3 strict_rule` forbids the host from patching `agents.md` directly,
which is why this is a draft for a nucleus PR rather than an applied edit.

## Proposed amendment

**`RA-XX: POST_CONDITION_DISCRIMINATION`** — A check that verifies an action
succeeded MUST be capable of failing against the state that existed before the
action ran. A post-condition satisfiable by the precondition is not a check and
MUST NOT be counted as one. Where the caused state and the prior state are
distinguishable only by identity (which chat, which record, which deploy), the
check MUST compare that identity and fail closed on a mismatch or on an
unreadable value.

Suggested placement: `agents.md §7`, beside `RA-13 SEQUENTIAL_GATES`, which is
the closest relative — `RA-13` says a gate and the action it guards must be
separate invocations so the gate's result is observed; this says the gate must
be able to return a negative at all.

## Suggested enforcement

A rule with no instrument is a rule that will be rediscovered. Two candidates,
neither yet built:

| Instrument | What it would catch |
| :--- | :--- |
| A `rules/qa_and_testing.md` review question in the Phase 7 checklist: *"for each post-condition, what pre-existing state would satisfy it?"* | The class at review time, cheaply, with no new code |
| A test-shape check: a regression test for a fail-closed path must be shown to fail against the pre-fix tree | `H-001` names this explicitly — a regression test that passes against the broken code pinned nothing |

The second is close to what the Implementation Plan template's **Tests** section
already asks (*"Reproduce before repairing"*), so the cheapest real enforcement
may be extending that section's check rather than adding an instrument.
