# DOM Probe Notes — Sprint 006 (W2)

**Probe**: `scripts/probe_chat_start.py` · **Question**: does WhatsApp Web draw a
start-of-conversation marker, and in how many chats?

**Status**: 🟡 **RUN ONCE, INCONCLUSIVE.** Run 1 (`2026-08-30T21:21:45Z`,
`data/probes/chat_start_probe_20260830T212145Z.json`) requested 5 chats and
probed **1**. The other four died on a probe defect, now fixed. The verdict
below stays `inconclusive` and W3 stays gate-locked until a run probes five.

> The tables carry only what run 1 measured. Filling the rest from the Sprint
> 005 spike, from WhatsApp's documented structure, or from the exporter's own
> selectors would reproduce `KI-004-A` exactly: three successive theories about
> message direction were reasoned rather than measured, all three were wrong,
> and all three shipped.

---

## 1. Why this probe exists

`complete: true` has never been produced — not once, in any run
(`grep -rl '"complete": true' data/ | wc -l` → `0`). Two explanations are open,
and the sprint's Approval Gate authorized W1–W2 **only**, so that the ADR (W3)
is written against the answer rather than alongside it:

| Hypothesis | Claim | Consequence if true |
| :--- | :--- | :--- |
| **H1** | The marker exists in some chats; no uncapped run has ever met one | `complete: true` is reachable. The criterion stands and needs execution, not redesign |
| **H2** | The marker is absent from this operator's chats | The criterion is unusable in practice. `ADR-0004` must replace it |

The probe also decides neither if the marker turns out to be **non-reproducible
between runs over the same chat**. That is the plan's abort criterion, and it is
a third possible outcome, not a failure of the probe.

---

## 2. How to run it

The probe needs at least five distinct chats, **one of them deliberately short**.
A short conversation is where a start marker has the best chance of being on
screen at all, so its absence there is much stronger evidence for H2 than its
absence in a long one.

```
.venv/bin/python scripts/probe_chat_start.py \
    -q <fragment-1> -q <fragment-2> -q <fragment-3> \
    -q <fragment-4> -q <short-chat-fragment>
```

| Exit code | Meaning |
| :--- | :--- |
| `0` | Probe met the five-chat minimum. The verdict in the report is evidence |
| `3` | Probe ran but probed fewer chats than the minimum. The verdict is anecdote |
| `2` | No chats were requested |

The verdict never changes the exit code: **H2 is a valid measurement, not a
failure.** Evidence lands in `data/probes/chat_start_probe_<stamp>.json`, under
gitignored `data/` because even structural evidence comes from a real session.

**What the probe records, and what it refuses to.** Structural attributes only,
from a fixed allowlist (`data-icon`, `data-testid`, `role`, `class`, `dir`,
`tabindex`). It never reads `innerText`. `data-pre-plain-text`, `title`, `alt`
and `aria-label` are excluded from that allowlist because each can carry a
person's name, and chats appear under the same pseudonymous digest the exporter
writes (`ADR-0003`).

---

## 3. Evidence — start-of-conversation marker

One row per probed chat. `chat_id` is the pseudonymous digest, never a name.

| `chat_id` | Rows seen | Stopped reason | Passes | Marker found | Matched selector |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `chat_1fc92bb` | 54 | `stalled` | 5 | **No** | — |
| _(4 more needed)_ | | | | | |

**Run 1 probed one chat of five.** Chats 2–5 all failed identically with
`Chat search box not found`, a defect in the probe rather than a finding about
WhatsApp: `export_one` opens one chat per process, so a second search on one
page had never been exercised. Fixed (§6).

**Per-selector match counts.** A selector that fires on the *wrong* node is a
different defect from one that never fires, and only this table separates them.

| Selector | Matches in run 1 (1 chat) | Notes |
| :--- | :--- | :--- |
| `#main [data-icon="lock-refreshed"]` | 0 | |
| `#main [data-testid="msg-system"] [data-icon="lock"]` | 0 | |
| `#main div.message-system [data-icon="lock"]` | 0 | |

