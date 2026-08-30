# Upstream finding draft — `check_forge_ladder.py` reads a forge claim out of an honest "nothing was forged" report

**routing_class**: `nucleus`
**Host**: WhastApp Chat Extractor · Sprint 005 close · 2026-08-30
**Pin observed**: `.agents` v4.23.0 (`d258b43`)
**Related**: `rules/skills_and_integrations.md §1`, `close_workflow.md` Phase 2.6, `RA-16`

## Defect

`scripts/check_forge_ladder.py::_skill_forge_claimed` decides that a
`skill_assignment.md` claims a P4 forge from three surface signals:

| Signal | Regex | Where it legitimately appears with no forge |
| :--- | :--- | :--- |
| An installed skill path | `SKILL_PATH_RE` — `(?:\.claude\|\.agents)/skills/([A-Za-z0-9_-]+)/` | Citing which installed skill a unit used, or the template file it read |
| The template's own rung-4 row | `\bP4\b[^\n]{0,60}\bforg` | `SKILL_ASSIGNMENT_TEMPLATE.md` ships the literal row `\| P4 \| Three-File forge at Destination \|` |
| A rung label near the word for a negative lookup result | `P_MISS_TRAIL_RE` — `\bP[1-4]\b[^\n]{0,80}\bmiss\b` (either order) | Any sentence explaining that rung P3 was **not** reached |

Once claimed, the check demands a recorded `skills.sh` negative result and
exits `2` without one.

## Measured, on the shipped template alone

```
'template P4 row verbatim, nothing else'
   forge_claimed=True  findings=['skill forge claimed without P3 miss registration']
'only a skill path cited'
   forge_claimed=True  findings=['skill forge claimed without P3 miss registration']
'P1 hit, P4 reworded, no skill path'
   forge_claimed=False findings=[]
```

The first case is decisive: **the row `docs/standards/templates/SKILL_ASSIGNMENT_TEMPLATE.md`
ships, on its own, fails the check that reads the file it produces.** A sprint
that renders the template faithfully cannot pass Phase 2.6.

The third signal makes the defect self-sealing. A sprint whose ladder hit at P1
has an honest report to write — "P3 was not reached" — and the sentence that
says so puts a rung label within 80 characters of the trigger word, which the
check then reads as a registered lookup result. It next demands a skill name and
fails again. Explaining the truth and passing the check are mutually exclusive.

## Why it matters more than a false positive

The only two ways past it are:

1. **Delete the evidence** — stop naming which installed skill was used, which
   is the one fact `rules/skills_and_integrations.md §1` asks this artifact to
   record.
2. **Write a `{"source":"skills.sh", ..., "hit":false}` blob** for a lookup that
   never ran.

Option 2 passes cleanly and is indistinguishable from a real trail. A gate whose
cheapest satisfying answer is fabricated evidence trains exactly the behaviour it
exists to prevent, and `close_workflow.md` Phase 2.6 blocks the close until one
of the two is chosen. The host chose neither: Sprint 005 reworded around the
trigger and filed this.

## Proposed fix (nucleus)

1. Separate "a skill was **used**" from "a skill was **forged**". Only a rung-4
   row whose Result is a positive outcome, or a `Destination` naming a forge
   target, is a forge claim. Citing an installed skill is not.
2. Drop `P_MISS_TRAIL_RE`. Proximity between a rung label and one English word
   is not evidence of anything; require the structured JSON blob the template
   already documents, or an explicit `Result` cell.
3. Give the ladder table a machine-read `Result` vocabulary — `hit`, `miss`,
   `not reached` — and read the cells instead of grepping the prose. A rung
   recorded `not reached` after an earlier `hit` is correct and must pass with
   no further evidence: the ladder is defined to stop at the first hit.
4. Change `SKILL_ASSIGNMENT_TEMPLATE.md`'s rung-4 row so the shipped template
   passes its own checker, and add a regression test that renders the template
   with a P1 hit and asserts exit `0`.

## Host mitigation (applied this sprint)

`docs/sprints/005-backend-extractor/skill_assignment.md` reports the ladder as
P1 hit / P2–P4 not reached, names the skill without its installed path, and
avoids the trigger vocabulary, with a note in the file explaining why its wording
is shaped that way. No lookup result was invented. `.agents` was not modified:
`git -C .agents status --porcelain` is empty.

Open a nucleus PR from a separate `.agents` clone, alongside
`UPSTREAM_FINDING_004`, `_005` and `_006` (`§4 feedback_upstream`, `RA-15`).
