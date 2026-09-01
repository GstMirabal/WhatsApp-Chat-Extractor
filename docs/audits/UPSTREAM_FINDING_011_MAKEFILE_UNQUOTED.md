# Upstream finding draft — `.agents/Makefile` is unusable on any host whose path contains a space

**routing_class**: `nucleus`
**Severity**: HIGH
**Host**: WhatsApp Chat Extractor · 2026-08-30, re-verified 2026-09-01
**Pin observed**: `.agents` v4.24.0 (still present)
**Related**: `agents.md §3 strict_rule`, `rules/project_topology.md`

## Defect

`.agents/Makefile` writes `cd $(AGENTS_DIR)` **unquoted**. `AGENTS_DIR` is
derived at line 15 from the Makefile's own absolute path:

```make
AGENTS_DIR := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
```

so it holds whatever the host's installation path is, spaces included. `cd` then
splits the argument on whitespace and the recipe fails on the first word.

Measured at pin v4.24.0 on 2026-09-01:

| Pattern | Occurrences |
| :--- | :--- |
| `cd $(AGENTS_DIR)` (unquoted) | **22** |
| `cd "$(AGENTS_DIR)"` (quoted) | **0** |

Reproduce: `grep -c 'cd \$(AGENTS_DIR)' .agents/Makefile`.

## Blast radius

Lines 47-65 are the entirety of `make verify`. The other affected targets
include `session-start`, `model-ledger`, `docs-freshness-check`,
`cursor-tiers` and `role-artifacts`.

`make verify` is the framework's own staleness gate — `agents.md §0` names it as
what keeps `WORKFLOWS_STEP_MAP_GUIDE.md` honest — so a host with a space in its
path has no working verification target, no session-start target, and no model
ledger, from the moment it installs.

## Why the host cannot fix it

`Makefile` is a tracked file inside the submodule. `agents.md §3 strict_rule`
forbids the host from altering the framework's internal architecture, and
`scripts/submodule_purity.py` refuses the sprint close if it tries. The one-line
repair is unavailable to precisely the party that hits the bug.

## Proposed fix

Quote it: `cd "$(AGENTS_DIR)" && …`, in all 22 places.

A regression guard is worth more than the fix, because the next contributor will
write the unquoted form again: a `make verify` check asserting that no recipe
line matches `cd \$\(AGENTS_DIR\)` without surrounding quotes. That check must
live in the framework, since the failure is invisible on any developer machine
whose own path has no space — which is why this shipped.

## Host workaround in use

The host directory was renamed on 2026-08-30:

```
<parent>/Some Project Name  ->  <parent>/Some-Project-Name
```

(The real names are host-identifying and are genericized here under `RA-15`.
What matters upstream is only that the original contained a space and the
replacement does not.)

Consequences the rename carried, recorded so the next host is not surprised: the
virtual environment had to be recreated (it embeds the old absolute path in
`bin/*` and `pyvenv.cfg`), and `.ruff_cache` / `.pytest_cache` were deleted as
stale. Git, the remote and the submodule were unaffected.

Renaming the project directory to dodge a quoting bug is not a fix. It is also
not always available — a host may not control its own path.
