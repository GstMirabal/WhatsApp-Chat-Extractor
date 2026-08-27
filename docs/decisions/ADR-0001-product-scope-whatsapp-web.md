# ADR-0001: Product scope and WhatsApp Web extraction
**Status**: `Accepted`
**Date**: 2026-08-27
**Triggers**: 2, 3, 4 (`rules/documentation_standard.md §3.1`)

---

## 1. Context

WhatsApp Chat Extractor exists so a business can dump the text history of
customer-support chats into a file that a **later** AI pipeline can use to study
requests, behaviours, and sentiment for a customer-care bot.

Sprint 001 left product shape open and recommended a Python CLI while rejecting
WhatsApp Web scraping as the primary path. In Sprint 002 the human clarified the
real product in chat. Those decisions replace the provisional #001 direction for
this repository's scope.

Facts from that debate:

- Success for **this app** = produce the export file, nothing more.
- Chats are **business staff ↔ customers**, on **one** WhatsApp number.
- Downstream analysis (sentiment, solicitudes, learning server, bot) is **out of
  this repository**.
- The operator runs exports **manually on a Mac**, when they want a dump.
- Output lives in a **folder inside this repo** that is **gitignored** (customer
  data must not be pushed).

## 2. Decision

| Topic | Decision |
| :--- | :--- |
| Product boundary | This repo **only** creates the export JSON. No sentiment, no bot, no learning server. |
| Source | **WhatsApp Web** (single business number). WhatsApp Business API is rejected for this goal (it does not dump stored history). |
| Coverage | **Full history**, **text only** (message body + who + when/order). No media files. |
| Operator UX | Orchestrated from a **Cursor agent session**. The agent guides the human (e.g. QR) and runs automation. |
| Automation split | **Scripts** own the heavy/repeatable work (browser, traverse, write JSON). The agent orchestrates and handles human-only steps. |
| Runtime | Manual, on the operator's Mac. Not a scheduled service in v1. |
| Output | JSON under a repo-local gitignored directory (see ADR-0002 for path). Success feedback = file on disk + short agent note that it is there. |
| Consumers | External AI / learning systems read the JSON; they are not built here. |

## 3. Consequences

| Easier | Harder |
| :--- | :--- |
| Clear MVP: one export path, one number, text JSON | WhatsApp Web UI changes break scripts; needs a spike before large investment |
| Cursor + scripts match how the operator already works | ToS / account risk of automating Web; human must accept that trade-off |
| Customer data stays local via gitignore | Full-history scroll is slow and flaky; hardening is its own phase |
| Downstream AI can evolve without blocking this repo | Business API / multi-number / media require new ADRs |

## 4. Deciders

Gustavo (product owner) · Sprint 002 chat debate · session documentation

## 5. Considered Options

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **A — WhatsApp Web + Cursor-guided scripts (chosen)** | Matches “all stored chats”; fits manual Mac use; agent can coach QR/failures | Fragile UI; ToS risk; needs spike |
| **B — WhatsApp Business API** | Official channel | Does not export personal/business **history** for training dump |
| **C — Official per-chat export only** | Stable, allowed | Cannot scale to “all conversations” as one dump |
| **D — Local Desktop/backup DB** | May be complete offline | Encryption/OS variance; deferred unless Web spike fails |
| **E — Build analysis + bot in this repo** | One place | Out of stated product boundary; bloated MVP |

---
*Immutable once Accepted — a changed decision gets a new ADR that supersedes this one, never an in-place edit (`rules/documentation_standard.md §3`). File lives at `docs/decisions/ADR-0001-product-scope-whatsapp-web.md`.*
