# Phase Register — Sprint 010 (`backend-extractor`)

Which pipeline phase ran, what it left behind, and what proves it. A phase that
left no artifact did not run (`close_workflow.md` Phase 2.6).

| Phase | Ran | Artifact | Evidence |
| :--- | :--- | :--- | :--- |
| 1. Planning | Yes | `IMPLEMENTATION_PLAN.md` | `audit_plan.py` → `[OK]`, exit `0`. Committed at `a98db70` |
| 2. Environment | Yes | none (precondition) | `ruff` clean, **283 passed / 1 skipped** at plan approval. No `.env` read (`RA-09`) |
| 3. Roadmap | Folded | `SPRINT_LOG.md`, `task_scope.md` | **Deviation, recorded and human-approved**: executes on `ai-sprint/009`, not a fresh `ai-sprint/010` (`RA-12`). The operator chose to fold this onto the open, undeployed Sprint 009 branch rather than wait for its deployment; Sprint 009's deployment carries both. Phases 4.1/4.2/4.3 collapsed into `task_scope.md` at Phase 1 rather than run as separate steps |
| 5. Approval Gate | Yes | none (human) | Full approval, human, attended, 2026-09-10, against the plan text as committed |
| 6. Execution | Yes | 6 units, 8 commits | `935b3be`, `54c052d`, `6616d7a`, `5d0c5cd`, `ce2e23c`, `d674a95` plus two Phase-7 remediation commits (`9169e4c`, `0e333b8`) and one doc correction (`d6c94f3`) |
| 7. Quality Gate | Yes | four rows in `SPRINT_LOG.md` | QA round 1 `REJECTED`/`charter`, round 2 `RECORD`/`testifying`; Tester `RECORD`/`testifying`. `RECORD` does not count toward escalation (`RA-17`) |
| 8. Closeout | Yes | this file | Blueprint, Walkthrough, Global Roadmap and Master Ledger updated |

## Units delivered

6 planned, all landed, no scope change during execution.

| Unit | File | Outcome |
| :--- | :--- | :--- |
| A1 | `consolidate.py` | `read_chat_files`, `resolve_source_run`, `build_header`, `write_corpus` |
| A2 | `test_consolidate.py` | NDJSON contract, both aborts, stable order |
| B1 | `__main__.py` | `consolidate` subcommand, wiring only |
| B2 | `test_consolidate_cli.py` | CLI orchestration through the real parser, browserless |
| C1 | `EXTRACTOR_BLUEPRINT.md` | Component + corpus contract subsection |
| C2 | `EXTRACTOR_WALKTHROUGH.md` | Operator section, footer to `#010` |

## The Phase 7 structural gate — two rounds, both by execution

Round 1 scanned the full repository from the start (31 files, 551 functions),
a change the Orchestrator required after Sprint 009's round-1 miss. It found
zero complexity or style violations and rejected the sprint anyway, on a
design-contract failure it proved by running the code rather than reading the
docstring:

| Round | Finding | Remediation |
| :--- | :--- | :--- |
| 1 | `write_corpus` did not enforce plan `§D2`: a header built from one list and a body from another wrote a corpus whose header lied about its own body, no error. The false guarantee had propagated into the Blueprint as Law | `9169e4c` — `write_corpus` recomputes `chat_count` from the list it actually writes and overwrites whatever the header claimed. Also fixed in the same commit: a missing `chat_id` crashed with `KeyError` instead of this module's own `ValueError` contract. Both proven by mutation |
| — | `EXTRACTOR_BLUEPRINT.md` still asserted the false guarantee | `d6c94f3` |
| 2 | `F-1`, self-inflicted: the pinning test for the round-1 fix counted NDJSON lines with `str.splitlines()`, which also breaks on U+2028/U+2029/U+0085 — the exact defect class the fix was proving closed could have produced a false pass | `0e333b8` — four counting sites switched to `\n`-only splitting; reproduced with a real message body carrying those characters before and after |
| 2 (final) | none | `RECORD` |

## The Phase 7 functional gate — verified against real production data

Tester `RECORD`. Ran `consolidate` against the real 1018-file corpus from
Sprint 009's whole-account run, not only synthetic fixtures: zero duplicate
`chat_id`, header `chat_count` exact, provenance exact against the credited
manifest, both aborts and both flags (`--from-manifest`, `--out`) confirmed
through the real CLI parser.

Eight coverage gaps found by mutation, none charging the sprint — each is a
behaviour the plan's own `A2`/`B2` rows never required tested:

| Gap | What survives the suite |
| :--- | :--- |
| `T-1` | `--from-manifest` silently ignored |
| `T-2` | Four of six header fields deletable |
| `T-3` | "Newest manifest" selection untested — picking the oldest instead survives |
| `T-4` | Input glob unpinned (though a widened glob fails loudly against real data) |
| `T-5` | Schema abort pinned only below the CLI |
| `T-6` | `F-1`'s fix has no regression test of its own |
| `T-7` | `--from-manifest`/`source_run` accepts a path to a file that was never a real run |
| `T-8` | See below — the one that matters |

### `T-8` — found validating provenance against real data, not this sprint's defect

The gate's real-data run surfaced that the credited manifest's `started_at`
(`2026-09-09T20:56:52Z`) is the timestamp of its **last** `--resume` pass, not
when the run began (`2026-09-02T21:40:02Z`). Root cause, confirmed
independently: `journal.read_journal` (`journal.py:223-230`) overwrites
`header` on every header record it walks, so a journal holding five resume
headers yields only the most recent one. **570 of 1018 conversations (56%)
carry an `exported_at` earlier than the date their own manifest claims the run
started.** No conversation's own content or identity is wrong.

Carried, not hotfixed, by human decision: unlike `H-003`, nothing operational
is blocked.

## Carried forward, unscheduled

| Item | Origin |
| :--- | :--- |
| `§D5` — the title-index journal decision | Sprint 009, explicitly excluded from this sprint's plan |
| `§D6` — `__main__.py` at 793 lines | Sprint 009, same |
| `T-2` (Sprint 009's timezone-function tests) | Sprint 009, same |
| `KI-009-H` — no wall-clock timeout in the harvest loop | Sprint 009, blocking a fully unattended run |
| The systemic wall-clock-bound amendment (`H-003 §5`) | Sprint 009, pending `constitutional_escalation` |
| `T-1` through `T-7` (this sprint's coverage gaps) | This sprint, non-blocking |
| `T-8` — journal header selection keeps the last, not the first | Found this sprint, root cause in Sprint 009's `journal.py` |
