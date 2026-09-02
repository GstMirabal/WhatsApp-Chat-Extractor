# Upstream finding draft — the `SubagentStop` hook destroys the Double-Gate evidence it is meant to guarantee

**routing_class**: `nucleus`
**Severity**: HIGH
**Host**: WhatsApp Chat Extractor · Sprint 008 Phase 7 · 2026-09-01/02
**Pin observed**: `.agents` v4.24.0
**Related**: `scripts/check_role_artifact.py`, `config/artifact_registry.json`, `claude/settings.hooks.json`, `RA-11`, `RA-17`, `F-026-A1`
**Found by**: the host orchestrator and, independently and from inside the trap, the `tester_agent` itself (its `F-8`)

## Defect

`check_role_artifact.py --from-hook` runs on `SubagentStop`. For a Double-Gate
role it exits `2` unless `SPRINT_LOG.md` **already** holds that gate's row:

```
$ echo '{"agent_type":"qa-agent"}' | python3 .agents/scripts/check_role_artifact.py --from-hook
❌ [ROLE-ARTIFACT] role='QA Agent' missing: 'QA' row in SPRINT_LOG.md
HOOK_EXIT=2
```

The gate agent **cannot** satisfy this, by three independent parts of the
framework's own design:

| Constraint | Source |
| :--- | :--- |
| `SPRINT_LOG.md` is owned by the Orchestrator, not the gates | `config/artifact_registry.json` |
| Gates emit verdicts; they do not write sprint artifacts | `pipeline_workflow.md` Phase 7, `agents/qa_agent.md` |
| `qa_agent` and `tester_agent` hold no `Write`/`Edit` | `F-026-A1` |

Under `RA-11`, exit `2` blocks the stop and feeds stderr back to the agent,
forcing a continuation. **Only the last message reaches the parent**, so each
forced continuation overwrites the report the gate had just produced. The hook
that exists to guarantee gate evidence is the thing that destroys it.

The docstring says `--from-hook` "only warns". It does not: `main_from_hook`
returns `_report(...)` unchanged, and `_report` returns `2`. The advisory
behaviour is real only for the three early-exit paths (bad JSON, unrecognised
`agent_type`, no `current_sprint`).

## Observed

Sprint 008 dispatched both gates with a deliberately strong prompt — named
deliverable, explicit statement that a verdict-only reply is a failed response,
required method statement and tool-call count:

| Dispatch | Tokens | Tool calls | Duration | Reply |
| :--- | :--- | :--- | :--- | :--- |
| A1 (`qa-agent`, diagnostic) | 40,711 | 10 | 2.2 min | full report |
| Gate 1 (`qa-agent`) | 89,516 | 24 | 8.0 min | **one line** |
| Gate 2 (`tester-agent`) | 88,682 | 35 | 10.4 min | **one line** |

Roughly 178,000 subagent tokens of real work — Gate 2 alone ran an 18-mutant
analysis — reduced to two verdict lines.

## The controlled experiment

The hook resolves the sprint directory from `docs/active_state.json`. A1 ran
before the anchor was repointed from Sprint 007 to Sprint 008, and Sprint 007's
log already carried both gate rows. Flipping **only** `current_sprint.id`:

| Anchor | Hook exit | Message |
| :--- | :--- | :--- |
| Sprint 7 (log has both rows) | `0` | `required artifacts present` |
| Sprint 8 (log said `_pending_`) | `2` | `missing: 'QA' row in SPRINT_LOG.md` |

That is the whole difference between a gate whose evidence survives and one
whose evidence does not. Nothing about the prompt, the model, the task size or
the reply length changed.

**Confirmation of the fix**: transcribing both rows into `SPRINT_LOG.md` and
re-asking the same two agents returned both reports in full, including Gate 2's
mutation analysis, which produced three genuine coverage gaps the host then
closed.

## Why it went undiagnosed for two sprints

Sprint 007 recorded the identical symptom twice — *"the gate's own evidence never
reached the orchestrator"* — and attributed it to the result channel or the
agent profiles. It could not be reproduced afterwards, because by then Sprint
007's log **had** rows and the hook was silent again. The trap is armed only in
the window between opening a sprint and transcribing its first gate row, which
is exactly the window Phase 7 runs in.

Sprint 008 spent a dedicated unit (`A1`) on the wrong hypothesis and reached a
confident, wrong conclusion for the same reason: the diagnostic ran on the far
side of the anchor update that arms the trap.

## Impact

1. **Every host loses Double-Gate evidence on every sprint**, in the default
   configuration, unless it happens to pre-write the row.
2. The loss is silent and looks like agent under-performance, which is how two
   sprints came to blame the wrong component.
3. It inverts `pipeline_workflow.md`'s own precedent note: the double gate
   exists so the author does not review their own work, and an evidence-less
   verdict forces the orchestrator back into exactly that posture.
4. The cost is real — ~178k subagent tokens in one sprint here.

## Proposed fix

The hook asks the wrong actor at the wrong moment. Three parts:

| # | Change | Reason |
| :--- | :--- | :--- |
| 1 | Move the Gate-row check out of `SubagentStop` entirely, to `close_workflow.md` **after** transcription | The Orchestrator is the only actor who can satisfy it, and the close is when it is due |
| 2 | While it remains a `SubagentStop` hook, make the Double-Gate branch **advisory** — print and `return 0` — matching what the docstring already claims | A check no addressee can satisfy must never block |
| 3 | Never let a `SubagentStop` hook block on an artifact the stopping agent lacks the tools to write. Derive the addressee from `artifact_registry.json` and skip when it is not the stopping role | This is the general defect; `SPRINT_LOG.md` is one instance |

Part 3 is the one worth an `RA-XX`: **a blocking hook must be satisfiable by the
actor it blocks.** It is the same shape as `UPSTREAM_FINDING_009` — a check that
cannot discriminate is not a check; here, a check the addressee cannot satisfy
is not a gate, it is a trap.

A regression test should assert that a `SubagentStop` payload for a read-only
role never returns `2`.

## Host workaround in use

Write both gate rows into `SPRINT_LOG.md` with placeholder verdicts **before**
dispatching either gate, then fill them in on return. Recorded in
`docs/sprints/008-backend-extractor/GATE_CHANNEL_DIAGNOSIS.md §7`.

It works, and it is backwards: the host must pre-write the verdict row in order
to receive the evidence that determines the verdict.
