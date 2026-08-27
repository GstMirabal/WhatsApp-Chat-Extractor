# Changelog

All notable changes to WhatsApp Chat Extractor. This file is the **Master Ledger** (agents.md §0): every Sprint Closeout appends its sprint entry under `[Unreleased]`; every deployment seals that section as `[vX.Y.Z] - date` immediately before tagging.

Format: [Keep a Changelog](https://keepachangelog.com/) · Versioning: [SemVer](https://semver.org/).

> Jurisdiction note: framework changes live in `.agents/CHANGELOG.md`, never here. When the `.agents` pin is updated, this ledger records only the bump (e.g. `chore(deps): pin .agents to v3.1.0 #[Sprint_ID]`).

## [Unreleased]

### Added

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
