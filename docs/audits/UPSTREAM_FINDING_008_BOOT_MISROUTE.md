# Upstream finding draft — a host session cannot boot via `session_start.py --boot`

**routing_class**: `nucleus`
**Severity**: HIGH
**Host**: WhatsApp Chat Extractor · `/agents:start` · first observed 2026-08-30, reproduced 2026-09-01
**Pin observed**: `.agents` v4.24.0
**Related**: `UPSTREAM_FINDING_004` (same root cause, different symptom), `agents.md §3 jurisdiction`, `§5 mandatory_topology`, `RA-16`

## Defect

`scripts/session_start.py` resolves its root from its own file location and
imposes it on every child process:

| Location | Code |
| :--- | :--- |
| `scripts/session_start.py:46` | `repo_root()` returns `Path(__file__).resolve().parent.parent` |
| `scripts/session_start.py:417` | `root = repo_root()` |
| `scripts/session_start.py` (drift, claim, probe, sync, bridge) | every sub-step spawned with `cwd=root` |
| `scripts/session_state.py:51` | `ACTIVE_STATE = Path("docs/active_state.json")` — cwd-relative |

In submodule mode that root is the host's `.agents/` checkout. The claim
therefore always targets `.agents/docs/active_state.json`, never the host's.

**Neither the working directory nor a `scripts/` symlink changes this**, because
`__file__` resolution defeats the symlink — `scripts/_root.py` documents
`.resolve()` as doing exactly that, deliberately, for framework-scoped scripts.
`session_start.py` does not call `agents_root()`; it reimplements the same
anchoring as `repo_root()` and then imposes it on host-scoped children through
`cwd`, which is the rule `_root.py` states in its own docstring:

> *"Host-scoped scripts MUST NOT adopt `agents_root()`. Anchoring them to the
> framework would make them audit the framework instead of the host."*

## Observed

`python3 .agents/scripts/session_start.py --boot --tool claude-code`, run from
the host root on 2026-09-01:

```
❌ Session lock held by 20260827T154222Z-45916, still IN_PROGRESS.
boot: claim refused (exit 2).
```

That holder appears in **no host artifact**. It is in
`.agents/docs/active_state.json`, with `session_tool: cursor` and
`start_time: 2026-08-27T15:42:22Z` — a nucleus lock left by a previous
misrouted boot, five days stale. Meanwhile the host anchor
`docs/active_state.json` held `status: SUSPENDED`, which the guard lets through,
and was never consulted.

Re-running the five binding steps individually from the host root gave a clean
result on every one, at the same commit, in the same minute:

| Step (from host root) | Result |
| :--- | :--- |
| `python3 .agents/scripts/detect_drift.py` | `0` — HEAD matches sealed close `ac6ddd9` |
| `python3 .agents/scripts/session_state.py claim --tool claude-code` | `0` — resumed the host's suspended sprint, session #14 |
| `python3 .agents/scripts/session_probe.py` | advisory findings only |
| `python3 .agents/scripts/sync_agents_pin.py` | `0` — pin current (v4.24.0) |
| `bridge_state.bridge_stale(host, "claude", nucleus=False)` | `False` — mirror fresh |

The `--boot` verdict and the binding-table verdict disagree on the same
repository at the same commit. `--boot` is the declared `RA-16` invoker for
those steps, so while mis-rooted, the steps have an invoker that never exercises
them against their real subject.

## Why it stays invisible

`.agents/.gitignore:55` excludes `docs/active_state.json`, so the write lands on
a path the nucleus ignores. `git -C .agents status --porcelain` stays empty and
`scripts/submodule_purity.py` reports no contamination — verified again on
2026-09-01, when purity passed while the stale nucleus lock was sitting in the
submodule tree. This is the `§5 mandatory_topology` blindness reproduced on the
state anchor.

## Impact

1. **A host cannot use the documented operator path at all.** `/agents:start`
   step 1 is the single command the workflow tells an operator to run, and on
   this host it has never once claimed the right anchor.
2. The stale lock is **not clearable from the host**: `--takeover` would be a
   host write inside `.agents`, which `§3 strict_rule` forbids. The blocker is
   permanent from the host side and diagnosable only by reading the submodule's
   own ignored state file.
3. Drift, probe and sync report on the framework rather than the host, so the
   briefing that `/agents:start` step 2 tells the operator to read describes the
   wrong repository.
4. A host session writes inside the submodule tree, contradicting
   `§3 jurisdiction`, and no shipped check can detect it.

## Proposed fix

`session_start.py` must not impose its own location on host-scoped children.
Either spawn every sub-step with `cwd=Path.cwd()` (the host, which is their
declared subject) while resolving the *scripts themselves* through
`agents_root()`, or have `session_state.py` and the other host-scoped children
anchor explicitly rather than relying on an inherited cwd.

The second is more robust and matches what `_root.py` already prescribes for the
two classes: framework-scoped scripts `chdir` to `agents_root()`, host-scoped
scripts never do and declare their root in their own docstring.

A regression test should assert that a `--boot` run launched from a directory
that is **not** the framework root claims the anchor under the cwd, not the one
beside the script.

## Host workaround in use

Run the five binding steps individually with the working directory at the host
root, in the order `start_workflow.md` gives: drift → claim → probe → sync →
bridge. This targets the host anchor and leaves the submodule pure. It is what
the 2026-09-01 session did, and it is a workaround, not a fix: it abandons the
declared operator path and the `RA-16` invoker along with it.
