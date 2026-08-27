# Spike Notes — Sprint 003 (P1)

**Branch**: `ai-sprint/003`  
**Purpose**: Evidence log for WhatsApp Web → one chat → JSON. Update this file
after every live attempt (success or failure). Abort after ≤2 documented
failed attempts per Implementation Plan.

---

## Operator commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
wa-extract login --keep-open
wa-extract export-one --query "CONTACT_OR_TITLE"
```

Profile path: `data/browser_profile/` (gitignored via `/data/`).  
Output path: `data/<slug>_<UTC>.json`.

---

## Attempt log

| # | Date (UTC) | Command | Result | Notes |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 2026-08-27 | `wa-extract export-one` (pre-fix) | FAIL | `Chat search box not found` — old selectors |
| 2 | 2026-08-27T15:24:44Z | `wa-extract export-one --query …` | **OK** | `data/Rocio_Luca_de_Tena_20260827T152444Z.json` — **84 messages**; search fix (icon + ES/EN placeholders) |

---

## Selectors in force

| Role | Module constants | Notes |
| :--- | :--- | :--- |
| QR | `session.QR_SELECTORS` | Fragile; WA may rotate `data-testid` |
| Ready / chat list | `session.READY_SELECTORS` | |
| Search icon | `export_one.SEARCH_ICON_SELECTORS` | Clicked first when the box is collapsed |
| Search box | placeholders ES/EN + `CHAT_SEARCH_SELECTORS` | 2026-08-27: old `chat-list-search` alone failed on operator Mac |
| Search results | `SEARCH_RESULT_SELECTORS` | Click first hit before falling back to Enter |
| Message panel / rows | `MESSAGE_PANEL_*` / `MESSAGE_ROW_*` | Scroll is limited (`--scroll-passes`) |

When a selector breaks, patch the constant and add a row here with the old/new
value — do not silently invent selectors mid-run without a note.

### Attempt note — search box (2026-08-27)

Operator hit: `Chat search box not found; update CHAT_SEARCH_SELECTORS`.
Fix: open search icon → placeholder/role (ES+EN) → CSS fallbacks; type via
keyboard (contenteditable); click first result.


---

## ToS / account risk

Automating WhatsApp Web may violate WhatsApp Terms of Service and can risk the
business number. Operator acceptance was part of ADR-0001 and the Sprint 003
Approval Gate. Stop immediately if Meta challenges the session or Gustavo
halts the spike.

---

## Abort criterion (reminder)

If two documented attempts cannot complete QR → one chat → JSON file, stop
product investment, leave evidence in this file, and do not open P2 until a
superseding ADR or plan B.
