# Platform Hardening — pending controls

**Status**: CI landed 2026-08-30 (Sprint 004) and **executes since 2026-09-01**
(Sprint 008 — evidence below). Branch protection still **blocked**.
**Blocker**: the repository is private on a free plan, where GitHub does not
offer branch protection or rulesets:

```
GET /repos/GstMirabal/WhastApp-Chat-Extractor/branches/main/protection
{"message":"Upgrade to GitHub Pro or make this repository public
            to enable this feature.","status":"403"}
```

This is a plan limitation, not a token scope problem — the operator's token
carries `repo` and `workflow`.

**Second blocker, found when the CI landed — CLEARED 2026-09-01.** Actions jobs
could not start on this repository: all four checks failed in 2 seconds with

```
The job was not started because recent account payments have failed
or your spending limit needs to be increased.
```

Actions consumes billed minutes on private repositories; on public ones they are
free.

### The billing block is gone — measured, Sprint 008

Re-checked on 2026-09-01 with `gh run list`. CI now executes for real:

| Run | Branch | Event | Conclusion | Duration |
| :--- | :--- | :--- | :--- | :--- |
| `33477613266` | `main` | push | **success** | 23 s |
| `33477552793` | `main` | push | **success** | 20 s |
| `33477448158` | `ai-sprint/007` | pull_request | **success** | 25 s |
| `33360762207` | `main` | push | failure | 4 s |
| `33360697068` | `main` | push | failure | 5 s |

The last two are the old billing signature; the first three are real. Job-level
evidence for `33477613266`, which is what distinguishes a genuine pass from the
2-second failures — these jobs ran **steps**:

| Job | Steps executed | Conclusion |
| :--- | :--- | :--- |
| `ruff` | 7, including `Install ruff` and `Lint` | success |
| `pytest (3.11)` | 8, including `Install package and test dependencies` and `Run tests` | success |
| `pytest (3.13)` | 8, same | success |
| `no exported chats committed` | 5, including `Refuse any tracked file under data/` | success |

Reproduce: `gh run view 33477613266 --json jobs`.

**First sprint verified by CI, not by the operator's Mac.** PR
[`#9`](https://github.com/GstMirabal/WhastApp-Chat-Extractor/pull/9) (Sprint
008) triggered run `33597073031` on `pull_request`, and all four jobs passed
with real work behind them:

| Job | Steps | Duration | Conclusion |
| :--- | :--- | :--- | :--- |
| `pytest (3.11)` | 8 | 19 s | success |
| `pytest (3.13)` | 8 | 18 s | success |
| `ruff` | 8 | 14 s | success |
| `no exported chats committed` | 5 | 7 s | success |

The step counts and durations are the evidence, not the green tick: the billing
failures concluded in 2–5 seconds having executed **zero** steps. Reproduce with
`gh run view 33597073031 --json jobs`.

**What this changes.** Four releases were merged past `ci_gate.py` under
explicit human authorization because no independent infrastructure could run
this code. That is no longer true: `main` has passing CI, and as of PR `#9` a
sprint branch does too, before any merge. What has **not**
changed is the first blocker — branch protection and rulesets still return
`403`, so `ci_gate.py` still cannot read what `main` requires and will still
refuse. Green checks now exist; the gate still cannot see a rule saying they are
mandatory.

**Correction to the record.** `docs/active_state.json` describes the `ci_gate.py`
`403` as *"the token lacks scope"*. That is wrong, and this document had it right
from the start: it is a plan limitation. Re-confirmed 2026-09-01 — the API
returns *"Upgrade to GitHub Pro or make this repository public to enable this
feature"*, which no token scope can satisfy. The anchor is corrected in the same
sprint that measured this.

## Deviation on record — v0.4.0 merged without CI

`ci_gate.py` exited `2` and Sprint 004 was merged anyway, on 2026-08-30, under
explicit authorization from the repository owner. The only verification behind
`v0.4.0` is local: `ruff check .` exit `0`, 62 passing tests, and a live export
run, all executed on the operator's Mac. No independent infrastructure has run
this code.

Written here rather than left in a chat transcript: a release that skipped its
gate should be legible to whoever reads this repository next.

## Deviation on record — v0.5.0 merged without CI (second occurrence)

Sprint 005, PR `#5`, merged 2026-08-30 under explicit authorization from the
repository owner after the same gate refused it again. What was observed, in
full:

