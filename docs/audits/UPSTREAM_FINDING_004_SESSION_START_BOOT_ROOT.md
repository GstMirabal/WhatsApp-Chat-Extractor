# Upstream finding draft — `session_start.py --boot` mis-roots host-scoped steps

**routing_class**: `nucleus`
**Host**: WhastApp Chat Extractor · pre-Sprint 004 session start · 2026-08-29
**Pin observed**: `.agents` v4.23.0
**Related**: `agents.md §3 jurisdiction`, `§5 mandatory_topology`, `RA-16`

## Defect

`scripts/session_start.py` resolves its root from its own file location:

| Location | Code |
| :--- | :--- |
| `scripts/session_start.py:37-39` | `repo_root()` returns `Path(__file__).resolve().parent.parent` |
| `scripts/session_start.py:203-213` | `_run_script()` spawns every sub-step with `cwd=str(root)` |
| `scripts/session_start.py:306,315,235,258,284` | drift, claim, probe, sync, bridge all routed through that `cwd` |

In **submodule mode** that root is the host's `.agents/` checkout, not the host
repository. The sub-steps it launches are **host-scoped** and resolve their
targets against the cwd:

| Script | Anchor resolution |
| :--- | :--- |
| `scripts/session_state.py:51` | `ACTIVE_STATE = Path("docs/active_state.json")` — cwd-relative |
| `scripts/detect_drift.py` | host-scoped by declaration (`scripts/_root.py` docstring) |

