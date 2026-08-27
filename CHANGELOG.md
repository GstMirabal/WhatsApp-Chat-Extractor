# Changelog

All notable changes to WhatsApp Chat Extractor. This file is the **Master Ledger** (agents.md §0): every Sprint Closeout appends its sprint entry under `[Unreleased]`; every deployment seals that section as `[vX.Y.Z] - date` immediately before tagging.

Format: [Keep a Changelog](https://keepachangelog.com/) · Versioning: [SemVer](https://semver.org/).

> Jurisdiction note: framework changes live in `.agents/CHANGELOG.md`, never here. When the `.agents` pin is updated, this ledger records only the bump (e.g. `chore(deps): pin .agents to v3.1.0 #[Sprint_ID]`).

## [Unreleased]

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
