# Upstream finding draft — the bridge installer deletes host-authored commands, then gitignores the evidence

**routing_class**: `nucleus`
**Severity**: HIGH
**Host**: WhatsApp Chat Extractor · `/agents:start` boot · 2026-08-30
**Pin observed**: `.agents` v4.23.0
**Related**: `agents.md §3 federation`, `§3 strict_rule`, `scripts/install.py`, `start_workflow.md` `bridge_check`

> **Scope note.** This finding was not in Sprint 008's approved Work table. It
> was found while drafting `_008`–`_011`, which the anchor listed as the
> outstanding set: the anchor's `upstream` summary says *eight* findings and
> names `_004`–`_011`, but `bridge_clobbers_host_commands` records a twelfth
> that the summary omits. Drafted here rather than left out, because it is the
> same class and the same destination as the four that were approved, and
> leaving it undrafted would reproduce exactly the gap this block exists to
> close.

## Defect

`scripts/install.py --target cursor` rebuilds the mirrored commands directory
**exclusively** from `.agents/commands/`, so any file living alongside the
mirrored ones is destroyed. It then appends the directory to the host
`.gitignore`, which hides the next such loss from `git status` entirely.

`agents.md §3 federation` names `install.sh` as *the* sanctioned bridge into the
host's configuration and describes it as *"symlinks + non-destructive JSON
merge"*. The observed behaviour is destructive, and it is destructive toward
host-authored content specifically.

## Observed

During an `/agents:start` boot on 2026-08-30 the bridge install:

| # | Action | Object |
| :--- | :--- | :--- |
| 1 | Deleted | `.cursor/commands/wa-export.md` — a **git-tracked** host project command, source at `.claude/commands/wa-export.md` |
| 2 | Appended | `/.claude/commands/` and `/.cursor/commands/` to the host `.gitignore` |

Step 2 is what turns a recoverable mistake into a silent one. The deletion in
step 1 was noticed only because the file was tracked and `git status` reported
it **before** the ignore entries landed. With the ignore rules in place, the
same deletion on the next boot produces no output at all.

Both were reverted in the same session (`git checkout` for the file, the
`.gitignore` change backed out) and the tree was left clean.

## Impact

1. **Host content is destroyed by a framework routine**, inverting
   `§3 strict_rule`: the host is forbidden from writing into the framework, and
   here the framework silently overwrites the host.
2. `wa-export` is this host's only project slash command and it is referenced
   from `EXTRACTOR_BLUEPRINT.md §3` as a declared interface. Its loss is a
   documented-interface regression, not a cache miss.
3. The added ignore rules make the failure **self-concealing**. A host that does
   not catch it on the first boot has no mechanism to catch it later.
4. Any host that keeps its own commands beside the mirrored ones — the natural
   layout, since both are Claude Code commands — is exposed on every boot.

## Proposed fix

Three parts, in order of importance:

| # | Change | Reason |
| :--- | :--- | :--- |
| 1 | The installer must **preserve files it did not author**. Track provenance (a manifest of mirrored filenames, or a marker in mirrored files) and remove only those | A rebuild that cannot tell its own output from someone else's must not delete |
| 2 | It must **not** add a `.gitignore` entry for a directory that holds host-tracked files | The concealment is worse than the deletion |
| 3 | If ignoring the mirror is genuinely wanted, ignore the mirrored **filenames**, not the directory | Keeps host commands visible to `git status` |

A regression test should place an unmirrored file in the target directory, run
the installer, and assert the file survives.

`bridge_check` runs on every boot under both harnesses, so the blast radius is
every host on every session, not an occasional path.
