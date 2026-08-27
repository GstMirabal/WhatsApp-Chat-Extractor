# Roadmap: WhatsApp Chat Extractor — delivery program

Program authority: [ADR-0001](../../decisions/ADR-0001-product-scope-whatsapp-web.md),
[ADR-0002](../../decisions/ADR-0002-delivery-program-and-layout.md).

| Phase | Sprint | Status | Goal |
| :--- | :--- | :--- | :--- |
| P0 | 002 | CLOSED | Seal product + delivery ADRs, overview, this roadmap |
| P1 | 003 | IN_PROGRESS | Spike: one chat via WhatsApp Web → text JSON in `data/` |
| P2 | 004 | PLANNED | Happy path: Cursor agent + scripts for a usable dump |
| P3 | 005+ | PLANNED | Harden: full history, all chats, retries / partial failure |
| — | — | OUT OF REPO | AI analysis (solicitudes, sentimiento), learning server, bot |

## Phase notes

| Phase | In | Out |
| :--- | :--- | :--- |
| P0 | Decisions only (no product code) | Playwright, `src/`, live dump |
| P1 | Minimal package + Playwright proof on Mac | All-chats dump, Cursor skill polish |
| P2 | Agent orchestration command/skill; scripts do the work | Sentiment/bot; perfect resilience |
| P3 | Completeness and robustness of export | Downstream AI products |
