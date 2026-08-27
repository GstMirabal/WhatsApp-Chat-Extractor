# Blueprint: EXTRACTOR
**File**: `docs/architecture/EXTRACTOR_BLUEPRINT.md`
**Status**: `RATIFIED`
**Sprint of origin**: #003
**Last Audit Sprint**: #003
**Last Audit Date**: 2026-08-27
**Last Audit Commit SHA**: *(filled at close)*

---

arc42-lite (`rules/documentation_standard.md §5`) — Reference only.

## 1. Introduction & Goals

Python package that opens WhatsApp Web via Playwright, lets the operator
complete QR login once (persistent Chromium profile), opens **one**
human-selected chat, and writes a text-only JSON export under gitignored
`data/`.

## 2. Context & Scope

| Aspect | Value |
| :--- | :--- |
| **Upstream dependencies** | Playwright Chromium; WhatsApp Web UI; operator Mac + phone for QR |
| **Downstream consumers** | External AI / learning pipelines reading `data/*.json` (out of repo) |

## 3. Building Block View

| Aspect | Value |
| :--- | :--- |
| **Owns** | `src/whatsapp_chat_extractor/`, `tests/`, `pyproject.toml`, writes under `data/` |
| **Must not touch** | Sentiment/bot code; Cursor dump skill (P2); `.agents/` internals |

| Interface | Type | Defined in |
| :--- | :--- | :--- |
| `wa-extract login` | CLI | `src/whatsapp_chat_extractor/__main__.py` |
| `wa-extract export-one` | CLI | `src/whatsapp_chat_extractor/__main__.py` |
| `ChatExport` JSON | file schema | `writers.ChatExport` / this blueprint §3 |

Data model:
- **ChatExport**: `chat_id`, `title`, `exported_at`, `messages[]`
- **MessageRecord**: `sender`, `timestamp`, `body`, `order` (text only)

## 4. Runtime View

1. Operator runs `wa-extract login` → Chromium persistent profile → QR if needed → chat list ready.
2. Operator runs `wa-extract export-one --query "…"` → search → open chat → scroll passes → collect DOM text → write `data/*.json`.
3. Pytest exercises `writers` with fixtures only (no live WhatsApp).

## 5. Crosscutting Concepts

- Selectors centralized in `session.py` / `export_one.py`; changes logged in `SPIKE_NOTES.md`.
- Customer data and browser profile stay under `data/` (gitignored).
- Logging via stdlib `logging`; no secrets in logs.

## 6. Non-negotiable Constraints

| Constraint | Verification |
| :--- | :--- |
| No live WhatsApp in CI | `python -m pytest tests/ -q` uses fixtures only |
| Exports never committed | `rg -n '^/data/' .gitignore` |
| Text-only messages | Schema has no media fields |
| Submodule purity | `git -C .agents status --porcelain` empty at close |

## 7. Decisions

- `docs/decisions/ADR-0001-product-scope-whatsapp-web.md`: Web + text JSON + Cursor/scripts split
- `docs/decisions/ADR-0002-delivery-program-and-layout.md`: P1 spike layout + exit criterion

## 8. Glossary

| Term | Meaning in this module |
| :--- | :--- |
| Persistent profile | Chromium `user_data_dir` under `data/browser_profile` reused after QR |
| Spike export | Visible DOM messages after limited scroll — not guaranteed full history |
