# Chat List Probe Notes — Sprint 007 (W5 / W6)

**Status**: run 1 taken 2026-08-31 and **invalidated by a defect in the probe**.
Run 2 pending. Q1 and Q2 both remain unanswered.

> Run 1's numbers are kept below rather than deleted. The probe reported a
> verdict about a whole list from 3.3% of it, which is the same error
> `history.py:38-44` records for the message panel and `W4a` fixed there two days
> earlier. Keeping the run is the point: the mistake is the lesson, and a deleted
> run cannot be compared against its replacement.

---

## 1. Why this probe exists

Sprint 007 must export **every** conversation, and the enumerator's whole design
turns on two facts nobody has measured. One prior measurement exists and does not
settle either:

| Measured | Where | What it does not answer |
| :--- | :--- | :--- |
| `list_size` from `[data-testid="cell-frame-container"]` | `scripts/probe_chat_start.py:637` | Whether that count is the whole account or only what is rendered |
| 59 rows under `#pane-side div[role="row"]` | Sprint 006, `search_selector_scope` | Same |

### Q1 — Does the chat list virtualize?

The **message** panel does: `history.py:3` records that rows scrolled out of the
viewport are removed from the DOM, which is why the harvest re-reads on every
pass instead of scrolling to the top once. Whether `#pane-side` behaves the same
way has never been checked.

It decides the enumerator's shape. If the list is fully materialised, one
`query_selector_all` is the enumeration. If it virtualizes, "every chat" requires
scrolling the pane itself and merging by identity — the same pattern the message
harvest already uses.

### Q2 — Is a chat's index stable?

WhatsApp orders the chat list by recency and reorders it when a message arrives.
`probe_chat_start._probe_chat_list:820` already guards against this by comparing
digests, and its docstring says why: *"two indices can land on one conversation
mid-run"*.

If position is not a stable identity, an index-driven enumerator exports one chat
twice and skips another **and raises nothing**. That is the failure class of
H-001 — a wrong chat exported silently, found by the operator rather than by the
code — and it is why this sprint's abort criterion is written against exactly
this question.

**Privacy.** Titles are read only to compute `pseudonymous_chat_id` and are never
stored, logged or written to the report (`ADR-0001`). No message body is read.

---

## 2. How it is run

Requires the operator: a real login, a real account, real conversations. It
cannot run unattended and must not be wrapped in a routine.

```
$ .venv/bin/python3 scripts/probe_chat_list.py --scroll-passes 20
```

| Flag | Default | When to change it |
| :--- | :--- | :--- |
| `--scroll-passes` | 20 | Raise it if Q1's verdict comes back `inconclusive`, or if the account has many conversations |
| `--settle-ms` | 1200 | Raise it on a slow connection: a pane that has not rendered yet looks like a pane with nothing left to give |
| `--profile-dir` | `data/browser_profile` | Only to use a different logged-in profile |
| `--out-dir` | `data/probes` | Only to write the report elsewhere. `data/` is gitignored |

Exit codes: `0` both questions carry a verdict · `3` a verdict is
`inconclusive`. A verdict of `virtualized` or `unstable` is a **measurement, not
a failure**, and exits `0`.

The report lands at `data/probes/chat_list_probe_<stamp>.json`. It is gitignored:
even structural evidence comes from a real session.

---

## 3. Evidence — Q1, virtualization

### Run 1 — 2026-08-31, `chat_list_probe_20260831T105333Z.json` — **INVALID**

Command: `.venv/bin/python3 scripts/probe_chat_list.py --scroll-passes 20`

| Pass | Rendered rows | New digests | Total distinct | `scroll_top` | `scroll_height` | `client_height` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 70 | 70 | 70 | 0 | 68 407 | 746 |
| 2 | 70 | 0 | 70 | 746 | 68 407 | 746 |
| 3 | 70 | 0 | 70 | 1 492 | 68 407 | 746 |
| 4 | 70 | 0 | 70 | 2 238 | 68 407 | 746 |

| Summary | Value |
| :--- | :--- |
| Max rendered at once | 70 |
| Total distinct digests | 70 |
| Passes used | 4 of a 20 cap |
| Rows with no readable title | 0 |
| Title selector that worked | `span[title]` — the **third** candidate |
| Pane traversed | 2 238 + 746 of 68 407 px = **4.4%** |
| Verdict as printed | `not-virtualized` |
| **Verdict as it stands** | **INVALID — the sweep never reached the foot of the pane** |

**Why it is invalid.** The probe stopped after three passes produced no new
digest and concluded `not-virtualized`, having moved through 4.4% of the pane.
An unchanged count over a stretch that was never finished is equally what a
sweep still inside the render buffer looks like: the list keeps far more than one
viewport of rows in the DOM, so scrolling 746 px at a time revealed nothing new
while 66 km of pane remained below.