| Signal | Value |
| :--- | :--- |
| `ci_gate.py 5` | exit `2` — *"What `main` requires could not be determined … branch protection: forbidden; rulesets: forbidden"* |
| PR checks | `no exported chats committed`, `ruff`, `pytest (3.11)`, `pytest (3.13)` — all `failure` in 2–4 s |
| Steps executed in those jobs | **Zero** |
| GitHub annotation on all four | *"The job was not started because recent account payments have failed or your spending limit needs to be increased."* |

**The red checks are a billing block, not a code failure**, and the distinction
is the reason this table exists: a reader who sees four failed checks against a
merged commit would otherwise conclude the code was known-broken and shipped.
Nothing in `.github/workflows/ci.yml` ran.

The only verification behind `v0.5.0` is local, on the operator's Mac:
`ruff check .` exit `0`, **78** passing tests, a live export of 301 messages
whose written file contains no `blob:`, `data:image` or `https://` URL and no
contact name, and a successful `pip wheel`. No independent infrastructure has
run this code.

This is now a pattern rather than an incident. Two consecutive releases have
been merged past the same gate, and the gate is not at fault: it reported
honestly both times. Until the billing block is cleared, every release here
carries the operator's word alone.

---

## What already works on the private repository

| Control | State | Where |
| :--- | :--- | :--- |
| CI: `ruff check .` | Active | `.github/workflows/ci.yml` |
| CI: `pytest` on 3.11 and 3.13 | Active | `.github/workflows/ci.yml` |
| CI: refuse tracked files under `data/` | Active | `.github/workflows/ci.yml` |
| Dependency updates (pip, actions) | Active | `.github/dependabot.yml` |

GitHub Actions runs on private repositories under the free plan and injects its
own `GITHUB_TOKEN`; no operator token is required.

## What unlocks when the repository becomes public (or Pro)

Run each command and observe its result before running the next
(`agents.md RA-13`). Substitute nothing — these are the exact commands.

### 1. Require the CI checks on `main`

```bash
gh api -X PUT repos/GstMirabal/WhastApp-Chat-Extractor/branches/main/protection \
  --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["ruff", "pytest (3.11)", "pytest (3.13)", "no exported chats committed"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

The four context names must match the `name:` of each job in
`.github/workflows/ci.yml`. A required check whose name does not match is
treated as never reported, and `ci_gate.py` will wait for it forever.

### 2. Confirm the deployment gate can now read it

```bash
python3 .agents/scripts/ci_gate.py <PR number>
echo "EXIT=$?"
```

Exit `0` is what `deployment_workflow.md` Phase 1 requires before
`gh pr merge --squash`. Read the code with `$?` directly, never through a pipe.

### 3. Secret scanning and push protection

```bash
gh api -X PATCH repos/GstMirabal/WhastApp-Chat-Extractor \
  -f security_and_analysis[secret_scanning][status]=enabled \
  -f security_and_analysis[secret_scanning][push_protection][status]=enabled
```

### 4. Private vulnerability reporting

```bash
gh api -X PUT repos/GstMirabal/WhastApp-Chat-Extractor/private-vulnerability-reporting
```

### 5. Code scanning (CodeQL)

Available on public repositories at no cost; on private ones it needs GitHub
Advanced Security. Enable through **Settings → Code security** once public.

---

## Before making this repository public — read this first

The repository holds no exported conversation: `data/` has been gitignored since
Sprint 003 and the CI job above now proves no file under it is tracked. Two
things still deserve a check by a person, because neither is mechanical:

| To verify | Why |
| :--- | :--- |
| Commit history for stray exports | `git log --all --diff-filter=A --name-only -- data/` returning nothing is the evidence |
| Contact names in documents and commit messages | Sprint 003 and 004 records and early filenames referenced a real contact by name; grep the working tree and the log before publishing |

`agents.md RA-15` requires the same genericization for anything routed to the
`.agents` nucleus, and both open upstream findings under `docs/audits/` were
written to that standard already.

## Still open (not blocked by the plan)

| Gap | Owner | Re-checked |
| :--- | :--- | :--- |
| `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `NOTICE.md` absent at the host root | `/agents:harden` | 2026-09-01 — all four still absent; `LICENSE` is present |
| `ci_gate.py` cannot read `main`'s requirements, so a green CI still does not satisfy the deployment gate | repository owner (make public, or GitHub Pro) | 2026-09-01 — `403` unchanged |

## Controls not applied by this sprint, and why

Sprint 008's D1 ran the platform **probe** only. Every write in *"What unlocks
when the repository becomes public"* above is still unapplied, because each one
either returns `403` on this plan or changes the repository's public posture —
an outward-facing change that belongs to the repository owner, not to a sprint
executing an approved code plan. The probe is read-only by design.
