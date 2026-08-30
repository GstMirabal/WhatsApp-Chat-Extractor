# Changelog

All notable changes to WhatsApp Chat Extractor. This file is the **Master Ledger** (agents.md §0): every Sprint Closeout appends its sprint entry under `[Unreleased]`; every deployment seals that section as `[vX.Y.Z] - date` immediately before tagging.

Format: [Keep a Changelog](https://keepachangelog.com/) · Versioning: [SemVer](https://semver.org/).

> Jurisdiction note: framework changes live in `.agents/CHANGELOG.md`, never here. When the `.agents` pin is updated, this ledger records only the bump (e.g. `chore(deps): pin .agents to v3.1.0 #[Sprint_ID]`).

## [Unreleased]

> Entries below were reconstructed on 2026-08-30 by `/agents:reconcile` from the commit range `ac806f5..c090646` and its diffs, after `detect_drift.py` returned verdict `U`. No product code changed in that range; it is documentation and planning only.

### Added
- `docs/decisions/ADR-0003-media-placeholders-in-export.md` — media messages become placeholder records carrying a `kind` instead of being skipped. Supersedes the *Coverage* row of ADR-0001 §2. No media byte is stored. #005
- `docs/sprints/005-backend-extractor/IMPLEMENTATION_PLAN.md` — Sprint 005 plan, status `DRAFT`, not approved. #005
- `docs/sprints/005-backend-extractor/RESUME_NOTES.md` — session-close state that cannot be recovered by reading the code. #005

### Changed
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
