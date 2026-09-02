# Gate Evidence Channel — Diagnosis (Sprint 008, unit A1)

**Verdict**: ~~`profile` — the request contract, not the transport.~~
**SUPERSEDED by §7 below.** The real cause is an unsatisfiable `SubagentStop`
hook. The A1 experiment was sound and its conclusion was wrong, for a reason A1
could not have seen: it ran while the state anchor still pointed at Sprint 007,
whose `SPRINT_LOG.md` already carried the row the hook demands.
**Date**: 2026-09-01, superseded 2026-09-02
**Decides**: whether Phase 7 of this sprint dispatches its gates as subagents.

---

## 1. The question

Sprint 007's Phase 7 produced two verdicts and no findings. `qa_agent`
(`af56a8f`) returned only a verdict line on three invocations, twice with
`tool_uses=0`; `tester_agent` (`a90db59`) ran 48 tool calls over 12.6 minutes and
returned one line, twice. Roughly 430k subagent tokens bought verdicts with no
evidence, and the orchestrator re-verified its own work — the posture the double
gate exists to prevent.

`docs/active_state.json` `gate_evidence_channel` requires settling one thing
before gates are dispatched again: **is the truncation in the result channel, or
in the agent profile?** The two have opposite remedies. A truncating channel
means findings can never be delegated and Phase 7 must run in session. A profile
that does not emit findings is fixed by asking differently.

## 2. Method

One `qa-agent` invocation with a deliberately falsifiable task: audit two files
against two numeric rules whose answers were computed independently **before**
dispatch, so the reply could be checked rather than believed.

The prompt differed from Sprint 007's in one respect, which is the whole
experiment: it named the deliverable. Three required sections (findings table
with fixed columns, method statement, tool-call count), an explicit instruction
not to summarize, and an explicit statement that a verdict without the table is
a failed response.

Ground truth computed before dispatch, via `ast` over both files:

| File | Function | Span |
| :--- | :--- | :--- |
| `export_one.py` | `open_chat_by_query` | 52 lines |
| `export_one.py` | `scroll_one_pass` | 51 lines |
| `history.py` | — | none over 50 |

## 3. Result

The reply carried all three sections in full: a five-row findings table, a
six-step method statement naming every command, and a tool-call count.

| Measure | Sprint 007 | This invocation |
| :--- | :--- | :--- |
| Findings returned | none | 4 violations + 3 adjudicated near-misses |
| Method stated | no | yes, six steps |
| Tool calls | 0 (twice) | 10 |
| Tokens | ~430k across five invocations | 40,711 |
| Duration | 12.6 min (Tester) | 2.2 min |

It reproduced both pre-computed length findings exactly, and **exceeded** the
ground truth with two `max_indentation` violations that had not been measured
before dispatch:

| File | Function | Depth | Independently confirmed |
| :--- | :--- | :--- | :--- |
| `export_one.py` | `_open_first_result` | 4 | yes — AST block-nesting re-run by the orchestrator |
| `export_one.py` | `_click_load_earlier` | 4 | yes — same |

Both were verified by an independent AST walk before being accepted. It also
distinguished three raw-indentation false positives (wrapped dict literals and a
wrapped call) from real nesting, by reading the source regions rather than
trusting either of its two scripts — a discrimination a truncated channel could
not have delivered even if it had wanted to.

## 4. Conclusion

**The channel carries a full report.** A 40k-token reply with a table, a method
and adjudicated edge cases arrived intact. Sprint 007's empty verdicts were not
transport loss.

What differed is that this prompt **named the deliverable and declared a
verdict-only reply a failure**. The `qa_agent` profile is defined around emitting
`APPROVED | REJECTED | RECORD` (`RA-17`), and asked for a verdict it returns a
verdict — correctly, by its own contract. The Sprint 007 dispatches asked for
the verdict and got exactly that.

This also explains the `tool_uses=0` invocations without needing a channel
defect: an agent asked only to conclude can conclude without looking.

## 5. Posture for this sprint's Phase 7

Gates **are** dispatched as subagents. Both dispatches must carry:

| Requirement | Reason |
| :--- | :--- |
| A named, structured deliverable (findings table with fixed columns) | The single variable that changed the outcome here |
| An explicit statement that a verdict-only reply is a failed response | Overrides the profile's default of concluding |
| A required method statement | Makes `tool_uses=0` visible instead of silent |
| A required tool-call count | Cheap, and it is what exposed the Sprint 007 pattern |
| Independent verification of every accepted finding | Two of the four findings here were novel; both were re-derived before being believed |

The last row is not a hedge against the gate — it is what turned this
invocation from an assertion into evidence, and it stays.

