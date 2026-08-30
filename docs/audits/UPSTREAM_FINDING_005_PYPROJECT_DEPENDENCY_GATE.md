# Upstream finding draft — dependency gate reads any `pyproject.toml` key as a package

**routing_class**: `nucleus`
**Host**: WhastApp Chat Extractor · Sprint 004 · 2026-08-29
**Pin observed**: `.agents` v4.23.0
**Related**: `rules/code_craft.md §7`, `hooks/on_commit.py`

## Defect

`hooks/on_commit.py:740` detects newly added dependencies with:

```python
PACKAGE_NAME = re.compile(r'^[+-]\s*"?([A-Za-z0-9_.@/-]+)"?\s*[:=><~^"]')
```

`MANIFESTS` (line 699) includes `pyproject.toml`, which is not only a
dependency manifest: it is also where `[tool.*]` sections configure ruff,
pytest, mypy, coverage and every other Python tool. The pattern matches
**any** `key = value` line, so a tool setting is indistinguishable from a
package pin.

Reproduced exactly, adding a ruff `exclude` setting:

```
$ git diff --cached -U0 -- pyproject.toml | grep '^+'
+exclude = [".agents", ".venv"]

>>> PACKAGE_NAME.match('+exclude = [".agents", ".venv"]').groups()
('exclude',)
```

The commit was refused with *"This commit adds a dependency without justifying
it"*, naming a package called `exclude` that does not exist.

## Why the suggested remedies are both wrong

The refusal offers two exits, and neither is truthful for a tool-config change:

| Offered exit | Why it is false here |
| :--- | :--- |
| Add `Dependency: <name> — <reason>` | There is no dependency to justify |
| Use `chore(deps)` | The commit is not version maintenance of a dependency |

A gate whose only escapes require a false statement pushes the author toward
mislabeling the commit, which corrupts the history the gate exists to protect.
`hooks/on_commit.py:716-719` already records the PR #27 lesson that a gate must
recognise the legitimate case rather than block everything resembling the
illegitimate one; this is the same class of defect, one file further on.

## Proposed fix (nucleus)

1. Parse `pyproject.toml` structurally rather than by line regex: consider only
   keys under `[project] dependencies`, `[project.optional-dependencies]`,
   `[build-system] requires`, and the Poetry/PDM equivalents. `tomllib` is in
   the standard library from Python 3.11, which the framework already targets.
2. Failing that, scope the regex by section: ignore added lines that fall under
   a `[tool.…]` table header in the same hunk.
3. Add a regression test: a commit that adds `[tool.ruff] exclude = [...]` to
   `pyproject.toml` and nothing else must pass the dependency gate.

## Host mitigation (applied this session)

Ruff configuration was moved out of `pyproject.toml` into `.ruff.toml`, which is
a standard ruff location and is not a dependency manifest. This is a genuine
improvement in its own right — packaging metadata stays separate from tool
configuration — but the gate's false positive is what surfaced it, and the next
host to add a `[tool.*]` key will hit the same refusal.

Open a nucleus PR from a separate `.agents` clone — do not edit the submodule
here (`agents.md §3 strict_rule`, `§4 feedback_upstream`).
