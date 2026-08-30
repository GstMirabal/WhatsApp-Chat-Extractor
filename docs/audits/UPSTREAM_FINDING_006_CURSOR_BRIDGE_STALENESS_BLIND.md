# Upstream finding draft — `commands_stale()` is blind in submodule mode, and the install it forces clobbers the host `.gitignore`

**routing_class**: `nucleus`
**Host**: WhastApp Chat Extractor · `/agents:start` session #7 · 2026-08-30
**Pin observed**: `.agents` v4.23.0 (`d258b43`)
**Related**: `UPSTREAM_FINDING_004` (same mis-rooting family), `agents.md §3 federation`, `RA-16`

## Defect A — the freshness check cannot see a host's bridge

`cursor_adapter.commands_stale(host_dir, *, nucleus)` compares `host_dir/commands`
against `host_dir/.cursor/commands`. That layout is the **nucleus** layout. In a
host, the two directories live in different trees:

| Artifact | Host location |
| :--- | :--- |
| Command sources | `.agents/commands/` |
| Rendered Cursor mirror | `<host-root>/.cursor/commands/` |

`session_start.py:245-251` calls it with `root` = `repo_root()` = the host's
`.agents/` checkout, and hardcodes `nucleus=True`:

```python
return bool(commands_stale(root, nucleus=True))
```

Measured in this host:

| Call | Result | Why |
| :--- | :--- | :--- |
| `commands_stale(.agents, nucleus=True)` | `True` | `dest_root` = `.agents/.cursor/commands` — **never exists in a host**; the `if not dest_root.is_dir(): return True` branch fires every time |
| `commands_stale(<host-root>, nucleus=False)` | `False` | `src_root` = `<host-root>/commands` does not exist either; the `if not src_root.is_dir(): return False` branch fires and reports fresh **without comparing anything** |

Neither rooting compares the artifacts that actually exist. The check is
unconditionally `True` on the path `session_start.py` uses, and vacuously
`False` on the other. `nucleus=True` is also the wrong render flag for a host:
comparing the same 13 commands with the correct roots gives **0 mismatches at
`nucleus=False` and 12 mismatches at `nucleus=True`**, so even a corrected
rooting would report false staleness while that flag stays hardcoded.

Consequence: `bridge_check` triage in `start_workflow.md` v6.6.0 always takes
branch **(b) "commands stale → `install.sh --target …`"**, so every Cursor boot
of every host runs a full bridge install that Sprint 040's triage was written to
avoid.

## Defect B — that forced install regresses the host's `.gitignore`

`install.sh --target cursor` appends a bridge/graphify ignore block:

```
# .agents Claude/Cursor bridge + graphify output (regenerated locally, never commit)
/.claude/commands/
```

It appends without checking whether the host already governs that path more
narrowly. This host does, and deliberately — Sprint 004 shipped it as a fix
(`CHANGELOG.md [0.4.0] Fixed`):

```
/.claude/commands/*
!/.claude/commands/wa-export.md
```

Excluding the **directory** defeats a negation inside it: git does not descend
into an excluded directory, so the later blanket rule silently re-ignored the
tracked, host-authored `.claude/commands/wa-export.md`. Verified with
`git check-ignore -v --no-index`:

```
.gitignore:42:/.claude/commands/   .claude/commands/wa-export.md
```

`git check-ignore` **without** `--no-index` reported nothing, because it skips
tracked paths — so the regression is invisible to the obvious check. This is the
exact defect Sprint 004 fixed, reintroduced by the installer six days later.

`agents.md §3 federation` sanctions `install.sh` as the bridge into the host's
configuration and specifies a "non-destructive JSON merge" for JSON. The
`.gitignore` append has no equivalent guard.

## Proposed fix (nucleus)

1. Give `commands_stale()` explicit source and destination roots instead of
   deriving both from one `host_dir`, and have `session_start.py` pass
   `.agents/commands` and `<host-root>/.cursor/commands` in submodule mode.
2. Derive the `nucleus` flag from `scripts/_mode.is_nucleus()` at the call site
   in `_commands_body_stale()` rather than hardcoding `True`.
3. Before appending an ignore rule, have `install.sh` skip any path already
   matched by an existing `.gitignore` rule — and never append a bare directory
   exclusion when a `path/*` + `!path/keep` pair for the same directory is
   present.
4. Regression tests: (a) `commands_stale` returns `False` for a simulated host
   whose `.cursor/commands` matches `.agents/commands` rendered at
   `nucleus=False`; (b) two consecutive `install.sh --target cursor` runs leave
   `.gitignore` byte-identical; (c) a host `.gitignore` carrying
   `/.claude/commands/*` + a negation still un-ignores the negated file after an
   install.

## Host mitigation (applied this session)

The appended `.gitignore` block was removed, restoring `wa-export.md` to
trackable. The bridge itself was left installed: it is genuinely fresh — all 13
commands match at `nucleus=False`, and `.agents/.bridge_cursor.lock` records
framework `HEAD` `d258b43`. `.agents` was not edited (`§3 strict_rule`):
`git -C .agents status --porcelain` is empty.

Open a nucleus PR from a separate `.agents` clone, alongside
`UPSTREAM_FINDING_004` and `_005` (`§4 feedback_upstream`, `RA-15`).