**Top-of-panel chrome.** For a chat where no selector matched, this is what
WhatsApp drew at the top *instead* — the evidence that turns "our selector is
wrong" into "there is nothing to select".

| `chat_id` | Node signatures observed above the first bubble |
| :--- | :--- |
| _(pending)_ | |

**Chrome attribute inventory.** The table above is a *sample*: it walks the panel
in document order and stops at `TOP_NODE_LIMIT` nodes. A pre-run verification
against a real Chromium proved that sample can miss a marker buried under a deep
stack of attribute-less wrappers — which is what a live WhatsApp panel is made
of — and a marker that exists but was not sampled reads **exactly like H2**.

This inventory has no limit to fall outside of, so it is the authority for
"there is nothing to select". Where the two disagree, the inventory wins.

| `chat_id` | `data-icon` values | `data-testid` values | `role` values | Chrome nodes |
| :--- | :--- | :--- | :--- | :--- |
| `chat_1fc92bb` | **`{}` — none** | **`{}` — none** | `{"row": 54}` | 54 |

**This is the strongest single result of run 1.** Across the entire message
panel's chrome, WhatsApp drew **not one** `data-icon` and **not one**
`data-testid`. The 54 chrome nodes are all `role="row"` wrappers — the message
rows themselves, whose inner `[data-id]` ancestor keeps their contents out of
the chrome set.

So the failure is not a wrong selector for a marker that exists. In this chat
there is no attribute-bearing chrome node **at all** for a start marker to be.
That is evidence for H2 from one chat; four more are needed before it counts.

The sampled dump (previous table) confirms why the inventory was necessary: all
twelve sampled nodes are obfuscated-class wrappers
(`x1liijdw xu342n7 xelbjmh…`) carrying no `data-icon` or `data-testid`
whatsoever. Had the pre-run fix (§6) not landed, this table would not exist and
the sample alone would have been read as a marker that fell outside the budget.

### Verdict

**`inconclusive` — 1 chat of the 5 required.** One chat with no marker is one
data point, and the plan set five deliberately.

The direction of the evidence is worth stating without granting it authority:
that chat had **no attribute-bearing chrome node at all**, which is a stronger
form of absence than "our selector missed". If four more chats repeat it, H2 is
established. One caveat travels with it — the chat stopped on `stalled`, not on
a proven start, and `history.py:39` records a `stalled` run that once produced a
`complete: true` export of 217 messages from a much longer conversation. A stall
is not proof of having reached the beginning, so even five stalled chats answer
"no marker was drawn where we looked", not "the conversation had no start".

---

## 4. Observation — `unknown_media` (not corrected here)

Plan D3: Sprint 005 exported 6 of 301 rows as `kind: unknown`. Six rows cannot
distinguish a video from a document from a sticker, so this sprint
**characterises** them and Sprint 007 fixes them. The probe records the
structural signature of every unknown row — precisely the evidence that is
missing today.

| `chat_id` | Rows seen | Kind counts | Unknown signatures |
| :--- | :--- | :--- | :--- |
| `chat_1fc92bb` | 54 | `text: 51`, `unknown: 2`, `image: 1` | 2 captured |

Both unknown rows carry the identical signature: `div[data-testid="msg-container"]`,
obfuscated classes, `child_count: 3`, and — the notable part —
**`has_data_id: false`**. Sprint 005's ratio holds (2 of 54 here, 6 of 301 there).

Two rows are still too few to distinguish a video from a document from a
sticker, so this stays Sprint 007's, exactly as `## Out of scope` says. What run
1 adds is the signature itself, which did not exist before.

> **Unplanned finding, outside this sprint.** `has_data_id: false` means these
> rows have no WhatsApp id of their own and fall through to
> `fallback_message_id`, whose key cannot separate two same-kind rows from one
> speaker in one minute — the collapse `history.fallback_message_id` documents.
> `_row_id` recovers via a `[data-id]` ancestor, which the chrome inventory
> confirms exists (it is what excludes bubble contents from the chrome set), so
> nothing is broken. Recorded because it was measured, not because it is due.

