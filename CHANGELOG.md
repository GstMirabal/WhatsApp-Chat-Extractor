# Changelog

All notable changes to WhatsApp Chat Extractor. This file is the **Master Ledger** (agents.md §0): every Sprint Closeout appends its sprint entry under `[Unreleased]`; every deployment seals that section as `[vX.Y.Z] - date` immediately before tagging.

Format: [Keep a Changelog](https://keepachangelog.com/) · Versioning: [SemVer](https://semver.org/).

> Jurisdiction note: framework changes live in `.agents/CHANGELOG.md`, never here. When the `.agents` pin is updated, this ledger records only the bump (e.g. `chore(deps): pin .agents to v3.1.0 #[Sprint_ID]`).

## [Unreleased]

### Fixed

- **The Global Roadmap was never updated at the Sprint 008 close** (`H-002`). It
  still declared Sprint 008 as `GATED` platform hardening while that sprint was
  closed, merged and released as `v0.8.0`, so a reader planning Sprint 009 from
  it would have concluded the enumeration defect was still open and platform
  hardening was the outstanding work. `RA-05` names four mandatory closeout
  artifacts and the close's gates measure three: the roadmap is
  repository-scoped and carried no freshness stamp, so `docs_freshness_check`
  passed clean over a document six days stale. Now corrected, stamped, and
  carrying a proposed Sprint 009. Routed upstream as `UPSTREAM_FINDING_014`.
  #H002

## [0.8.0] - 2026-09-02

### Fixed

- **The chat-list enumeration no longer loses conversations in silence.** A
  single sweep advances the pane one viewport per pass and dedupes by digest, so
  a list that reorders mid-sweep — one arriving message does it — drops
  conversations below the sweep position and never renders them into any pass.
  Measured against the real geometry (899 conversations, 70-row window, 76px
  rows): **882 of 899** found at one reorder per 5 reads, **856 of 899** at one
  per 2, no duplicates. `sweep_until_stable` repeats the sweep from the head and
  unions by digest until two consecutive sweeps contribute nothing new, and
  recovers **899 of 899 at both rates** in 4 sweeps; a quiet list converges in 3.
  `sweep_chat_list` is unchanged and remains the single-pass primitive, its limit
  still pinned by the test that found it. #008

### Added

- **`ADR-0005`: enumeration completeness is three values, not a boolean.** The
  manifest's `enumeration_complete` was set from whether the pane reached its
  foot — true of the pane, and not the claim its name made: it reported `true`
  for a run that had lost 43 of 899 conversations. Replaced by `enumeration`
  (`converged` \| `unconverged` \| `truncated`) plus a `sweeps` counter, failing
  closed — `converged` requires a positive demonstration of both conditions.
  Deliberately offers no `proven`: unlike `ADR-0004`, no future signal could ever
  make it reachable, and a permanently dead value invites branching on an
  impossible case. #008
- **`scripts/probe_unknown_rows.py`** — operator-run probe capturing the DOM
  signature of every row whose `sender` or `kind` is `unknown` (3.9% and 9.6% in
  the #007 live run). Records which known selectors were tried and missed, plus
  attribute **names**, class tokens and shape — never values, since `aria-label`
  and `data-pre-plain-text` both carry the sender's real name. Two tests assert
  no name and no message body can reach a signature. It classifies nothing:
  `KI-004-A` forbids theorising over this DOM without data. #008

### Changed

- **Manifest schema v1 → v2.** `enumeration_complete` is **removed**, not
  derived. The export file's schema is untouched at v5 — the two version
  independently. #008

### Fixed (framework interaction)

- **The Double-Gate stopped losing its own evidence.** Both Phase 7 gates
  returned a verdict and no findings — the same failure Sprint 007 recorded
  twice and attributed to the result channel. The cause is a deadlock: the
  `SubagentStop` hook runs `check_role_artifact.py --from-hook`, which exits `2`
  unless `SPRINT_LOG.md` already holds that gate's row — a row the gate profiles
  hold no `Write` tool to produce. Exit `2` forces a continuation, and the
  continuation overwrites the report. Roughly 178k subagent tokens came back as
  two lines. Worked around by transcribing both rows before dispatch; routed
  upstream as `UPSTREAM_FINDING_013`. #008
- Gate 2's mutation analysis (18 mutants, 13 killed) found three coverage gaps
  in this sprint's own tests, all now closed: the manifest schema version was
  unpinned, the union's discovery order was untested though `index` is a live
  seek hint, and half the sweep stop condition could be deleted unnoticed. #008

### Known open

- The unknown-row probe has **not been run**: it needs an authenticated WhatsApp
  Web session no agent can start. The instrument ships; the measurement and the
  classification it unblocks belong to Sprint 009. #008
- Five complexity-rule violations in `export_one.py` and `__main__.py`, all
  pre-existing on `main`, surfaced by this sprint's gate-evidence experiment and
  deliberately not fixed — outside the approved scope. Sprint 009. #008
- **CI now executes** (three runs green with real steps on 2026-09-01, after
  five occurrences of the 2-second billing failure), but branch protection and
  rulesets still return `403` on a private free-plan repository, so `ci_gate.py`
  still cannot read what `main` requires. Green checks exist; no rule says they
  are mandatory. #008
- Ten upstream framework findings are drafted under `docs/audits/`; the nucleus
  pull request is a separate act in a separate clone and is not this sprint's.
  #008

## [0.7.0] - 2026-09-01

### Added

- **Sprint 007 (`backend-extractor` / P3b «all chats»)** — `wa-extract export-all`
  enumerates every conversation in the chat list, exports each, and writes a run
  manifest (`data/run_manifest_<stamp>.json`) stating the outcome of every one.
  New modules `chat_list.py` (sweep a virtualized list; reopen a chat by verified
  identity) and `manifest.py` (outcomes, and an opt-in `chat_id` → name index).
  One conversation failing does not end a run; losing the WhatsApp session does.
  A conversation beyond `--limit` is recorded as `skipped`, never omitted. #007
- **`ADR-0004`: completeness is three values, not a boolean.** `completeness` is
  `proven` \| `unproven` \| `truncated`. `classify_completeness` fails closed —
  an unrecognised stop reason is `truncated`, never `proven`. #007
- **`scripts/probe_chat_list.py`** — operator-run probe measuring whether the
  chat list virtualizes and whether a chat's index survives a sweep. #007

### Changed

- **Export schema v4 → v5.** `completeness` is added and required; `complete`
  survives as a boolean **derived** from `completeness == "proven"`, so the two
  cannot disagree and schema-v4 readers keep working. #007
- **`export-one` no longer reports every export as a failure.** It exited `3`
  whenever `complete` was false, and `complete` was never true — so **every
  export ever produced** told the operator the run had failed and advised raising
  a `--max-passes` cap that was not the cause. Only `truncated` exits `3` now. #007
- **`build_parser` and `cmd_export_one` split** to stay inside `agents.md §1`'s
  50-line limit, which this sprint's additions had pushed them past (103 and 58
  lines). No function in the package now exceeds it, measured by AST. #007
- **The chat-list DOM contract lives in one place.** `probe_chat_list.py` imports
  its selectors, title reader and bottom test from `chat_list.py` rather than
  keeping copies: two copies would let the instrument and the product measure
  different DOMs. #007

### Measured

- **The chat list virtualizes**: 899 conversations seen while the DOM never held
  more than 70 rows at once, reproduced across two sweeps 2.5 hours apart, both
  reaching the foot of the pane. A single `query_selector_all` would return 70 of
  910 and report success. #007
- **Position is stable across a sweep** (0 of 69 positions changed) and **no two
  conversations share a title** (0 collisions in 7 100 row observations), so the
  digest identifies a conversation within a run. The sprint's abort criterion
  required both to fail; neither did. #007
- **Identity is not permanent across runs.** Two sweeps counting 899 each shared
  **898**: the digest follows the title, so a renamed conversation becomes a new
  `chat_id` and will not link to its earlier exports. #007
- **A whole-account run is on the order of 15 hours.** Live verification on
  2026-08-31: enumeration of 910 conversations took ~3 minutes, then ~60 seconds
  per conversation, most of it the three 15-second waits confirming the panel had
  stopped producing history. #007
- **Live verification of `export-all --limit 3`**: 3 exported, 0 failed, 907
  skipped of 910 enumerated; 129 messages at schema v5, `completeness: unproven`
  on all three, no title in any payload or in the manifest. #007

### Known open

- **`sender: unknown` on 3.9% of messages** (5 of 129) in the live verification,
  and `kind: unknown` on the same proportion. Sprint 005 measured 0 unknown
  senders over 513 messages in one conversation, so this is either chat-dependent
  or a regression; it is **recorded, not diagnosed**, because the sprint that
  guesses at direction is the sprint `KI-004-A` was written about. Routed to a
  later sprint together with the `unknown_media` classification already queued.
- **The enumerator undercounts silently when the chat list reorders mid-sweep.**
  Measured after the gates, against the real geometry: 882 of 899 conversations
  found at one reorder per 5 reads, 856 at one per 2. No duplicates — the digest
  key prevents that — so the failure is pure loss, and `enumeration_complete`
  still reports `true` because the pane foot was reached. One arriving message
  causes it, and a whole-account run is hours long. Pinned as a test; the fix
  (re-sweep until two consecutive sweeps agree) needs its own measurement. #007
- **Resume is not implemented.** The manifest carries the identity, outcome and
  file of every conversation, which is what a later sprint needs to skip what
  already succeeded. Retries stay out on purpose: retrying without having measured
  why a conversation fails is guessing at how many times to guess.
- **`chore(deps): pin .agents to v4.24.0`** — the framework pin moved during this
  sprint. `UPSTREAM_FINDING_008`, `_010`, `_011` and `_012` are re-verified as
  still open at that tag and still owe their nucleus PRs.

## [0.6.0] - 2026-08-31

> Merged from `ai-sprint/006` as PR #7 under explicit human authorization **without CI verification — the fourth such occurrence**. `ci_gate.py` exited `2` for two independent platform reasons: it could not read what `main` requires (branch protection and rulesets both `forbidden`, the token lacks scope), and all four checks reported failure in 2 seconds each having produced **no logs at all** (`gh run view --log-failed` → `log not found`) — the same GitHub billing signature recorded for PR #5 and PR #6. Verified locally on the exact merged tip `b05e7dc`: 116 passed, 1 skipped, `ruff` clean, no files tracked under `data/`. Unblocking this is `/agents:harden` plus GitHub billing; neither is code.

> Sprint 006 (`ai-sprint/006`) closes **partially by design**. The Approval Gate
> authorized W1–W2 only, so that `ADR-0004` would be written against the probe's
> measurement rather than alongside it; W4a was a later, narrow unlock for the
> stall rule. W3 (the ADR) and W4–W8 remain unstarted and gate-locked. The
> sprint's question is answered, which is what it existed for. #006

### Added
- `scripts/probe_chat_start.py` — an operator-run DOM probe that answers whether WhatsApp Web draws a start-of-conversation marker, instead of assuming it. Records structural attributes from a fixed allowlist, never `innerText`, and excludes `data-pre-plain-text` because it carries the sender's name (`ADR-0003`). Chats appear under the exporter's pseudonymous digest, so the evidence names no one. #006
- `--from-list N` walks the chat list by index rather than searching. Searching produced every dead end of the first two runs; walking the list removes the whole class, and matches where the product is heading — exporting every chat rather than named ones. #006
- `chrome_attribute_inventory` — a budget-free tally of every `data-icon`, `data-testid` and `role` in the panel's chrome. `top_chrome_signatures` samples in document order and a marker nested ~30 wrappers deep falls outside its limit; that miss is silent and reads exactly like an absent marker. Found before any real chat was touched, by exercising the probe against a real Chromium. #006
- `tests/test_probe_chat_start.py` — 28 tests over the probe's contract. One needs a browser (the defect it pins lives in JavaScript) and skips when Chromium cannot launch, so the fast suite stays fast. #006
- `docs/sprints/006-backend-extractor/DOM_PROBE_NOTES.md` — four runs of measured evidence, including what was **not** established. #006

### Fixed
- `history.decide_stop` called a still-fetching panel a stall. Probe run 3 caught it live: one conversation was declared `stalled` after 175 passes with a `loading-spinner` still in the panel chrome — the harvest gave up mid-fetch and reported a top it had never reached, the same class of error as the 217-message "complete" export this module already documents. `panel_loading` now suppresses the stall verdict only; `max_passes` still guarantees termination and reports itself honestly, and a reached start still wins over both. Run 4 confirmed the fix acts: that chat ran 255 passes and ended with the panel quiet. #006

### Measured
- **`complete: true` is unreachable.** Across five real conversations and two runs, with the stall defect corrected, `COMPLETE_REASONS` never fired once and no start marker appeared in any panel — `data-icon` empty in every chrome inventory taken. Three of the five reproduce their pass and row counts exactly between runs, so these are stable tops rather than abandonments, and the plan's abort criterion (a marker whose presence flickers) does not apply. **Not claimed**: no harvest reached a *provable* beginning, so "the marker does not exist" remains an inference. What is established is enough for `ADR-0004` — a field that is constant cannot distinguish a complete history from a truncated one. #006
- Unknown media is **30 of 311 rows (9.6%)**, well above the 6 of 301 Sprint 005 measured; that sample understated the rate. Signatures captured for Sprint 007. #006
- No search-result selector matches anything outside `#pane-side` (0 leaks, five chats), which is the question `search_selector_scope` was deferred on. Separately, both `role="listitem"` candidates match **nothing** in this build, so `_open_first_result` silently falls through its first choice. #006

### Known defects, deliberately not fixed
- `export_one._open_first_result` clicks `.first` of the earliest candidate with any match. `#pane-side div[role="listitem"]` matches 0, so it falls through to `#pane-side div[role="row"]` (59) and clicks a wrapper that accepts the click and opens nothing, raising no error — the operator had been opening chats by hand without registering that they were covering for it. The fix is now **measured** rather than theorised: `[data-testid="cell-frame-container"]` opened every chat it was tried on. Candidate hotfix H-002; loses most of its urgency if the product stops searching by name. #006

## [0.5.1] - 2026-08-30

> Hotfix release (RA-03), outside the sprint cycle. Merged from `hotfix/H-001` as PR #6 under explicit human authorization **without CI verification — the third such occurrence**. The four checks reported red having produced no logs at all in 2-4 seconds, the same GitHub billing signature recorded for PR #5; the code was verified locally and again on the integrated `main` tip (88 passed, `ruff` clean). Record: `docs/hotfixes/H-001-backend.md`.

### Fixed
- `open_chat_by_query` opened no chat and still reported success, so an export could be written for **whichever conversation was already on screen** and exit `0`. Since `chat_id` is a digest and the title is never stored, the output file carried no evidence of its origin — a corpus attributed to the wrong person. Every post-condition was satisfiable by the page state that already held: the panel wait was already satisfied, the result click matched the ordinary chat list, and the title was read but never compared. The opened conversation is now matched against the query and the run aborts on mismatch or on an unreadable title. Fail-closed is deliberate: an avoidable failed run is cheaper than a mislabelled corpus. HIGH, inherited from Sprint 003. #H001
- `read_open_chat_title(page) or query` fabricated agreement between what was asked for and what was opened, which is why the defect above could not surface. The fallback is removed. #H001

### Added
- `_normalize_title` / `_title_matches_query` in `export_one.py` — accent- and case-insensitive containment, because the operator types a fragment rather than the full name. #H001
- `tests/test_open_chat_verification.py` — 10 tests pinning the silent wrong-chat failure, proved to fail against the defective source before the fix landed. The suite goes from 78 to 88. #H001
- `docs/hotfixes/H-001-backend.md` — hotfix record, written before the first substantive commit (RA-03). #H001

## [0.5.0] - 2026-08-30

> The first three `Added` entries and the last two `Changed` entries were reconstructed on 2026-08-30 by `/agents:reconcile` from the commit range `ac806f5..c090646` and its diffs, after `detect_drift.py` returned verdict `U`. No product code changed in that range; it was documentation and planning only. Everything else is Sprint 005 execution.

### Added
- `docs/decisions/ADR-0003-media-placeholders-in-export.md` — media messages become placeholder records carrying a `kind` instead of being skipped. Supersedes the *Coverage* row of ADR-0001 §2. No media byte is stored. #005
- `docs/sprints/005-backend-extractor/IMPLEMENTATION_PLAN.md` — Sprint 005 plan, approved at the Phase 5 gate on 2026-08-30. #005
- `docs/sprints/005-backend-extractor/RESUME_NOTES.md` — session-close state that cannot be recovered by reading the code. #005
- Export schema v4: every message carries a mandatory `kind` of `text`, `image`, `voice` or `unknown`, and a message with no text is recorded instead of discarded (ADR-0003). Under v3 a photo or a voice note left no trace, so the conversation read as question → next question and taught an adjacency that never happened. No media file is downloaded or referenced. #005
- `export_one._row_kind` and `export_one._row_emoji_body`, plus the `VOICE_SELECTOR` / `IMAGE_SELECTOR` / `EMOJI_IMG_SELECTOR` constants. Every selector was observed on a live row by the W2 DOM probe of 2026-08-30, never inferred (`KI-004-A`). #005
- `.cursor/commands/wa-export.md` — the Cursor entry point ADR-0001 declares. Sprint 004 shipped only the Claude Code command. It is a host-authored file rather than a symlink, because `install.sh` overwrites the framework's own files under `.cursor/commands/`. #005
- `README.md` — the file `pyproject.toml:9` has declared since Sprint 003 with nothing behind it, so a package build failed. Covers requirements, `login` → `export-one`, how to read `complete`, the schema, and the four privacy constraints. #005
- `LICENSE` — proprietary terms backing the `Proprietary` string in `pyproject.toml:11`, which named a licence that did not exist. It also states that the licence governs the software only and confers no right over any conversation the software exports. #005
- 16 tests covering `kind` classification, emoji-body recovery, schema v4 and media survival through the accumulator; the suite goes from 62 to 78. #005

### Fixed
- Emoji-only messages were dropped entirely. WhatsApp draws each emoji as `<img alt="…">` inside a `div[data-testid="selectable-text"]`, which the `span.selectable-text` matcher never saw, so `inner_text()` returned nothing and the row read as bodiless. The first live v4 export recovered 23 such messages out of 301 — a larger loss than the media ADR-0003 was written for. #005
- `message_count` counted text messages while presenting itself as a message count, because rows with no text were discarded before being counted. #005
- Two captionless media messages from one speaker in the same minute hashed to one identity and the second was dropped as a duplicate. `_row_id` now falls back to the `conv-msg-<HEX>` wrapper before the hashed key, and `kind` joins that key. The hash alone still cannot separate two rows of the *same* kind, which is asserted in a test rather than left as an assumption. #005
- `.gitignore` excluded `/.cursor/commands/` wholesale, which would have made the host-authored Cursor command untrackable — the same defect fixed for `/.claude/commands/` in Sprint 004, and the reason git never consults a negation inside an excluded directory. #005

### Changed
- `docs/architecture/EXTRACTOR_BLUEPRINT.md` — schema v4, the kind contract with its four DOM signals, the revised identity ladder, and the stated timestamp limitation. #005
- `docs/roadmaps/docs/extractor/002-delivery-program.md` — the single `P3 harden` row becomes four sprints: P2.5 (005, corpus fidelity + operator surface), P3a (006, one chat proven complete), P3b (007, all chats), P4 (008, platform hardening, `GATED`). Sprint 005 exists because Sprint 004's scope review found four declared items never built: the Cursor entry point ADR-0001 names, the `README.md` and `LICENSE` that `pyproject.toml` declares, and platform hardening. #005
- `docs/0_SYSTEM_OVERVIEW.md` — records ADR-0003, the released `v0.4.0` state and the Sprint 005 resume pointer; the artifact table adds ADR-0003, `.github/workflows/ci.yml` and `docs/PLATFORM_HARDENING.md`. #005

## [0.4.0] - 2026-08-30

### Added
- Full-history harvest: `history.harvest_history` reads the message panel on every scroll pass and merges by message id, replacing the single DOM read that lost the recent end of the conversation to WhatsApp Web row virtualization. #004
- Export schema v3 with `schema_version`, `message_count`, `complete` and `stopped_reason`, so a corpus states whether it holds the whole chat. #004
- Pseudonymous chat identity: `chat_id` is a digest of the chat title, the title is not stored, and the filename carries the digest — no contact name reaches disk. #004
- `tests/test_row_fields.py` — sender/timestamp extraction and load-control matching against stub rows, the coverage whose absence let the #003 defect ship. #004
- Automatic clicking of the "load older messages" control, identified by text across `button` and `[role=button]`; the operator previously had to press it once per batch. #004
- Message direction resolved from three DOM signals in order — bubble tail, `aria-label`, `data-pre-plain-text` — each covering what the previous misses. #004
- `/wa-export <chat>` slash command over `wa-extract export-one`. #004
- `tests/test_history.py` — merge, ordering and termination rules against synthetic pass sequences (no live WhatsApp). #004

### Changed
- `wa-extract export-one` replaces `--scroll-passes` with `--max-passes` and `--stall-threshold`, drops `--chat-id`, and exits `3` when the harvest stops without proving it reached the start. #004
- `export_one` reduced to single-pass primitives (`scroll_one_pass`, `collect_visible_rows`, `at_chat_start`); the iteration moved to `history`. #004
- Ruff configuration moved from `pyproject.toml` to `.ruff.toml` and scoped to the host tree, excluding the `.agents` submodule. #004
- Full chat history brought forward from P3 to P2: a dump truncated by a scroll count does not serve its stated consumer. #004

### Fixed
- `.gitignore` excluded `/.claude/commands/` wholesale, which made host-authored commands untrackable; it now excludes the directory's contents and re-includes `wa-export.md`. #004
- `sender` carried the clock instead of the speaker (214 of 217 messages in the first live export) because `data-pre-plain-text` was read off the row rather than its descendant; `timestamp` carried message body for the same reason. Both inherited from #003. #004
- A stalled harvest was recorded as `complete: true`, producing a 217-message export of a longer conversation marked complete. Only a start-of-chat marker proves completeness now. #004
- The scroll waited a fixed 400 ms, ending the first live harvest after 1.2 seconds; it now clicks any load-earlier control and polls the panel signature until it changes. #004
- The load-control matcher was scoped to `#main a` and `#main [tabindex]` with a bare `haz clic aquí` alternative, so it clicked links inside the conversation during a live run. Candidates are panel chrome only, nodes inside message bubbles are rejected outright, and every pattern alternative requires the noun `mensajes`/`messages`. #004
- Every sender in a 513-message live export was `unknown`: current WhatsApp Web builds carry no `.message-in`/`.message-out`, and `data-id` is bare hex rather than `true_`/`false_` prefixed. Direction now comes from probed signals. #004

## [0.3.0] - 2026-08-27

### Added
- Python package `src/whatsapp_chat_extractor/` with Playwright session, one-chat export, and `wa-extract` CLI (`login`, `export-one`). #003
- Offline pytest for JSON writers and chat-search locator fallbacks (no live WhatsApp in CI). #003
- `docs/architecture/EXTRACTOR_BLUEPRINT.md` and `docs/walkthroughs/EXTRACTOR_WALKTHROUGH.md`. #003
- Spike notes with live proof: one chat → gitignored JSON (84 messages) on operator Mac. #003

### Changed
- Chat search hardened (ES/EN placeholders + icon + CSS fallbacks) after live selector miss. #003
- `.agents` pin bumped to v4.23.0. #003
- Program roadmap P1 marked CLOSED. #003

### Fixed
- Duplicate Claude/Cursor `PreToolUse` `on_commit` hook (non-JSON stdout) that blocked agent commits after bridge re-merge. #003

## [0.2.0] - 2026-08-27

### Added
- Product scope ADR-0001: WhatsApp Web export (one business number, full text history) to gitignored `data/` JSON; Cursor agent + scripts; analysis/bot out of repo. #002
- Delivery program ADR-0002: phases P0→P3 (document → spike → happy path → harden) and host layout (`src/whatsapp_chat_extractor/`, `data/`). #002
- Project roadmap `docs/roadmaps/docs/extractor/002-delivery-program.md`. #002

### Changed
- System Overview Level 1–2 aligned to ADR-0001/0002. #002
- `.gitignore` ignores `/data/` (customer chat exports). #002

## [0.1.0] - 2026-08-27

### Added
- Adopted Token-Optimized Agent Pipeline governance (v4.22.0) — onboarding scenario: A Greenfield. #001
- Host documentation topology (`docs/`), System Overview, identity config, and sprint 001 closeout artifacts. #001
