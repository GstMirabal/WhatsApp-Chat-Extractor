# 🚑 Hotfix: H-001-backend
**File**: `docs/hotfixes/H-001-backend.md` (RA-03 emergency naming — sanctioned exception to RA-06)
**Severity**: `HIGH`
**Detected**: 2026-08-30 · **Resolved**: 2026-08-30

---

## 1. Symptom

`open_chat_by_query` types the search string but does not enter the target
conversation, and still returns successfully. The operator reported on
2026-08-30 that the chat had to be clicked by hand. The visible hang is the
benign symptom. The severe one is silent: when nobody clicks, the export is
written **for whichever conversation was already on screen** and the process
exits `0`. Because `chat_id` is a digest and the title is deliberately not
stored (identity contract, Sprint 004), the output file carries **no evidence of
which conversation it came from**. A corpus attributed to the wrong person is
worse than an absent corpus. Blast radius: every `wa-export` run, all exported
JSON produced without a manual click. Inherited from Sprint 003; not introduced
by Sprint 005.

## 2. Root Cause

Three independent defects in `src/whatsapp_chat_extractor/export_one.py`, none
of which can observe the failure:

| Line | What it does | Why it cannot detect the failure |
| :--- | :--- | :--- |
| `48-53` `SEARCH_RESULT_SELECTORS` | First entry is `#pane-side div[role="listitem"]` | That selector matches the **ordinary chat list**, which exists whether or not a search is active. It is not search-scoped |
| `176-191` `_open_first_result` | Clicks `loc.first` and returns | Returns **without verifying a conversation opened**. Any non-empty chat list satisfies it |
| `211` `open_chat_by_query` | Waits for `MESSAGE_PANEL_SELECTORS` | When a conversation is already open the selector is **already satisfied**, so the wait returns instantly and proves nothing |
| `219-222` | `read_open_chat_title(page) or query` | Reads the title of whatever is open and **never compares it to `query`**; falling back to `or query` fabricates agreement |

The common root cause is that **every check is satisfiable by the pre-existing
page state**. A wait on an already-satisfied selector is not a wait, and a title
that is read but never compared is not a verification.

Measured evidence (Sprint 005 W2 probe): a run with `--query "test"` — a string
naming no chat — returned success and measured a 36-row window identical to the
one returned afterwards for the real chat name. It had not matched anything; it
measured the conversation already on screen. A second `"test"` run with no
conversation open did raise `RuntimeError`, which is the behaviour consistent
with this diagnosis.

## 3. Fix Applied

| File | Change |
| :--- | :--- |
| `src/whatsapp_chat_extractor/export_one.py` | Added search-scoped `SEARCH_RESULT_SELECTORS` entries ahead of the `#pane-side` fallbacks |
| `src/whatsapp_chat_extractor/export_one.py` | `open_chat_by_query` captures the open-chat title **before** searching and requires it to change, so an already-satisfied panel cannot pass |
| `src/whatsapp_chat_extractor/export_one.py` | `open_chat_by_query` matches the resolved title against `query` and raises `RuntimeError` on mismatch; the `or query` fallback that fabricated agreement is removed |
| `tests/test_open_chat_verification.py` | Regression test pinning all three failure modes |

Fail-closed is deliberate. When the title cannot be read, the run now aborts
instead of proceeding: an unverifiable chat identity is the exact condition that
produces a mislabelled corpus.

Branch/commit: `hotfix/H-001` → see section 4.

## 4. Verification

```
python3 -m pytest tests/ -q
ruff check .
```

Regression test added: `tests/test_open_chat_verification.py`, pinning the
failure modes that previously passed —

1. A page whose conversation panel is **already open** and whose search changes
   nothing must make `open_chat_by_query` raise, not return.
2. A resolved title that does not contain `query` must raise.
3. An unreadable title must raise rather than fall back to `query`.

## 5. Rule Amendment Check

- [x] Is this failure class systemic (a process pattern, not a one-off)? **Yes.**
      The pattern is *verifying a post-condition with a predicate that the
      pre-existing state already satisfies* — a wait on an open panel, a click on
      an always-present list, a title read but not compared. It is a general
      automation defect class, not specific to WhatsApp. Proposed as
      `UPSTREAM_FINDING_009` for `constitutional_escalation` rather than patched
      into `agents.md` directly, since `strict_rule` forbids a host editing the
      submodule: **RA-XX candidate — a post-condition check MUST distinguish the
      state it intends to cause from the state that already held.**
- [x] Does the root cause reveal a design decision worth recording? **Yes** —
      fail-closed on unverifiable chat identity, chosen over best-effort export.
      Recorded here and in the Master Ledger; it extends the ADR-0003 principle
      (never synthesize a value indistinguishable from a measured one) from
      timestamps to chat identity.
- [x] Master Ledger entry added under `[Unreleased]`.
