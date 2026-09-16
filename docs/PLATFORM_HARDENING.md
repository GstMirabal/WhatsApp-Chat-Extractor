# Platform Hardening — pending controls

**Status**: CI landed 2026-08-30 (Sprint 004) and **executes since 2026-09-01**
(Sprint 008 — evidence below). Branch protection still **blocked**.
**Blocker**: the repository is private on a free plan, where GitHub does not
offer branch protection or rulesets:

```
GET /repos/GstMirabal/WhatsApp-Chat-Extractor/branches/main/protection
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
[`#9`](https://github.com/GstMirabal/WhatsApp-Chat-Extractor/pull/9) (Sprint
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

## Applied — Sprint 012, 2026-09-16

The repository is now **public**. Every control below is active, applied in
this order, each observed as a separate step before the next
(`agents.md RA-13`):

| # | Control | State | Evidence |
| :--- | :--- | :--- | :--- |
| — | Repository renamed | Done | `WhastApp-Chat-Extractor` → `WhatsApp-Chat-Extractor`, typo fixed before publishing |
| — | 2 stale Dependabot PRs (`actions/checkout`, `actions/setup-python`) | Merged | Rebased twice (the second PR needed a second rebase after the first's merge touched the same file), fresh CI green on both, squash-merged |
| — | Visibility | **Public** | `gh repo view --json visibility` → `PUBLIC` |
| 1 | Branch protection, 4 required checks on `main` | Active | `gh api repos/GstMirabal/WhatsApp-Chat-Extractor/branches/main/protection` returns the 4 contexts below, no `403` |
| 2 | Deployment gate reads the requirement | Confirmed | `ci_gate.py`'s `403`-driven `RECORD` path is no longer the only outcome — branch protection is now readable, ending the run of 5 releases (`v0.4.0`–`v0.8.0`) merged under human authorization past an unreadable gate |
| 3 | Secret scanning + push protection | Active | `security_and_analysis`: `secret_scanning.status=enabled`, `secret_scanning_push_protection.status=enabled` |
| 4 | Private vulnerability reporting | Active | `gh api -X PUT .../private-vulnerability-reporting` → `204` |
| 5 | Code scanning (CodeQL) | Active | `gh api -X PATCH .../code-scanning/default-setup -f state=configured -f query_suite=default` — this document previously claimed this needs a `Settings → Code security` UI action; it does not, the API endpoint above configures it |

**Command #3's field name in this document was wrong and would have
silently under-applied**: `-f security_and_analysis[secret_scanning][push_protection][status]=enabled`
sets nothing GitHub reads — the real field is a sibling, not nested:
`security_and_analysis[secret_scanning_push_protection][status]`. Found by
running the documented command literally and inspecting the response;
corrected in the exact commands below rather than left for the next
publish attempt to rediscover.

### Exact commands run

```bash
gh repo rename WhatsApp-Chat-Extractor
git remote set-url origin https://github.com/GstMirabal/WhatsApp-Chat-Extractor.git
gh repo edit --visibility public --accept-visibility-change-consequences

gh api -X PUT repos/GstMirabal/WhatsApp-Chat-Extractor/branches/main/protection \
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

python3 .agents/scripts/ci_gate.py <PR number>   # separate invocation, observe $? before merging

gh api -X PATCH repos/GstMirabal/WhatsApp-Chat-Extractor \
  -f 'security_and_analysis[secret_scanning][status]=enabled'
gh api -X PATCH repos/GstMirabal/WhatsApp-Chat-Extractor \
  -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'

gh api -X PUT repos/GstMirabal/WhatsApp-Chat-Extractor/private-vulnerability-reporting

gh api -X PATCH repos/GstMirabal/WhatsApp-Chat-Extractor/code-scanning/default-setup \
  -f state=configured -f query_suite=default
```

The four required-check context names must match the `name:` of each job in
`.github/workflows/ci.yml`. A required check whose name does not match is
treated as never reported, and `ci_gate.py` will wait for it forever.

---

## Verified before publishing

The repository holds no exported conversation: `data/` has been gitignored
since Sprint 003, and the CI job proves no file under it is tracked, checked
again immediately before flipping visibility:

| Verified | Result |
| :--- | :--- |
| Commit history for stray exports | `git log --all --diff-filter=A --name-only -- data/` — empty, confirmed twice (Sprint 012 planning and again immediately before publishing) |
| Contact names in documents and commit messages | Targeted greps for a filled-in real name in early sprint docs and query examples found nothing; per this row's own long-standing caveat, this is a check a person should also make, since only a human knows which name to look for |

`agents.md RA-15` requires the same genericization for anything routed to the
`.agents` nucleus, and every upstream finding under `docs/audits/` was
written to that standard already.

## Still open

| Gap | Owner |
| :--- | :--- |
| `test_strength_gaps` F-6 (enumeration is an unvalidated `str`) | Future sprint, carried since Sprint 010 |

## Deployment attempt — Sprint 008, PR #9 (2026-09-02)

`deployment_workflow.md` Phase 1 `pr_flow` ran and **stopped**. `RA-13` requires
`ci_gate.py` to be observed at exit `0` before `gh pr merge --squash` is issued:

```
$ python3 .agents/scripts/ci_gate.py 9
CI_GATE_EXIT=2
❌ What `main` requires could not be determined … branch protection: forbidden; rulesets: forbidden
```

**The distinction that matters, and that the four earlier deviations did not
have**: the checks are green. Run `33598297247` on the sealed tip `df61678`
passed all four with real steps — `pytest (3.11)` 19 s, `pytest (3.13)` 23 s,
`ruff` 10 s, `no exported chats committed` 5 s.

| | Releases `v0.4.0` – `v0.7.0` | PR `#9` |
| :--- | :--- | :--- |
| Checks reported | failure in 2–5 s | **pass** in 5–23 s |
| Steps executed | **zero** | 5–8 per job |
| Independent verification | none | **full** |
| `ci_gate.py` | exit `2` | exit `2` |

The gate refuses for a different reason now. Before, there was nothing to
verify; now the verification exists and no *rule* declares it mandatory, so the
gate cannot read a requirement to confirm. Merging would be the fifth
authorization past this gate and the first with real evidence behind it — a
different decision from the previous four, and still the repository owner's.

## Deviation on record — v0.8.0 merged without a readable gate (fifth occurrence)

Sprint 008, PR `#9`, squash-merged `a2413bb` on 2026-09-02 under explicit
authorization from the repository owner, after `ci_gate.py 9` exited `2` for the
fifth consecutive release.

**This deviation is not the same as the previous four, and the difference is the
whole reason this entry exists.** Those four shipped with *no* independent
verification: the checks reported failure in 2–5 seconds having executed zero
steps, so the gate's refusal and the absence of evidence were the same fact.
Here the evidence exists:

| Signal | `v0.4.0`–`v0.7.0` | `v0.8.0` |
| :--- | :--- | :--- |
| Checks on the merged tip | failure, 2–5 s | **pass**, 5–23 s |
| Steps executed | zero | 5–8 per job |
| Run | — | `33598297247` on `df61678` |
| `ci_gate.py` | exit `2` | exit `2` |
| Reason for the refusal | nothing had run | no rule declares the checks required |

`ci_gate.py` treats *"a branch declaring no required check"* as a failure by
design, because an unprotected repository is not a verified one. That judgement
is correct and is not being argued with: what was merged is a tip whose four
checks genuinely passed, on a base branch that cannot express a requirement.

Post-merge verification on the integrated `main` tip `a2413bb`: `ruff check .`
exit `0`, **225 passed**.

The exception is removed, not repeated, by making the repository public or
moving to GitHub Pro and then applying the branch protection in *"What unlocks
when the repository becomes public"* above. Until then every release here still
carries the owner's authorization rather than a gate's.