**What the geometry suggests, and is not claimed.** 68 407 px against 70 rendered
rows is roughly 977 px per rendered row, where a chat row renders at something
like 72 px. That arithmetic points at a list of several hundred conversations
with a 70-row render window — i.e. **virtualized** — but it is an inference from
a ratio, not a measurement, and this document does not record inferences as
findings. Run 2 measures it.

**The fix** (`0d0d0b6`): `virtualization_verdict` now returns `inconclusive`
unless the sweep reached the foot of the pane, `at_pane_bottom` decides that from
the geometry, and the default cap rose from 20 to 400 — 20 could not have
traversed this pane even with a correct stop rule (68 407 / 746 ≈ 92 passes).
`virtualized` still needs no such condition: seeing more conversations than were
ever in the DOM at once proves it wherever it is observed.

### Run 2 — pending

| Pass | Rendered rows | New digests | Total distinct | `scroll_top` | `scroll_height` | `at_bottom` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| | | | | | | |

| Summary | Value |
| :--- | :--- |
| Max rendered at once | |
| Total distinct digests | |
| Passes used | |
| Pane coverage | |
| Reached bottom | |
| **Verdict** | |

**How to read it.** `total_distinct > max_rendered_at_once` means scrolling
revealed conversations the DOM did not already hold — the list virtualizes. Equal
counts mean it does not, **but only if `reached_bottom` is true**; otherwise the
verdict is `inconclusive`
(`tests/test_probe_chat_list.py::test_a_sweep_that_never_reached_the_bottom_decides_nothing`).

---

## 4. Evidence — Q2, index stability

### Run 1 — 2026-08-31 — **valid but narrow**

| Reading | Rows | Taken after |
| :--- | :--- | :--- |
| 1 | 70 | The (truncated) scroll sweep of §3 |
| 2 | 70 | Scroll to top plus one 1 200 ms settle |

| Summary | Value |
| :--- | :--- |
| Positions compared | 70 |
| Positions that changed | **0** |
| Changed positions | none |
| Duplicate digests within reading 1 | **0** |
| Verdict | `stable` |

**This result survives run 1's defect, and it is narrower than it looks.** It was
measured over the 70 rows the DOM held, across the top ~4% of the list, with the
two readings seconds apart. What it establishes: within one render window and
over a few seconds, position is identity and no two of those 70 conversations
share a title. What it does **not** establish: that position survives the minutes
an enumeration of several hundred chats would take, or that titles stay unique
across the whole list. Run 2 re-measures both over the full pane.

**Corroboration for the title selector.** `span[title]` is generic enough that it
could in principle have matched a message-preview span rather than the chat name,
which would make every digest meaningless. Two facts argue against that: 0 of 70
rows were untitled, and 0 of 70 digests changed between readings — a preview
string is not a stable per-row value. That is corroboration, not proof; run 2
inherits the question.

### Run 2 — pending

| Summary | Value |
| :--- | :--- |
| Positions compared | |
| Positions that changed | |
| Duplicate digests within reading 1 | |
| **Verdict** | |

**How to read it.** Any changed position means index is not identity and the
enumerator must key on the digest. **Duplicate digests within one reading** is
the more serious finding: `pseudonymous_chat_id` hashes the title alone, so two
conversations with the same title collapse into one identity
(`tests/test_probe_chat_list.py::test_two_chats_sharing_a_title_collide_into_one_digest`).
If that count is above zero *and* positions also change, neither position nor
digest identifies a conversation, and **the sprint's abort criterion fires**
(`IMPLEMENTATION_PLAN.md` §Abort criterion): block C is abandoned and the sprint
closes on block A plus this finding.

The two readings are separated only by a scroll and a settle. An enumerator does
strictly more between conversations — it opens each one — so instability measured
here is a **lower bound**, not the worst case.

---

## 5. What this probe deliberately does not do

| Not done | Why | Where it goes |
| :--- | :--- | :--- |
| Open any conversation | Q1 and Q2 are answered from the list alone, and opening chats is what block C does. A probe that exports is not a probe | W7–W11 |
| Fix `search_open_defect` (H-002 candidate) | Enumeration removes search from the path entirely, so the defect stops mattering for this route. It still affects `export-one` | `docs/active_state.json`, `RA-03` if reported live |
| Classify `unknown_media` | Needs the signatures already captured in the Sprint 006 run-3 report and an analysis of its own | Sprint 008 |
| Measure how long a full enumeration takes | Needs block C to exist | After W11 |

---

## 6. What happens next

1. Operator runs the command in §2.
2. §3 and §4 are filled **from the JSON report**, not from recollection.
3. The verdicts decide W7: a stable, fully-materialised list makes the enumerator
   a single read; anything else makes it a scroll-and-merge keyed on the digest.
4. If both verdicts are adverse in the way §4 describes, the abort criterion is
   invoked rather than worked around.