## 6. Side finding, recorded not fixed

The four violations this experiment surfaced are **real and pre-existing on
`main`**, in `src/whatsapp_chat_extractor/export_one.py`, a file Sprint 008 does
not touch and which appears in no `task_scope.md` row:

| Function | Rule | Measured |
| :--- | :--- | :--- |
| `open_chat_by_query` | `max_lines_per_func` (50) | 52 |
| `scroll_one_pass` | `max_lines_per_func` (50) | 51 |
| `_open_first_result` | `max_indentation` (3) | 4 |
| `_click_load_earlier` | `max_indentation` (3) | 4 |

A fifth, `__main__.py::cmd_login` at depth 4, was found by the orchestrator while
checking its own Sprint 008 edits and confirmed pre-existing at `HEAD` before
this sprint began.

Not fixed here: they are outside the approved scope, and widening a sprint to
absorb whatever an audit finds is how a scope stops meaning anything. Destination
is Sprint 009, and `docs/active_state.json` carries them so they do not depend on
this file being reread.

---

## 7. What actually caused it — written after Phase 7, superseding §4

A1's conclusion did not survive contact with the real gates. Both Phase 7
dispatches used exactly the prompt shape §5 prescribes — named deliverable,
verdict-only declared a failure, method and tool-count required — and both
returned **one line**:

| Dispatch | Tokens | Tool calls | Duration | Reply |
| :--- | :--- | :--- | :--- | :--- |
| A1 (`qa-agent`) | 40,711 | 10 | 2.2 min | full report |
| Gate 1 (`qa-agent`) | 89,516 | 24 | 8.0 min | verdict line only |
| Gate 2 (`tester-agent`) | 88,682 | 35 | 10.4 min | verdict line only |

The obvious reading — that loss scales with reply length — was wrong too. The
cause is a **deadlock between a hook and a role restriction**, and it reproduces
on demand.

### The mechanism

`.claude/settings.json` registers a `SubagentStop` hook running
`.agents/scripts/check_role_artifact.py --from-hook`. For a Double-Gate role it
exits `2` unless `SPRINT_LOG.md` already holds that gate's row:

```
$ echo '{"agent_type":"qa-agent"}' | python3 .agents/scripts/check_role_artifact.py --from-hook
❌ [ROLE-ARTIFACT] role='QA Agent' missing: 'QA' row in SPRINT_LOG.md
HOOK_EXIT=2
```

Under `RA-11`, exit `2` **blocks the stop** and feeds stderr back to the agent,
forcing a continuation. The agent cannot satisfy it: `artifact_registry.json`
names the **Orchestrator** as `SPRINT_LOG.md`'s owner, the `qa_agent` and
`tester_agent` profiles are read-only by design (`F-026-A1`), and both agents
said so explicitly rather than attempting the write. Each forced continuation
replaces the last message, and only the last message reaches the parent — so the
report is overwritten by the terse continuation that follows it.

Gate 2 named the same mechanism independently, from inside it, as its `F-8`.

### Why A1 escaped, and why that is the proof

The hook resolves the sprint directory from `docs/active_state.json`. A1 ran
**before** unit A2 repointed the anchor from Sprint 007 to Sprint 008, and
Sprint 007's `SPRINT_LOG.md` already carries `QA Agent` and `Tester Agent` rows.
So the hook exited `0` and A1's reply was never interrupted.

Demonstrated by flipping only the anchor's `current_sprint.id`:

| Anchor points at | Hook exit | Reason |
| :--- | :--- | :--- |
| Sprint 7 (log has both rows) | `0` | `required artifacts present` |
| Sprint 8 (log said `_pending_`) | `2` | `missing: 'QA' row in SPRINT_LOG.md` |

**A2 — this sprint's own anchor update — is what armed the trap between A1 and
the gates.** That is also why Sprint 007 recorded the same symptom twice and
never diagnosed it: by the time anyone looked, its log had rows and the hook was
quiet again.

### The fix that unblocked it

Transcribing both gate rows into `SPRINT_LOG.md` before the follow-up requests.
Both hooks then exited `0`, and both agents delivered their full evidence — Gate
2's arriving with an 18-mutant analysis that produced three real coverage gaps.

### Corrected posture

Gates **are** dispatchable, and §5's prompt requirements remain worth keeping —
they are why the recovered reports were usable. But they were never the binding
constraint. The binding constraint is: **`SPRINT_LOG.md` must already hold a row
for each gate before that gate is dispatched.** Write the row with a `_pending_`
verdict first and fill it in on return, or the hook eats the evidence.

Routed upstream as `UPSTREAM_FINDING_013`: a host must not have to pre-write a
verdict row to receive the evidence that determines it.
