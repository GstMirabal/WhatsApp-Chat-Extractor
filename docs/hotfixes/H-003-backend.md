# 🚑 Hotfix: H-003-backend
**File**: `docs/hotfixes/H-003-backend.md` (RA-03 emergency naming — sanctioned exception to RA-06)
**Severity**: `CRITICAL`
**Detected**: 2026-09-08 · **Resolved**: 2026-09-08

---

## 1. Symptom

A whole-account `export-all` run stopped producing conversations while the
process stayed alive and kept logging. Run `20260902T214002Z`, resumed at
2026-09-07T21:46:46Z, exported 70 conversations in roughly 75 minutes, then
opened conversation 249 of 991 (`chat_d4fd97c1ada0`) at 2026-09-07T23:02Z and
harvested it for **4 hours 24 minutes without collecting a single message**.
The log at the moment of diagnosis read `Pass 890: +0 new, 0 total (stall
889/3)` — a stall counter at 889 against a threshold of 3.

Blast radius: any conversation whose "load earlier messages from your phone"
request the phone never answers costs `max_passes × load_wait_ms` before the
run moves on — 2000 × 15 s ≈ **8.3 hours per affected conversation** at the
defaults. With 991 conversations enumerated, a handful of such conversations
makes a whole-account export impossible to finish. The operator killed the
first run on 2026-09-03 for the same reason.

## 2. Root Cause

`src/whatsapp_chat_extractor/history.py:247`, in `decide_stop`:

```python
if stall_count >= stall_threshold and not panel_loading:
    return STOP_STALLED
```

The spinner suppression is **unbounded**. `panel_is_loading`
(`history.py:254-266`) returns True whenever any `LOADING_SELECTORS` element is
present, and WhatsApp Web leaves that indicator up indefinitely when it has
asked the paired phone for older messages and the phone does not deliver. The
first pass of the affected conversation shows exactly that sequence:

```
No message rows found
Pass 1: +0 new, 0 total (stall 0/3)
Clicked load-earlier control: 'Haz clic aquí para obtener mensajes anteriores de tu teléfono'
```

With `panel_loading` permanently True, the stall branch can never fire, and the
only remaining exit is `passes_used >= max_passes`.

The suppression itself is correct and must stay: a spinner is positive evidence
that more history is coming, and stopping on it would report a top that was
never reached. What is missing is a **bound** on how long that evidence is
believed.

`classify_completeness` (`history.py:269-294`) states the assumption this
defect breaks: it calls the `stalled`-while-loading pairing *"defensive rather
than reachable"*. It is reachable, and it was reached for 890 consecutive
passes.

**Empirical basis for the bound.** Across the 250 conversations this project
has exported under schema v6:

| `passes_used` | Value |
| :--- | :--- |
| Minimum | 4 |
| Median | 4 |
| 90th percentile | 6 |
| Maximum | 13 |
| Over 20 passes | 0 |

No real conversation has needed more than 13 passes. The default cap is 2000.

## 3. Fix Applied

| File | Change |
| :--- | :--- |
| `src/whatsapp_chat_extractor/history.py` | Bound the spinner suppression: a new `loading_grace` parameter caps how many consecutive stalled passes `panel_loading` may suppress, and a new `STOP_LOADING_UNRESOLVED` reason ends the harvest honestly when it is exceeded |
| `tests/test_completeness.py` | Pin the new reason's classification and the bound's behaviour |

`classify_completeness` needs no change: it fails closed, so a reason it does
not recognise is already `truncated`. That is the correct classification — a
harvest that stopped because a spinner never resolved has not proven it reached
anything.

Branch/commit: `hotfix/H-003` → `1728519`.

**Branch base is `ai-sprint/009`, not `main`, and the deviation is
deliberate.** `main` is at `d0cdbb4` (`v0.8.1`) and contains no `--resume`: the
run this defect blocks can only be continued from the sprint branch, so a fix
based on `main` would be inert for the operator who reported it. `RA-03`
mandates the branch name, the record and the commit suffix, not the base.

## 4. Verification

| Check | Command |
| :--- | :--- |
| Regression test pins the bound | `python3 -m pytest tests/test_completeness.py -q` → `17 passed` (12 pre-existing + 5 new) |
| Zero regression | `python3 -m pytest -q` → `283 passed, 1 skipped` (up from 278/1, exactly +5) |
| Structural gate | `ruff check .` → `All checks passed!`, exit 0 |
| No function over 50 lines | AST scan of `history.py` and `test_completeness.py`, both `[]` |

Five tests pin the bound. The boundary case — `stall_count == stall_threshold +
loading_grace`, `panel_loading=True` — is chosen so it fails under either of
the two ways this could have been implemented wrong: dropping `loading_grace`
entirely, or using `>=` where the landed code uses `>`. The other four confirm
`at_chat_start` still wins over an unresolved spinner, ordinary non-loading
stalling is unaffected, the bound actually fires past the grace window, and the
new reason classifies as `COMPLETENESS_TRUNCATED` with no change to
`classify_completeness`.

**Proven by mutation, not asserted.** The `loading_grace` branch was removed
from `decide_stop`, restoring the exact pre-hotfix unbounded-suppression
behaviour; the boundary test failed alone (`assert None ==
'loading_unresolved'`), the other 282 stayed green, and the source was restored
byte-for-byte (`git diff --stat -- src/` empty) before the real fix was
recommitted. Without this test, the next change to `decide_stop` can
reintroduce the unbounded suppression and nothing would notice until another
run burned a night.

**One design note the implementation added.** A first attempt at extracting
`_observe_and_decide` (needed to keep `_one_pass` under the 50-line ceiling)
bought its line budget by deleting three explanatory comments — including the
one stating that a pass can add zero rows while the panel is still loading
beneath it, which is the exact interaction this hotfix turns on. Rejected on
review and the prose restored verbatim; the line budget came from the
extraction itself, not from shortening the explanation.

**Operator workaround available before this fix ships**, and it needs no code
change:

```
wa-extract export-all --resume <RUN_ID> --max-passes 40
```

40 is roughly three times the observed maximum of 13 and caps an affected
conversation at 10 minutes instead of 8.3 hours. Truncation is recorded rather
than silent — the export carries `completeness: truncated` and its
`passes_used` — so conversations cut short by the cap can be found afterwards
and re-run with a higher one.

## 5. Rule Amendment Check

- [x] Is this failure class systemic? **Yes, and it is already named.** The
  class is "a termination guarantee that exists but whose cost makes it
  useless": `max_passes` did bound the loop, at 8.3 hours per conversation.
  This is the second defect of the same family found in this software in six
  days — `KI-009-H` recorded an unbounded harvest loop with no timeout at all.
  Both were found by running the software, neither by review, because the whole
  test suite runs without a browser and no test can hang on a live page. Routed
  to `constitutional_escalation` as a proposed amendment: **every loop that
  waits on an external system must state its bound in wall-clock time, not only
  in iterations.** RA reference pending draft: `N/A` until Sprint 010 indexes it.
- [ ] Does the root cause reveal a design decision worth recording as an ADR?
  **No.** The decision to suppress the stall verdict while a spinner is up is
  already recorded and is still correct; this hotfix bounds it rather than
  reversing it, so `ADR-0004` and `ADR-0005` stand unchanged. `N/A`
- [x] Master Ledger entry added under `[Unreleased]` (`CHANGELOG.md`).
