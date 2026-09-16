# Upstream finding draft — the skill-count check counts the Claude Code bridge's own bookkeeping directory as a skill

**routing_class**: `nucleus`
**Severity**: LOW
**Host**: WhatsApp Chat Extractor · Sprint 012, `make verify` · found 2026-09-16
**Pin observed**: `.agents` v4.30.0
**Related**: `scripts/check_readme_counts.py`, `scripts/install.sh --target claude`, `agents.md §3 federation`

## Defect

`scripts/check_readme_counts.py:77-78` counts `README.md`'s claimed skill
total against `len([p for p in Path("skills").iterdir() if p.is_dir()])` —
every directory under `skills/`, with no filter on the name.

`scripts/install.sh --target claude` (the Claude Code bridge) creates
`skills/.claude/.cc-writes/` inside the `skills/` directory as its own
runtime bookkeeping — confirmed empty of any `SKILL.md`, `README.md` or
`/scripts/`, i.e. not a skill under the Three-File Standard by any reading.
`iterdir()` does not skip dotfile-prefixed entries, so this bookkeeping
directory counts as one more "skill" than `README.md`'s own "N flat skills"
line can ever state correctly — the drift is permanent on any host that has
run the Claude Code bridge install, not a one-time staleness that editing
the README fixes.

## Observed

```
$ python3 scripts/check_readme_counts.py
❌ README counts have drifted from the tree:
  • skills: README says 34, tree has 35.
$ python3 -c "from pathlib import Path; print([p.name for p in Path('skills').iterdir() if p.name.startswith('.')])"
['.claude']
$ ls -la skills/.claude/
.cc-writes/
```

34 is the real count of Three-File-Standard skills; 35 is 34 plus the
bridge's own directory. Bumping the README to say "35 flat skills" would
make the check pass while making the documented count wrong — the fix
belongs in the counting glob, not in the number.

## Proposed fix

Exclude dotfile-prefixed entries from the `skills` count in
`check_readme_counts.py` (`p for p in Path("skills").iterdir() if p.is_dir()
and not p.name.startswith(".")`), mirroring how `topological_order`
(`agents.md §3`) already treats `skills/` as flat and every real skill name
as a plain identifier, never a dotfile.

## Host action taken

None — cannot write inside `.agents` from a host session (`strict_rule`).
Not blocking: `make verify`'s other checks all passed; this single line was
the only failure, and it is cosmetic (a documentation count) rather than
structural. Left red rather than silently patched around.
