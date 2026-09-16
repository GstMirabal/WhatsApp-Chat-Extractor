# Upstream finding draft — `model_ledger.py` can never target a host, only the nucleus, and the host's own ledger file already carries nucleus data from an earlier session

**routing_class**: `nucleus`
**Severity**: MEDIUM
**Host**: WhatsApp Chat Extractor · Sprint 012 close, `model_ledger_regen` · found 2026-09-16
**Pin observed**: `.agents` v4.30.0
**Related**: `KI-008-G` (`memory_index.json`, Sprint 008 — same defect, first noticed but never drafted), `scripts/model_ledger.py`, `close_workflow.md` `model_ledger_regen`, `agents.md §3 jurisdiction`

## Defect

`scripts/model_ledger.py` is framework-scoped: it chdirs to `agents_root()`
unconditionally (same pattern as `verify_references.py`, `map_workflows.py`;
`_root.py`'s own docstring names the class). `close_workflow.md`'s
`model_ledger_regen` step instructs `make model-ledger` from a host session,
with the stated done-criterion "`docs/audits/MODEL_LEDGER.md` exists" — but
the file the script writes is always `.agents/docs/audits/MODEL_LEDGER.md`,
derived from the **nucleus's own** `docs/sprints/` history, never the host's.
A host session literally cannot produce its own model ledger with this
script — not "produces it in the wrong place sometimes", produces the
nucleus's ledger unconditionally, every time, regardless of host cwd.

## Observed

```
$ make -f .agents/Makefile model-ledger
cd .../.agents && python3 scripts/model_ledger.py
Wrote docs/audits/MODEL_LEDGER.md (17 sprint rows).
$ git -C .agents status --porcelain
(empty — gitignored inside the submodule)
$ cat .agents/docs/audits/MODEL_LEDGER.md | head -3
| sprint_id | tier | model_id | effort | units | gate1_rounds | gate2_rounds | verdicts |
| 31 | mixed | composer-2.5, grok-4.6 | high | 14 | 1 | 1 | APPROVED |
```

Sprint 31 with `composer-2.5`/`grok-4.6` at "high" effort is nucleus
internal history — this host's own sprints are numbered 001-012 and have
used only `claude-code` (`session_tool` unchanged all sprint, per
`docs/active_state.json`), never Cursor or those model families.

**A second, worse symptom, from an earlier session**: this host's own
tracked `docs/audits/MODEL_LEDGER.md` (dated 2026-08-27, likely session 12)
already contains the *same* nucleus sprint-31-40 rows, committed into the
HOST repository under the host's own path. Someone ran this script once,
got the nucleus's ledger, and — reasonably, given the done-criterion just
says "the file exists" — committed it as if it were the host's own. The
file has sat there, wrong, uncorrected, since.

## Why this class matters more than the instance

`close_workflow.md` names a done-criterion (`file exists`) that is
satisfiable by writing the *wrong file* — the same defect class as
`UPSTREAM_FINDING_009` (a post-condition that does not distinguish the
state it caused from a state that already held) and `UPSTREAM_FINDING_014`
(a required artifact with no instrument checking its content, only its
presence). A host running this close step has no way to notice the ledger
it just "regenerated" describes a different repository's sprints.

## Proposed fix

| # | Change | Why |
| :--- | :--- | :--- |
| 1 | `model_ledger.py` needs a host-scoped mode: read `docs/sprints/` relative to the invoking repository's own root (cwd, or an explicit `--repo-root`), writing `<that root>/docs/audits/MODEL_LEDGER.md` — mirroring `docs_freshness_check.py`/`detect_drift.py`'s host-scoped class rather than the framework-scoped one it currently follows | The nucleus and every host both need this file; only one class of resolution can serve both, and it is not the current one |
| 2 | `close_workflow.md`'s `model_ledger_regen` done-criterion should also assert the file's `sprint_id` range matches the closing sprint's own number (or at least does not contain sprint ids the host has never had) | A done-criterion of "the file exists" cannot catch "the file exists and is entirely the wrong repository's data" |

## Host action taken

None to `.agents` (`strict_rule`). The generated
`.agents/docs/audits/MODEL_LEDGER.md` from this session's regeneration
attempt is gitignored there and left as-is — it is scratch output, not a
tracked change. The host's own stale, wrong `docs/audits/MODEL_LEDGER.md`
(nucleus sprint 31-40 data) is left uncorrected by this sprint too: there is
no way to regenerate a *correct* one with the current script, and hand-
authoring one would fabricate data this project does not actually have
recorded per-sprint. Recorded here rather than silently left for the next
session to rediscover.
