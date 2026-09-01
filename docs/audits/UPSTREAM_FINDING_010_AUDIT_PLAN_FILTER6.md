# Upstream finding draft — `audit_plan.py` Filter 6 cannot tell using `/loop` from prohibiting it

**routing_class**: `nucleus`
**Severity**: LOW
**Host**: WhatsApp Chat Extractor · Sprint 006 Phase 1 · 2026-08-30
**Pin observed**: `.agents` v4.23.0
**Related**: `skills/token-saver-auditor/scripts/audit_plan.py:76`, `rules/loop_governance.md`, `docs/standards/templates/IMPLEMENTATION_PLAN_TEMPLATE.md`

## Defect

`audit_plan.py:76` tests for the literal substring `/loop` and requires
`loop_guard.py` to be named alongside it. The test cannot distinguish:

| Plan says | Filter 6 verdict | Correct verdict |
| :--- | :--- | :--- |
| "Phases 6-8 run under `/loop`" without naming the guard | reject | reject |
| "Phases 6-8 run under `/loop`, armed with `loop_guard.py start`" | pass | pass |
| "This sprint does **not** use `/loop`" | **reject** | pass |

The third row is the defect. A plan that correctly *prohibits* `/loop` is
rejected until it also names a guard it has no intention of arming.

## Evidence

Sprint 006's plan resolved the rejection by naming `loop_guard.py` and stating
why it is deliberately not armed. That is better documentation than the plan
would otherwise have carried, which is the honest complication here — the check
produced a good outcome by the wrong mechanism.

The mechanism is what makes it a finding: **the check rewards mentioning a
token, not reasoning about it.** A plan can satisfy Filter 6 by naming
`loop_guard.py` in a sentence that says nothing true.

The same class already bit the template itself. `IMPLEMENTATION_PLAN_TEMPLATE.md`
carries a standing note that until Sprint 041 its own approval footer named
`/loop` without naming `loop_guard.py`, so **every plan written faithfully from
the template was rejected by the mandatory Phase 1 gate**, and the only passing
plans were the ones that had dropped the footer. The template now pairs both
strings and warns against separating them. That repair fixed the template; it
did not fix the check, and the two failures share one cause.

## Proposed fix

Filter 6 should decide on the presence of a `/loop` **usage claim**, not on the
substring. Two options, cheapest first:

| Option | Mechanism | Cost |
| :--- | :--- | :--- |
| **A** | Require the pairing only when `/loop` appears **outside** a negation or the standing footer — e.g. ignore lines matching a small set of prohibition phrasings, and ignore the verbatim footer | Small; brittle in the same way, one level up |
| **B** | Have the plan declare loop usage in a **structured field** (a `Loop:` row in the Mechanisms table, `none` or `phases 6-8`), and make Filter 6 read that field | Requires a template change and a migration for existing plans |

**B is the real fix** and A is a stopgap. A check that greps prose for tokens
will keep failing this way, because prose is where the negation lives. The
Mechanisms table already exists in the template for exactly this purpose —
recording per-mechanism classification and invoker — so a `Loop` row is a
natural home rather than a new structure.

## Note for whoever picks this up

The script is **not** at `.agents/scripts/audit_plan.py`. It ships inside a
skill, at `.agents/skills/token-saver-auditor/scripts/audit_plan.py`, verified
by `find` over the submodule at pin v4.24.0. Three earlier host artifacts cited
the wrong path and were corrected on 2026-08-31; the wrong path is why one
sprint's mandatory Phase 1 audit was recorded as "script missing" rather than
performed.
