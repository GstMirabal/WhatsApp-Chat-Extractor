# Upstream finding draft — `RA-05` mandates four closeout artifacts and the close verifies three

**routing_class**: `nucleus`
**Severity**: MEDIUM
**Host**: WhatsApp Chat Extractor · Sprint 008 close · found 2026-09-02
**Pin observed**: `.agents` v4.24.0
**Related**: `agents.md RA-05`, `close_workflow.md` Phase 2 `history_sync`, Phase 2.6 `double_gate_evidence`, `rules/documentation_standard.md §4.1`
**Host record**: `docs/hotfixes/H-002-docs.md`

## Defect

`agents.md RA-05 SPRINT_CLOSEOUT` requires updating four things before a sprint
closes: **Blueprints, the Global Roadmap, Walkthroughs, and the Ledger**.
`close_workflow.md` Phase 2 `history_sync` names the same set and adds the two
Documentation Entry Point anchors.

Nothing verifies the Global Roadmap. The instruments that exist cover the others:

| `RA-05` artifact | What can detect staleness |
| :--- | :--- |
| Blueprints | `**Last Audit Sprint**` stamp + `docs_freshness_check` |
| Entry Point anchors | Same stamp + same check |
| Master Ledger | `[Unreleased]` section is structural; `ledger_seal` reads it at deploy |
| **Global Roadmap** | **nothing** |

Phase 2.6 `double_gate_evidence` enumerates the artifacts a close must find, and
it is explicitly scoped to `config/artifact_registry.json` entries with
`scope: sprint`. The roadmap is repository-scoped, so it is correctly outside
that check — and outside every other one too.

`rules/documentation_standard.md §4.1` defines the freshness-stamp convention
(`**Last Audit Sprint**` / `**Last Audit Date**` / `**Last Audit Commit SHA**`)
that makes staleness machine-detectable. The roadmap template does not carry it.

## Observed

Sprint 008 closed, merged (`a2413bb`) and released as `v0.8.0`. Its close
updated the Blueprint, the Walkthrough, the Master Ledger and both Entry Point
anchors, and omitted the Global Roadmap.

Every gate passed:

```
$ python3 .agents/scripts/docs_freshness_check.py . 008
[OK] docs-freshness-check: no findings
$ python3 .agents/scripts/check_task_scope.py --sprint-dir docs/sprints/008-backend-extractor
[OK]
$ python3 .agents/scripts/check_gate_log.py --sprint-dir docs/sprints/008-backend-extractor
[OK]
```

Meanwhile the roadmap still read:

```
| P4 | 008 | GATED | Platform hardening — blocked until the repository is public |
```

The document the *next* sprint is planned from described the sprint that had
just shipped as unstarted and blocked. A reader planning Sprint 009 from it
would have concluded that the enumeration defect was open and that platform
hardening was the outstanding work — both false.

Found only because a human asked how many sprints remained, which is not a
control.

## Why this class matters more than the instance

The roadmap is the **planning input**. A stale Blueprint misdescribes what was
built; a stale roadmap misdirects what gets built next, and the error compounds
into the following sprint's scope. Of the four `RA-05` artifacts, the unchecked
one is the one whose staleness propagates forward.

It is also the same shape as two findings this host already filed: `_009` (a
post-condition satisfiable by the pre-existing state is not a check) and `_013`
(a blocking hook no addressee can satisfy is not a gate). Here: **a requirement
with no instrument is not a requirement, it is a hope.**

## Proposed fix

| # | Change | Why |
| :--- | :--- | :--- |
| 1 | Add the `§4.1` freshness stamp to the roadmap template, and to whatever `standardization_workflow.md` scaffolds as the Global Roadmap | Nothing can check a document that carries no version of itself |
| 2 | Extend `docs_freshness_check.py` to require the Global Roadmap's `**Last Audit Sprint**` to be `>=` the sprint being closed, exactly as it already treats Blueprints | Reuses a working mechanism rather than adding one |
| 3 | Make `close_workflow.md` `history_sync` state the check command, not just the list of artifacts | The step currently names four documents and no way to confirm any of them moved |

Option 2 is the substantive one. Options 1 and 3 exist to make it possible and
to make it visible.

A regression test should close a fixture sprint with a roadmap stamped at an
earlier sprint and assert `docs_freshness_check` exits `2`.

## Host action taken

Fixed under `RA-03` as hotfix `H-002` rather than left for the next sprint: the
defect is in a governance artifact that actively misinforms planning, and the
next planning session was the thing about to consume it. The host added the
`§4.1` stamp to its own roadmap, which makes the staleness auditable — it does
not make it enforced. Enforcement is item 2 above and is framework work.
