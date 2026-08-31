# Chat List Probe Notes — Sprint 007 (W5 / W6)

**Status**: **Q1 and Q2 both ANSWERED** by runs 2 and 3. The chat list is
virtualized — 899 conversations behind a 70-row window — and a chat's position is
stable across the ~2 minutes a full sweep takes, with zero title collisions in
7 100 row observations. The abort criterion is **not** triggered. Block C
proceeds.

> Every run is kept below, including the two whose verdicts were wrong. Each
> failure was found by the *next* measurement rather than by review, and a
> deleted run cannot be compared against its replacement. Run 1's Q1 verdict and
> both Q2 verdicts are marked INVALID in place.

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
$ .venv/bin/python3 scripts/probe_chat_list.py
```

No flag is needed. The sweep runs until it reaches the foot of the pane; the cap
only guarantees termination. On run 1's geometry (68 407 px against a 746 px
viewport) that is roughly 92 passes at 1 200 ms each — **about two minutes**, and
the browser window must stay open and focused throughout.

| Flag | Default | When to change it |
| :--- | :--- | :--- |
| `--scroll-passes` | 400 | Raise it only if the log warns that the sweep never reached the foot of the pane. It was 20 for run 1, which could not have traversed that pane under any stop rule |
| `--settle-ms` | 1200 | Raise it on a slow connection: a pane that has not rendered yet looks like a pane with nothing left to give |
| `--profile-dir` | `data/browser_profile` | Only to use a different logged-in profile |
| `--out-dir` | `data/probes` | Only to write the report elsewhere. `data/` is gitignored |

Exit codes: `0` both questions carry a verdict · `3` a verdict is
`inconclusive`, **which now includes a sweep that never reached the foot of the
pane**. A verdict of `virtualized` or `unstable` is a **measurement, not a
failure**, and exits `0`.

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

### Run 2 — 2026-08-31, `chat_list_probe_20260831T110305Z.json` — **Q1 ANSWERED**

Command: `.venv/bin/python3 scripts/probe_chat_list.py` (after fix `0d0d0b6`)

| Pass | Rendered rows | New digests | Total distinct | `scroll_top` | `at_bottom` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 70 | 70 | 70 | 0 | No |
| 2 | 70 | 0 | 70 | 746 | No |
| 3 | 70 | 0 | 70 | 1 492 | No |
| … | … | … | … | … | … |
| 99 | 68 | 5 | 894 | 65 828 | No |
| 100 | 68 | 0 | 894 | 66 494 | No |
| 101 | 68 | 0 | 899 | 67 160 | No |
| 102 | 68 | 0 | 899 | 67 817 | **Yes** |

| Summary | Value |
| :--- | :--- |
| Max rendered at once | **70** |
| Total distinct digests | **899** |
| Row observations across the sweep | 7 033 |
| Passes used | 102 of a 400 cap |
| Pane coverage | **100.0%** (67 817 + 666 of 68 483 px) |
| Reached bottom | **Yes** |
| Rows with no readable title | **0 of 7 033** |
| Title selector that worked | `span[title]` — the third candidate |
| **Verdict** | **`virtualized`** |

**Q1 is answered: the chat list virtualizes.** 899 distinct conversations were
seen while the DOM never held more than 70 rows at once. That is a proof rather
than an inference — `virtualization_verdict` returns `virtualized` on this
evidence regardless of coverage, because seeing more conversations than were ever
rendered simultaneously cannot happen any other way. The sweep also reached the
foot of the pane, so the count of 899 is the whole list and not a lower bound.

The passes above also show the fix working: passes 2–4 revealed nothing new — the
exact stretch on which run 1 stopped and declared a verdict — while pass 99 was
still discovering conversations, 65 828 px in.

**What this settles for the enumerator (W7).** A single `query_selector_all` is
not the enumeration; it would return 70 of 899 conversations and report success.
`chat_list.py` must sweep the pane and merge by identity, which is the pattern
`harvest_history` already uses one panel over.

### Run 3 — 2026-08-31, `chat_list_probe_20260831T133447Z.json` — **confirms run 2**

| Summary | Run 2 | Run 3 |
| :--- | :--- | :--- |
| Total distinct digests | **899** | **899** |
| Max rendered at once | 70 | 70 |
| Passes used | 102 | 103 |
| Pane coverage | 100.0% | 100.0% |
| Reached bottom | Yes | Yes |
| Row observations | 7 033 | 7 100 |
| Max title collisions in one window | not measured | **0** |
| Verdict | `virtualized` | `virtualized` |

Two independent sweeps, 2.5 hours apart, both reaching the foot of the pane and
both counting 899. Q1 is reproducible, not a single observation.

**How to read it.** `total_distinct > max_rendered_at_once` means scrolling
revealed conversations the DOM did not already hold — the list virtualizes. Equal
counts mean it does not, **but only if `reached_bottom` is true**; otherwise the
verdict is `inconclusive`
(`tests/test_probe_chat_list.py::test_a_sweep_that_never_reached_the_bottom_decides_nothing`).

---

## 4. Evidence — Q2, index stability

### Runs 1 and 2 — **BOTH INVALID**, and for the same reason

| Run | Reading 1 taken at | Reading 2 taken at | Verdict printed |
| :--- | :--- | :--- | :--- |
| 1 | `scroll_top` 2 238 | `scroll_top` 0 | `stable` — 0 of 70 changed |
| 2 | `scroll_top` **67 817** | `scroll_top` **0** | `unstable` — **68 of 68** changed |

**Neither measured reordering.** The two readings were taken at different scroll
positions of a virtualized list, so they held different *windows*, not the same
window at two times. Run 2 compared the last 68 conversations against the first
69 of 899 — every position differing is arithmetic, not instability. Run 1 got
the opposite verdict from identical code because its sweep had moved only
2 238 px, leaving the two windows almost entirely overlapped.

The row counts give it away without any further analysis: run 2 reported
`reading_1_rows: 68` against `reading_2_rows: 69`. Two readings of one window do
not disagree about how many rows that window has.

**This retracts the "valid but narrow" reading previously recorded here for run
1.** It was neither: `stable` was as much an artifact as `unstable`, and the
paragraph claiming otherwise was written before run 2 exposed the mechanism.

**The fix** (`2b33712`): both readings are now anchored at the pane head
(`read_anchored_at_top`), and the anchor is written into the report so a reader
can see which question was answered. Reading 1 is taken **before** the sweep and
reading 2 **after** it, which makes the sweep itself the interval — on run 2's
timing, roughly two minutes apart, the timescale a real enumeration runs at
rather than an artificial pause.

The same commit adds `max_title_collisions_in_a_window`, counted across every
pass. Two rows rendered together are necessarily two different conversations, so
a repeated digest inside one window is a genuine title collision — which is the
precise question the abort criterion asks, and which neither run measured across
the whole list.

### Run 3 — pending

**Corroboration for the title selector.** `span[title]` is generic enough that it
could in principle have matched a message-preview span rather than the chat name,
which would make every digest meaningless. Two facts argue against that: 0 of 70
rows were untitled, and 0 of 70 digests changed between readings — a preview
string is not a stable per-row value. That is corroboration, not proof; run 2
inherits the question.


| Summary | Value |
| :--- | :--- |
| Positions compared | |
| Positions that changed | |
| Duplicate digests within reading 1 | |
| Max title collisions in one window | |
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

1. Operator runs the command in §2 — **run 3**, after the `2b33712` fix.
2. §4 is filled **from the JSON report**, not from recollection. §3 is settled and
   run 3 only needs to confirm the sweep still reaches the foot.
3. Q1 already decides W7's shape: the list virtualizes, so `chat_list.py` sweeps
   the pane and merges by identity. A single read is not the enumeration.
4. **Q2 came back `stable` with zero title collisions, so W7 keys on the
   digest anyway.** Position is proven stable only over a two-minute sweep, and
   an export of 899 conversations runs far longer; the digest is proven unique
   across the whole list, which is the stronger guarantee of the two.
5. **The abort criterion did not fire.** It required title collisions above zero
   *and* changed positions. Both are zero, so block C proceeds.
6. The cross-run digest churn (§4) is not a blocker but is a real limit on the
   export contract. It goes to W12 and W13, not into `chat_list.py`.