Consequence: `python3 .agents/scripts/session_start.py --boot --tool cursor`
claims the session lock on **`.agents/docs/active_state.json`** (the nucleus
anchor inside the host's submodule) and measures drift against the framework
repository instead of the host.

`scripts/_root.py` states the rule this violates: *"Host-scoped scripts MUST NOT
adopt `agents_root()`. Anchoring them to the framework would make them audit the
framework instead of the host."* `session_start.py` does not call `agents_root()`
but reimplements the same anchoring as `repo_root()` and then imposes it on its
children through `cwd`.

## Why it stayed invisible

The write lands on a path the nucleus ignores — `.gitignore:55`
`docs/active_state.json` — so `git -C .agents status --porcelain` stays empty and
`scripts/submodule_purity.py` reports no contamination. This is the exact
blindness `agents.md §5 mandatory_topology` documents for `docs/sprints/`,
reproduced on the state anchor.

## Observed evidence

| Anchor | Holder | Recorded |
| :--- | :--- | :--- |
| Host `docs/active_state.json` | `20260827T154249Z-46319` | `IN_PROGRESS`, `last_close_commit` present |
| Nucleus `.agents/docs/active_state.json` | `20260827T154222Z-45916` | `IN_PROGRESS`, no `last_close_commit` |

Two locks, 27 seconds apart, from one session: `--boot` claimed the nucleus
anchor, then the host anchor was claimed separately. On 2026-08-29 the boot
aborted at `claim` against the stale nucleus lock, while the host anchor was
never consulted. Re-running the binding steps from the host root gave a clean
result on every one:

| Step (from host root) | Result |
| :--- | :--- |
| `python3 .agents/scripts/detect_drift.py` | `0` — HEAD matches sealed close `b090ed3` |
| `python3 .agents/scripts/sync_agents_pin.py` | `0` — pin current (v4.23.0) |
| `python3 .agents/scripts/session_probe.py` | advisory findings only |

The `--boot` verdict and the binding-table verdict disagreed on the same
repository at the same commit.

## Impact

1. A host session writes inside the submodule tree, contradicting
   `§3 jurisdiction`, and no shipped check can detect it.
2. Drift, probe and sync report on the framework rather than on the host, so
   `/agents:start` step 2 ("read that briefing") describes the wrong repository.
3. A stale nucleus lock blocks every later host boot with a holder UID that
   appears in no host artifact, which is not diagnosable from the host side.
4. `--boot` is the declared invoker for these binding steps under `RA-16`;
   while mis-rooted, the steps have an invoker that does not exercise them
   against their real subject.

## Second instance, found at the Sprint 005 close (2026-08-30)

The same class, reached by a different mechanism: not `cwd` inheritance but a
direct adoption of the framework root.

`scripts/model_ledger.py:188` calls `agents_root()` unconditionally, and
`OUT_REL` is `docs/audits/MODEL_LEDGER.md` relative to it. `collect(root)` then
enumerates `root/docs/sprints/`. In a host:

| What the close asks for | What the script does |
| :--- | :--- |
| `close_workflow.md` `model_ledger_regen` done-criterion: `docs/audits/MODEL_LEDGER.md` exists | Writes `.agents/docs/audits/MODEL_LEDGER.md` |
| A ledger derived from **this sprint's** `task_scope.md` Model/Effort columns | Derives it from the **framework's** sprint records |

Observed here: the run reported `Wrote docs/audits/MODEL_LEDGER.md (10 sprint
rows)` — ten rows from the nucleus's own sprints, while this host has five. The
host's own ledger is never produced, so the step's done-criterion cannot be met
in a host by running the command the step names. It did not dirty the submodule
only because the regenerated content was byte-identical to the nucleus's
committed copy; a host whose sprint records differed would have modified a
tracked framework file, which `submodule_purity.py` would then correctly refuse
at the very close that produced it.

This is the rule `scripts/_root.py` states, violated directly rather than by
inheritance: *"Host-scoped scripts MUST NOT adopt `agents_root()`."*

### Third instance — `.agents/Makefile` is not space-safe

Unrelated to rooting, found in the same step. The `model-ledger` and
`docs-freshness-check` targets interpolate the repository path unquoted, so a
host whose path contains a space breaks:

```
cd /Users/gstmirabal/Developer/GitHub . Extractor/.agents && python3 scripts/model_ledger.py
python3: can't open file '/Users/gstmirabal/Developer/GitHub/scripts/model_ledger.py'
```

`make` reported `Error 2`, and the shell pipeline still reported `EXIT=0`, so the
failure is invisible to a caller that checks the exit code of the pipeline rather
than of `make`. Both gates were run by invoking the scripts directly instead.
Quote every path interpolation in `Makefile` and add a test that runs a target
from a directory whose name contains a space.

## Proposed fix (nucleus)

1. Split root resolution in `session_start.py`: keep `repo_root()` for locating
   the scripts, and add a host root (`Path.cwd()` in submodule mode,
   `agents_root()` in nucleus mode via `scripts/_mode.is_nucleus()`) used as the
   `cwd` of every host-scoped sub-step.
2. Pass that host root as `cwd` in `_run_script()` for `detect_drift.py`,
   `session_state.py`, `session_probe.py`; keep framework-scoped steps on
   `agents_root()`.
3. Extend `scripts/submodule_purity.py` to inspect gitignored state paths
   (`docs/active_state.json`, `.agent_state/`) inside `.agents/`, so a host
   session's write there fails the close instead of passing silently.
4. Add a regression test: invoking `session_start.py --boot` from a simulated
   host root claims the host anchor and leaves `.agents/docs/active_state.json`
   untouched.

## Host mitigation (applied this session)

Binding steps were run individually from the host root per
`workflows/start_workflow.md`, and the host lock was claimed with
`--takeover` after confirming the 2026-08-27 holder was a crashed session
(clean tree, `HEAD == last_close_commit`, Sprint 003 sealed as v0.3.0). The
stale nucleus anchor was left untouched: `strict_rule` forbids the host from
editing the submodule in place.

Open a nucleus PR from a separate `.agents` clone — do not edit the submodule
here (`§3 strict_rule`, `§4 feedback_upstream`).

## Third instance, reproduced live at the Sprint 008 close (2026-09-02)

`close_workflow.md` Phase 1 `model_ledger_regen` runs `make model-ledger`. At pin
v4.24.0, from the host root:

```
$ make -f .agents/Makefile model-ledger
cd <host>/.agents && python3 scripts/model_ledger.py
Wrote docs/audits/MODEL_LEDGER.md (11 sprint rows).
```

The eleven rows are **this host's sprints**, and the file landed at
`.agents/docs/audits/MODEL_LEDGER.md` — inside the submodule. The host's own
`docs/audits/MODEL_LEDGER.md` was left untouched and is now stale by six days.

`scripts/model_ledger.py:188` is `root = agents_root()`, unconditional, with
`OUT_REL = Path("docs/audits/MODEL_LEDGER.md")` resolved against it and no flag
to override either. A host has **no way** to regenerate its own ledger with the
shipped script, while the close workflow requires it to.

`submodule_purity.py` reported **clean** immediately afterwards, because
`.agents/.gitignore` covers `docs/audits/`. Host content is sitting in the
framework tree and the check built to catch that cannot see it — the same
blindness this finding's first instance documents for the state anchor, now
observed a third time on a third artifact.

**Fix**: `model_ledger.py` is host-scoped by subject — it enumerates the host's
sprints — so per `scripts/_root.py`'s own two-class rule it must resolve its
output against the cwd, not `agents_root()`, and declare that in its docstring.
A `--root` flag would also work and is more explicit.
