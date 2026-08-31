# Chat List Probe Notes — Sprint 007 (W5 / W6)

**Status**: procedure written, **evidence tables empty**. They stay empty until
`scripts/probe_chat_list.py` runs against a real account.

> The tables below are deliberately blank. Filling them from the Sprint 006 runs,
> from WhatsApp Web's documented structure, or from what the selectors "should"
> return would be `KI-004-A` a fourth time — three successive theories about this
> DOM were each wrong and each shipped. A blank row is an unanswered question; a
> plausible row is a wrong answer nobody will re-check.

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

*Empty until the probe runs.*

| Pass | Rendered rows | New digests | Total distinct | `scroll_top` | `scroll_height` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| | | | | | |

| Summary | Value |
| :--- | :--- |
| Max rendered at once | |
| Total distinct digests | |
| Passes used | |
| Rows with no readable title | |
| Title selector that worked | |
| **Verdict** | |

**How to read it.** `total_distinct > max_rendered_at_once` means scrolling
revealed conversations the DOM did not already hold — the list virtualizes. Equal
counts over two or more passes mean it does not. One pass decides nothing, which
is why `virtualization_verdict` returns `inconclusive` there
(`tests/test_probe_chat_list.py::test_a_single_pass_decides_nothing`).

---

## 4. Evidence — Q2, index stability

*Empty until the probe runs.*

| Reading | Rows | Taken after |
| :--- | :--- | :--- |
| 1 | | The scroll sweep of §3 |
| 2 | | Scroll to top plus one settle interval |

| Summary | Value |
| :--- | :--- |
| Positions compared | |
| Positions that changed | |
| Changed positions (first 20) | |
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