---

## 5. Observation — `search_selector_scope` (not corrected here)

Plan D3 and `KI-004-D`. The question is whether any candidate in
`SEARCH_RESULT_SELECTORS` matches nodes **outside `#pane-side`**, which is what
would let a search click land somewhere other than a conversation row. Residual
risk is already bounded — hotfix H-001 turns a wrong click into an abort rather
than a misattributed corpus — so this is measurement for Sprint 007, not a
live defect.

| Selector | Total matches | Matches outside `#pane-side` |
| :--- | :--- | :--- |
| `#pane-side div[role="listitem"]` | **0** | 0 |
| `#pane-side div[role="row"]` | 59 | **0** |
| `[data-testid="cell-frame-container"]` | 36 | **0** |
| `#side div[role="listitem"]` | **0** | 0 |

**Zero leakage on every candidate.** Not one selector matched a node outside
`#pane-side`, which is the answer `search_selector_scope` was waiting for and
the reason it was deferred rather than fixed: the risk it was opened against is
not present in this build.

Two candidates are **dead**: both `role="listitem"` selectors match nothing at
all. `_open_first_result` tries `#pane-side div[role="listitem"]` first, so
every search silently falls through it to `#pane-side div[role="row"]`. Working
as written, but the first-choice selector is inert — Sprint 007 material, and a
finding run 1 produced for free.

---

## 6. Pre-run verification of the probe itself

The probe was exercised before being pointed at any real chat, because a probe
that is wrong produces evidence that is wrong and looks exactly the same.

| Harness | What it covered | Result |
| :--- | :--- | :--- |
| Pure logic, fake page objects | `summarize` verdicts, `scroll_to_top` termination, marker counting, kind census, scope tally, degradation on an unopenable chat | 27/27 |
| Real Chromium, synthetic WA-shaped DOM | The actual Playwright API and the probe's JavaScript, against a panel with an encryption notice, message bubbles, an unknown medium and a stray row outside `#pane-side` | 24/24 |

Neither harness is in the repository: `tests/test_completeness.py` (W5) is
gate-locked, so writing tests into `tests/` would have breached `task_scope`.
They live in the session scratchpad.

**A second defect was found by run 1 itself**, which no harness had reached:
`export_one` opens one chat per process, so a *second* search on one page was
never exercised. The box kept the previous query, stopped matching on its
placeholder, and chats 2–5 all failed with `Chat search box not found`.
`open_for_probe` now dismisses search state before each open and reloads the
chat list as a fallback; four tests pin it, and all four fail with the fix
reverted.

**The first defect was found before any chat was touched.** `top_chrome_signatures` spends
its node budget in document order, and a marker sitting under ~30 nested
wrappers — ordinary for a live WA panel — fell outside the dump. The harness
reproduces it: the sample misses the buried marker while
`chrome_attribute_inventory` finds it. The fix is that inventory, added in the
same commit as the test that proves it.

The defect could never have produced a wrong `complete` value: `at_chat_start`
uses descendant CSS selectors and finds a buried marker regardless. What it
would have corrupted is **this document** — it would have shown an empty chrome
dump for a chat that did have a marker, and the sprint would have concluded H2
from missing evidence rather than from absent evidence.

---

## 7. What happens next

W3–W8 are **not authorized**. The Approval Gate of 2026-08-30 covered W1–W2
only, and section 3's verdict is still `inconclusive`, so nothing about that
changes yet.

**Run 2 is the next action**: the same five chats, with the search-state fix in
place. One of them must be deliberately short.

```
.venv/bin/python scripts/probe_chat_start.py -q <f1> -q <f2> -q <f3> -q <f4> -q <short>
```

Exit `0` means the five-chat minimum was met and the verdict is evidence. Only
then does the sprint return to the human with (H1) or (H2), and only then does
the gate reopen for `ADR-0004`.
