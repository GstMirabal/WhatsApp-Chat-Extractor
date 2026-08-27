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
| 1 | *(pending)* | | | Live QR → export not run in CI; operator fills after first Mac run |

---

## Selectors in force

| Role | Module constants | Notes |
| :--- | :--- | :--- |
| QR | `session.QR_SELECTORS` | Fragile; WA may rotate `data-testid` |
| Ready / chat list | `session.READY_SELECTORS` | |
| Search | `export_one.CHAT_SEARCH_SELECTORS` | |
| Message panel / rows | `MESSAGE_PANEL_*` / `MESSAGE_ROW_*` | Scroll is limited (`--scroll-passes`) |

When a selector breaks, patch the constant and add a row here with the old/new
value — do not silently invent selectors mid-run without a note.

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
