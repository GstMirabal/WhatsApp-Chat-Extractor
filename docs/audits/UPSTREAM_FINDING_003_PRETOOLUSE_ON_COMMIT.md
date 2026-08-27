# Upstream finding draft — PreToolUse on_commit template (Sprint 003)

**routing_class**: `nucleus`  
**Host**: WhastApp Chat Extractor · Sprint 003 · 2026-08-27  
**Related**: host `KI-001-B`

## Defect

`.agents/claude/settings.hooks.json` (pin v4.23.0) still ships:

```bash
if [ -f .agents/hooks/on_commit.py ]; then python3 .agents/hooks/on_commit.py; fi
```

Cursor/Claude PreToolUse requires JSON on stdout (`{"permission":"allow|deny"}`).
Raw `on_commit.py` prints prose → Cursor blocks the tool with "invalid JSON".

`merge_json.DEPRECATED_HOOK_COMMANDS` only lists the bare
`python3 .agents/hooks/on_commit.py`, so the `if [ -f … ]` form is **not**
pruned. A host that already has the JSON-safe wrapper gets the broken command
**appended** on `install.sh` / bridge refresh.

## Proposed fix (nucleus)

1. Replace the template PreToolUse command with the JSON-safe wrapper (stderr for
   gate prose; stdout only `{"permission":…}`).
2. Add the broken `if [ -f .agents/hooks/on_commit.py ]; then python3 .agents/hooks/on_commit.py; fi`
   string to `DEPRECATED_HOOK_COMMANDS` in `scripts/merge_json.py`.
3. Add a merge test that a host with the safe wrapper does not retain the broken
   duplicate after merge.

## Host mitigation (already applied)

Removed the duplicate broken matcher from host `.claude/settings.json` during
Sprint 003 close prep.

This file is the Sprint 003 `feedback_upstream` draft; open a nucleus PR from a
separate `.agents` clone — do not edit the submodule in place (`strict_rule`).
