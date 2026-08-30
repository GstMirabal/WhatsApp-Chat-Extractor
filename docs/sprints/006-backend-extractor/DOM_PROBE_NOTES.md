# DOM Probe Notes — Sprint 006 (W2)

**Probe**: `scripts/probe_chat_start.py` · **Question**: does WhatsApp Web draw a
start-of-conversation marker, and in how many chats?

**Status**: ⏳ **NOT YET RUN.** Every evidence table below is empty on purpose.
The probe drives the operator's real logged-in session against real
conversations, so it cannot run unattended and no session has executed it yet.

> An empty table here is the honest state. Filling it from the Sprint 005 spike,
> from WhatsApp's documented structure, or from a reading of the exporter's own
> selectors would reproduce `KI-004-A` exactly: three successive theories about
> message direction were reasoned rather than measured, all three were wrong, and
> all three shipped.

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

| `chat_id` | Chat length | Stopped reason | Passes | Marker found | Matched selector |
| :--- | :--- | :--- | :--- | :--- | :--- |
| _(pending)_ | | | | | |

**Per-selector match counts.** A selector that fires on the *wrong* node is a
different defect from one that never fires, and only this table separates them.

| Selector | Chats where it matched | Notes |
| :--- | :--- | :--- |
| `#main [data-icon="lock-refreshed"]` | _(pending)_ | |
| `#main [data-testid="msg-system"] [data-icon="lock"]` | _(pending)_ | |
| `#main div.message-system [data-icon="lock"]` | _(pending)_ | |

**Top-of-panel chrome.** For a chat where no selector matched, this is what
WhatsApp drew at the top *instead* — the evidence that turns "our selector is
wrong" into "there is nothing to select".

| `chat_id` | Node signatures observed above the first bubble |
| :--- | :--- |
| _(pending)_ | |

### Verdict

**Not established.** To be written here from the probe's `summary.verdict`,
together with the reasoning, once the probe has run.

---

## 4. Observation — `unknown_media` (not corrected here)

Plan D3: Sprint 005 exported 6 of 301 rows as `kind: unknown`. Six rows cannot
distinguish a video from a document from a sticker, so this sprint
**characterises** them and Sprint 007 fixes them. The probe records the
structural signature of every unknown row — precisely the evidence that is
missing today.

| `chat_id` | Rows seen | Kind counts | Unknown signatures |
| :--- | :--- | :--- | :--- |
| _(pending)_ | | | |

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
| `#pane-side div[role="listitem"]` | _(pending)_ | |
| `#pane-side div[role="row"]` | _(pending)_ | |
| `[data-testid="cell-frame-container"]` | _(pending)_ | |
| `#side div[role="listitem"]` | _(pending)_ | |

---

## 6. What happens next

W3–W8 are **not authorized**. The Approval Gate of 2026-08-30 covered W1–W2
only. Once section 3 carries a verdict, the sprint returns to the human with
(H1) or (H2) on the table, and the gate reopens for `ADR-0004`.
