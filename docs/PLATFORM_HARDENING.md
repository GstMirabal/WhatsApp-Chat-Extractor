# Platform Hardening — pending controls

**Status**: CI landed 2026-08-30 (Sprint 004). Branch protection **blocked**.
**Blocker**: the repository is private on a free plan, where GitHub does not
offer branch protection or rulesets:

```
GET /repos/GstMirabal/WhastApp-Chat-Extractor/branches/main/protection
{"message":"Upgrade to GitHub Pro or make this repository public
            to enable this feature.","status":"403"}
```

This is a plan limitation, not a token scope problem — the operator's token
carries `repo` and `workflow`.

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

| Gap | Owner |
| :--- | :--- |
| `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `NOTICE` absent at the host root | `/agents:harden` |
