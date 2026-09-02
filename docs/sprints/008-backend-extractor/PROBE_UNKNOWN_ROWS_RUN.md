# Unknown-row probe — run record (Sprint 008, unit C3)

**Status**: `NOT RUN` — awaiting the operator.
**Probe**: `scripts/probe_unknown_rows.py` (unit C1, `3669a49`)
**Blocked by**: a live, authenticated WhatsApp Web session. No agent can scan
the QR code, so this unit was declared operator-gated in the Implementation
Plan's **Out of scope** table before execution began, not discovered blocked
afterwards.

---

## What this file is for

The probe writes JSON evidence to gitignored `data/`, which never reaches the
repository. This file is where the *findings* from that evidence live, so the
measurement survives the run.

## What is being measured, and why it is not being fixed

| Field | Sprint 007 live run | Earlier measurement |
| :--- | :--- | :--- |
| `sender: unknown` | 5 of 129 messages (3.9%) | 0 of 513 in Sprint 004 |
| `kind: unknown` | 30 of 311 rows (9.6%) | 6 of 301 in Sprint 005, 2 of 54 in probe run 2 |

Both rose, and nothing measured so far separates "chat-dependent" from
"regression". `KI-004-A` forbids theorising over this DOM without data: three
direction hypotheses have already shipped wrong, the last producing a
513-message export with every sender `unknown`. Sprint 008 therefore builds the
instrument and stops. The classification decision belongs to Sprint 009, made
against what this run returns.

## How to run it

Requires a logged-in Chromium profile — the same one `wa-extract login`
established.

```bash
python3 scripts/probe_unknown_rows.py --chats 5 --max-signatures 12
echo "EXIT=$?"
```

| Exit | Meaning |
| :--- | :--- |
| `0` | At least one unknown row was captured — the run produced evidence |
| `3` | No unknown rows found, so this run characterises nothing. Not success: re-run against more conversations |

The JSON lands in `data/unknown_rows_probe_<stamp>.json`. Do not commit it —
`data/` is gitignored and the CI job `no exported chats committed` will refuse a
tracked file under it.

## Privacy properties of the output

Verified by test, not by inspection
(`tests/test_probe_unknown_rows.py`, unit C2):

| Property | Test |
| :--- | :--- |
| No `aria-label` **value** reaches a signature — only its presence and whether it ends in a colon | `test_no_attribute_value_reaches_a_signature` |
| No `data-pre-plain-text` value reaches a signature | same test |
| No message body reaches a signature — only `has_body` | `test_no_message_body_reaches_a_signature` |
| The chat title is hashed through `pseudonymous_chat_id`, never stored | `probe_open_chat` |

Both attributes carry the sender's real name, which is why presence is recorded
and content is not.

## Findings

_To be completed after the run._

| Question | Answer | Evidence |
| :--- | :--- | :--- |
| Is the `unknown` rate chat-dependent or uniform? | — | — |
| Do unknown-`sender` rows share a selector profile? | — | — |
| Do unknown-`kind` rows share one? | — | — |
| Are the two populations the same rows, or disjoint? | — | — |
| Is there a signal present on these rows that no current selector consults? | — | — |

The last question is the one that decides Sprint 009's scope. A `NO` means the
rows genuinely carry nothing readable and `unknown` is the correct output; a
`YES` names the selector to add.

## If this is still `NOT RUN` at the Sprint 008 close

That is an acceptable outcome and was planned for. The deliverable of Block C is
the **instrument**, which is committed, tested and invocable without a browser
(`python3 scripts/probe_unknown_rows.py --help` exits `0`). This record then
carries forward to Sprint 009 unchanged, and the sprint says so in its closeout
rather than implying the measurement was taken.
