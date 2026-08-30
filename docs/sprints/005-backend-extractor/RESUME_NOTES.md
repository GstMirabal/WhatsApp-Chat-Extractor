# Resume Notes — Sprint 005 (`backend-extractor` / P2.5)

Written 2026-08-30 at session close, for whoever opens this next — including the
same operator months later. Everything here is state you cannot recover by
reading the code.

## Where the work stands

| Item | State |
| :--- | :--- |
| Branch | `ai-sprint/005`, created off `main` at `ac806f5` (v0.4.0) |
| Plan | `IMPLEMENTATION_PLAN.md` in this directory, **`DRAFT`** — never approved |
| Done | W0 (ADR-0003), W1 (roadmap restructure) |
| Not started | W2–W12 |
| Anchor | `docs/active_state.json`, `status: SUSPENDED`, sprint 005 open |

`SUSPENDED` is deliberate and is what tells `/agents:start` to resume rather
than plan. It also makes `/agents:deployment` refuse, which is correct: nothing
here is releasable.

## Start here

1. `/agents:start` — it will see `SUSPENDED` and read this file.
2. Read `IMPLEMENTATION_PLAN.md` and decide the Approval Gate. It is `DRAFT`;
   Sprint 005 cannot execute until a human approves it.
3. First real task is **W2, the probe** — not W3. See below.

## The one thing that must not be skipped

**Probe the DOM before writing any selector.** Sprint 004 shipped three
successive theories about how WhatsApp marks message direction and all three
were wrong; the third produced a 513-message export in which every sender was
`unknown`. What finally worked came from dumping the live attribute chain.

`kind` detection is the same class of problem. The scratchpad probes from
Sprint 004 are gone (session-local), so W2 rewrites one. It must:

- open the chat and select rows **with no selectable text**
- print `data-testid`, `aria-label`, `data-icon` and the ancestor chain
- print **no message bodies** — the redaction pattern used before replaced
  everything after `]` in `data-pre-plain-text` with `<redacted>`

Starting points already observed, which are evidence but not conclusions:

| Signal | Seen on |
| :--- | :--- |
| `data-testid: image-thumb`, aria `Abrir foto` | An image |
| `data-testid: ptt-status`, aria `Mensaje de voz` | A voice note |

## Environment facts that cost time to rediscover

| Fact | Consequence |
| :--- | :--- |
| Live browser runs fail inside the agent sandbox | Chromium cannot create its `ProcessSingleton` socket. Run them outside it (`KI-004-E`) |
| `$TMPDIR` differs inside and outside the sandbox | Redirected output written outside is not where a sandboxed read looks |
| The commit gate reads the index **before** the command runs | `git add` in one call, `git commit` in the next (`KI-003-B`) |
| A `fix(` commit must stage its regression test | Same commit, or the gate refuses |
| Adding a `[tool.*]` key to `pyproject.toml` trips the dependency gate | It reads any `key = value` as a package — `UPSTREAM_FINDING_005` |
| `python3 .agents/scripts/session_start.py --boot` claims the **nucleus** anchor | Run the binding steps individually from the host root — `UPSTREAM_FINDING_004` |

## Open risk inherited from Sprint 004

`complete: true` **has never been produced.** Every live run was capped at 6–12
passes, so no run reached a chat start and `CHAT_START_SELECTORS` is unproven
against a real beginning of conversation. That is Sprint 006's subject, not
this one, but do not read a capped `complete: false` here as a new defect.

## Verified facts about the export, as of v0.4.0

Measured 2026-08-30 against a live chat, so they are a baseline to compare
against rather than claims to re-verify:

| Metric | Value |
| :--- | :--- |
| Longest run | 513 messages in 12 passes, history still above |
| Direction | 135 `contact` / 119 `me` / **0 `unknown`** over 254 messages |
| Duplicates | 0 |
| Timestamps parsed | 254 / 254 |
| Name in payload or filename | None |

## Deployment state

`v0.4.0` is merged, tagged and released. It was **merged without CI
verification** under explicit authorization: Actions jobs cannot start on this
private repository (billing) and branch protection needs a public repo or Pro.
Recorded in `docs/PLATFORM_HARDENING.md`. CI is configured and will run the
moment either blocker clears.
