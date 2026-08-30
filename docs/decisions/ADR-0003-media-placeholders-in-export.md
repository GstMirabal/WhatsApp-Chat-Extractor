# ADR-0003: Media messages appear in the export as placeholders
**Status**: `Accepted`
**Date**: 2026-08-30
**Supersedes**: the *Coverage* row of [ADR-0001](ADR-0001-product-scope-whatsapp-web.md) §2
**Triggers**: 2, 4 (`rules/documentation_standard.md §3.1`)

---

## 1. Context

ADR-0001 fixed coverage as **"full history, text only (message body + who +
when/order). No media files."** The implementation read that literally: a row
with no selectable text is skipped, so a photo or a voice note leaves **no trace
at all** in the export.

The consequence was measured during Sprint 004's live verification. A DOM probe
of the first 12 rows of one conversation found three media messages — one image
(`image-thumb`) and two voice notes (`ptt-status`) — none of which reached the
JSON. The exported conversation therefore reads as:

| What happened | What the corpus shows |
| :--- | :--- |
| Question → voice note answer → follow-up | Question → follow-up |

The consumer of this file is an agent learning how the business talks to its
customers (ADR-0001 §1). A gap with no marker is worse than a marked gap: the
agent cannot distinguish "nothing was said" from "something was said in a form
this export does not carry", and will learn from adjacency that never existed.

"No media files" was a decision about **storage and privacy** — do not download
or embed the media. It was read as a decision about **conversation structure**,
which it was not.

## 2. Decision

| Topic | Decision |
| :--- | :--- |
| Media messages | Emitted as a record with an empty `body` and a `kind` naming the medium. **Never skipped.** |
| Media content | Still never downloaded, embedded, or referenced by URL. ADR-0001's storage boundary is unchanged. |
| Record shape | `MessageRecord` gains `kind`; text messages carry `kind: "text"` |
| Recognised kinds | `text`, `image`, `video`, `audio`, `voice`, `document`, `sticker`, `location`, `contact`, `deleted`, `system`, `unknown` |
| Unrecognised media | `kind: "unknown"` — reported, never dropped and never guessed |
| Captions | An image or video caption **is** text and is kept in `body`, with `kind` naming the medium |
| Schema | Bumped to v4; `kind` is required on every record |

A record with an empty `body` is now meaningful rather than a bug, which is the
inversion this ADR makes explicit: the previous implementation used empty body
as the skip condition.

## 3. Consequences

| Easier | Harder |
| :--- | :--- |
| Turn structure survives; the agent sees that something occupied that turn | Every consumer must handle records whose `body` is empty |
| `message_count` finally counts messages rather than text messages | Counts are not comparable with v3 exports of the same chat |
| Media kinds are countable, so the operator can see how much of a chat is non-text | Kind detection depends on WA Web markup and will need the same probe-first discipline as direction (Sprint 004, `KI-004-A`) |
| Deleted and system messages stop being invisible | More rows to classify, more chances to land on `unknown` |

**Privacy is unchanged.** A placeholder records that a voice note existed; it
does not record what was said in it. No media byte reaches disk.

## 4. Deciders

Gustavo (product owner), 2026-08-30 in chat: *"debemos añadir imagen o voice
note, para que el aprendizaje sea correcto"* · Sprint 004 live probe as evidence.

## 5. Considered Options

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **A — Placeholder record with a `kind` (chosen)** | Preserves turn structure; no media stored; countable | Schema break; consumers must handle empty bodies |
| **B — Keep skipping media** | No change | The stated purpose fails: the corpus teaches adjacencies that never happened |
| **C — Download media alongside the JSON** | Complete record | Contradicts ADR-0001's storage boundary; large customer-data footprint on disk |
| **D — Transcribe voice notes** | Richest corpus | Sends customer audio to a third-party service; a privacy decision far beyond this ADR, and the operator's constraint runs the other way |

---
*Immutable once Accepted — a changed decision gets a new ADR that supersedes this one, never an in-place edit (`rules/documentation_standard.md §3`). File lives at `docs/decisions/ADR-0003-media-placeholders-in-export.md`.*
