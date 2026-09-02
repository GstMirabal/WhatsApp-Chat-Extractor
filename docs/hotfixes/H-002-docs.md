# 🚑 Hotfix: H-002-docs
**File**: `docs/hotfixes/H-002-docs.md` (RA-03 emergency naming — sanctioned exception to RA-06)
**Severity**: `HIGH`
**Detected**: 2026-09-02 · **Resolved**: 2026-09-02

---

## 1. Symptom

`docs/roadmaps/docs/extractor/002-delivery-program.md` was never updated during
the Sprint 008 close. It still declares `| P4 | 008 | GATED | Platform hardening
— blocked until the repository is public |`, describing Sprint 008 as an
unstarted, blocked platform sprint.

Sprint 008 is closed, merged (`a2413bb`) and released as `v0.8.0`. What it
actually delivered — the silent enumeration undercount fixed and measured,
`ADR-0005`, manifest schema v2, an unknown-row probe, six upstream drafts — is
absent from the only document that states the program's shape.

Blast radius is planning, not runtime: the Global Roadmap is where the next
sprint's scope is read from, and a reader planning Sprint 009 from it would
conclude that platform hardening is the outstanding work and that the
enumeration defect is still open. It also asserts the repository's phase state
wrongly to anyone reading the program for the first time.

## 2. Root Cause

Two failures, one of process and one of instrumentation.

**Process.** `agents.md RA-05 SPRINT_CLOSEOUT` requires updating Blueprints, the
**Global Roadmap**, Walkthroughs and the Ledger before closing.
`close_workflow.md` Phase 2 `history_sync` names the same four. The Sprint 008
close updated the Blueprint, the Walkthrough, the Master Ledger and both
Documentation Entry Point anchors — and omitted the Global Roadmap. The omission
was mine, and nothing in the session surfaced it.

**Instrumentation.** No shipped check verifies it. `close_workflow.md` Phase 2.6
`double_gate_evidence` enumerates the *sprint-scoped* artifacts that must exist
(`IMPLEMENTATION_PLAN.md`, `SPRINT_LOG.md`, `agent_assignment.md`,
`skill_assignment.md`, `task_scope.md`) and `docs_freshness_check` passed clean,
because the roadmap is repository-scoped and carries no per-sprint freshness
stamp the way Blueprints and Entry Point anchors do
(`**Last Audit Sprint**` / `**Last Audit Date**` / `**Last Audit Commit SHA**`,
`rules/documentation_standard.md §4.1`).

So `RA-05` names four mandatory artifacts and the gates measure three of them.
The Global Roadmap is the one with no stamp and no check.

## 3. Fix Applied

| File | Change |
| :--- | :--- |
| `docs/roadmaps/docs/extractor/002-delivery-program.md` | Sprint 008 row rewritten from `GATED` to `CLOSED (partial)` with what it delivered and what stayed blocked; a Sprint 008 detail section added; the P4 blocker table corrected against measurement; a proposed Sprint 009 row and section added; freshness stamp added |
| `docs/hotfixes/H-002-docs.md` | This record |

Branch/commit: `hotfix/H-002` → see `#H002` commits on this branch.

## 4. Verification

```bash
grep -n "008" docs/roadmaps/docs/extractor/002-delivery-program.md
python3 .agents/scripts/docs_freshness_check.py . 008 ; echo "EXIT=$?"
```

The roadmap must state Sprint 008 as closed, name `ADR-0005`, and no longer
describe it as `GATED`.

**Regression test.** A prose document has no unit test, so the pin is a
freshness stamp the existing gate can read: the roadmap now carries
`**Last Audit Sprint**`, `**Last Audit Date**` and `**Last Audit Commit SHA**`
in the form `rules/documentation_standard.md §4.1` defines, which is what makes
staleness detectable at all rather than depending on a reader noticing.

Stated honestly: adding the stamp makes the roadmap *auditable*; it does not by
itself make `docs_freshness_check` enforce it. Closing that gap is the amendment
below, and it is framework work, not host work.

## 5. Rule Amendment Check

- [x] Is this failure class systemic (a process pattern, not a one-off)? **Yes.**
      `RA-05` mandates four closeout artifacts and the close's own gates verify
      three. Any artifact a rule requires but no check measures will drift, and
      the one that drifted here is the document the *next* sprint is planned
      from. This is the same shape as `UPSTREAM_FINDING_009` and `_013`: a
      requirement with no instrument, and an instrument that cannot fail for the
      thing it names. Drafted for `constitutional_escalation` as
      **`UPSTREAM_FINDING_014`** — `close_workflow.md` `history_sync` must be
      backed by a check that each `RA-05` artifact carries a freshness stamp at
      or after the sprint being closed.
- [x] Does the root cause reveal a design decision worth recording? **No.** No
      architectural choice is involved; this is a missing control, not a
      contested design. No ADR.
- [x] Master Ledger entry added under `[Unreleased]`.
