<div align="center">

[![Python][python-shield]][python-url]
[![License: Proprietary][license-shield]][license-url]
[![Schema v4][schema-shield]][schema-url]

</div>

<a name="readme-top"></a>

<h3 align="center">WhatsApp Chat Extractor</h3>

<p align="center">
  Export a WhatsApp Web chat's full history to local pseudonymous JSON.
<br /><br />
<a href="docs/0_SYSTEM_OVERVIEW.md"><strong>Explore the docs »</strong></a>
</p>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul><li><a href="#built-with">Built With</a></li></ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation--configuration">Installation &amp; Configuration</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#what-the-export-contains">What the export contains</a></li>
    <li><a href="#privacy-constraints">Privacy constraints</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>

## About The Project

This tool drives a real WhatsApp Web session in a visible browser, scrolls one
conversation to the top, and writes its history to a JSON file under `data/`.
The intended consumer is an agent learning how a business talks to its
customers, which is why the output is built around one question: **does this
file hold the whole conversation, or only part of it?**

Every export answers that in the payload itself. `complete` is `true` only when
the harvest reached a proven start-of-chat marker; a run that stops at the pass
cap says so, and the CLI exits `3` rather than `0`. A truncated dump that is
indistinguishable from a complete one is the failure this project was rebuilt to
prevent.

| Property | Value |
| :--- | :--- |
| Scope | One chat per invocation, full history |
| Output | `data/chat_<digest>_<timestamp>.json`, schema v4 |
| Media | Recorded as a placeholder with a `kind`; no media file is downloaded |
| Identity | No contact name reaches the payload or the filename |
| Network | WhatsApp Web only; nothing is sent anywhere else |

### Built With

- [Python 3.11+](https://www.python.org/) — standard library plus one dependency
- [Playwright](https://playwright.dev/python/) — drives a persistent Chromium profile
- [pytest](https://docs.pytest.org/) and [ruff](https://docs.astral.sh/ruff/) — the quality gate

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

### Prerequisites

- macOS or Linux with Python **3.11 or newer**
- A WhatsApp account you own, reachable from your phone to scan a QR once
- A terminal that is **not sandboxed**. Chromium cannot create its
  `ProcessSingleton` socket inside a sandbox and aborts before reaching
  WhatsApp.

### Installation & Configuration

1. **Clone the repository**
   ```bash
   git clone https://github.com/GstMirabal/WhastApp-Chat-Extractor.git
   cd WhastApp-Chat-Extractor
   ```

2. **Create the virtual environment**
   ```bash
   python3 -m venv .venv
   ```

3. **Install the package and its browser**
   ```bash
   .venv/bin/pip install -e ".[dev]"
   .venv/bin/playwright install chromium
   ```

4. **Log in once**
   ```bash
   .venv/bin/wa-extract login
   ```
   A Chromium window opens showing a QR code. Scan it from WhatsApp on your
   phone. The session is stored in `data/browser_profile/`, which is gitignored,
   and survives across runs until WhatsApp expires it.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

Export one chat by a fragment of its name, exactly as you would type it into
WhatsApp's own search box:

```bash
.venv/bin/wa-extract export-one --query "Nombre del contacto"
```

The command prints the path of the file it wrote. Read the **exit code**, not
the log, to know what you got:

| Exit | Meaning |
| :--- | :--- |
| `0` | The export finished. `completeness` is `proven` or `unproven` — see below. |
| `3` | The harvest was **truncated**: it ended before the conversation did. |
| `2` | Timed out waiting for the session or for the chat to open. |
| `1` | The search matched no chat. |

Useful options:

| Option | Default | What it does |
| :--- | :--- | :--- |
| `--max-passes` | `2000` | Upper bound on scroll passes. Raise it when exit `3` persists. |
| `--stall-threshold` | `3` | Passes revealing nothing new before the harvest gives up. |
| `--data-dir` | `data/` | Where the JSON is written. |

From an agent session, `/wa-export <chat>` runs the same command and reports
`complete` explicitly. It is available in both Claude Code and Cursor.

### Exporting every chat

```bash
.venv/bin/wa-extract export-all
```

It enumerates the whole chat list, exports each conversation in turn, and prints
the path of a **run manifest** stating what happened to every one of them. Start
with `--limit 3` to see it work before committing to a full run.

| Option | Default | What it does |
| :--- | :--- | :--- |
| `--limit` | `0` (all) | Export only the first N chats. The rest are recorded as `skipped`, never omitted. |
| `--write-index` | off | **Writes real conversation names to disk.** See below. |
| `--settle-ms` | `1200` | Wait after each chat-list scroll. Raise it on a slow connection. |

**A full run is long.** Measured on 2026-08-31 against an account with 910
conversations: enumeration took about 3 minutes, and each conversation then took
roughly 60 seconds, most of it the three 15-second waits that confirm the panel
has stopped producing history. At that rate a whole-account export is on the
order of **15 hours**. Lowering `--load-wait-ms` is the lever, at the cost of
declaring a top the panel had not reached — the error `completeness` exists to
make visible.

One conversation failing does not end the run. It is recorded in the manifest
with its reason and the run continues; only losing the WhatsApp session aborts.

The manifest carries **no names**:

```json
{
  "schema_version": 1,
  "chats_enumerated": 910,
  "enumeration_complete": true,
  "counts": { "exported": 3, "failed": 0, "skipped": 907,
              "proven": 0, "unproven": 3, "truncated": 0, "messages": 129 },
  "chats": [
    { "chat_id": "chat_5666bd0c69f1", "index": 0, "outcome": "exported",
      "reason": "", "completeness": "unproven", "message_count": 31,
      "file": "chat_5666bd0c69f1_20260831T181033Z.json" }
  ]
}
```

`--write-index` additionally writes `data/chat_index_<stamp>.json`, mapping each
`chat_id` to the **real conversation name**. It is the only file this project
writes that contains names, it is off by default, and it is deliberately a
separate file so you can delete it without losing the manifest.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## What the export contains

```json
{
  "schema_version": 5,
  "chat_id": "chat_9f60a8baaaab",
  "exported_at": "2026-08-30T08:53:00Z",
  "message_count": 301,
  "complete": false,
  "completeness": "unproven",
  "stopped_reason": "stalled",
  "messages": [
    { "sender": "contact", "timestamp": "18:29, 28/8/2026",
      "body": "¿lo tienes?", "kind": "text", "order": 137 }
  ]
}
```

### How complete is it?

`completeness` answers that in three values ([ADR-0004](docs/decisions/ADR-0004-completeness-criterion.md)):

| Value | Meaning |
| :--- | :--- |
| `proven` | A start-of-conversation marker was seen. The whole history is here. |
| `unproven` | The panel stopped producing history and nothing indicated more was coming. Almost certainly the whole chat — but inferred, not proven. |
| `truncated` | The harvest ended before the conversation did. Raise `--max-passes`. |

**`proven` has never been produced.** Five conversations were measured across two
runs and no start marker appeared in any of them, so `unproven` is the normal,
expected result. The value is kept because the day WhatsApp Web renders such a
marker, the export must be able to say so.

`complete` is the old boolean, retained so readers of schema v4 keep working. It
is **derived** from `completeness == "proven"` and is therefore always `false`
today — which is exactly why `completeness` replaced it.

`sender` is a role — `me`, `contact` or `unknown` — never a name. `kind` is
mandatory on every message and is one of:

| `kind` | Meaning | `body` |
| :--- | :--- | :--- |
| `text` | An ordinary message, emoji included | The text |
| `image` | A photo | Its caption, or empty |
| `voice` | A voice note | Empty |
| `unknown` | A medium the DOM probe has not yet identified | Empty |

Media messages are recorded rather than skipped ([ADR-0003](docs/decisions/ADR-0003-media-placeholders-in-export.md)).
Dropping them made the conversation read as question → next question, teaching
an adjacency that never happened.

**Known limitation.** A message with no text carries no date in WhatsApp's DOM,
only a clock, so media rows have a `timestamp` of `H:MM` while text rows have
`H:MM, D/M/YYYY`. The date is not synthesized, because a fabricated one would be
indistinguishable from a measured one. Use `order` for sequence.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Privacy constraints

This repository handles a real person's conversations. Four rules are enforced
in code, not by convention:

1. **`data/` is never committed.** It is gitignored and CI fails if a chat
   export appears in a commit.
2. **No contact name is written to disk unless you ask for it.** `chat_id` is a
   digest of the chat title; the title itself is hashed and dropped. The one
   exception is `export-all --write-index`, which is off by default and named
   for what it does. This is pseudonymization, not anonymization: the digest is
   unsalted, so anyone holding a candidate name can confirm a match. It is also
   **not permanent** — the digest follows the title, so a renamed conversation
   gets a new `chat_id` and will not link to its earlier exports.
3. **No media content is downloaded or referenced.** No URL, blob or binary
   reaches the file — only the fact that a medium was sent.
4. **Message bodies stay out of agent transcripts.** The slash command reports
   counts and paths, never content.

Message bodies themselves are untouched and may name people on their own.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contributing

This is a private, proprietary repository and is not open to outside
contributions. Work follows the sprint pipeline in
[`.agents`](docs/0_SYSTEM_OVERVIEW.md): every change lands on an `ai-sprint/[ID]`
branch against an approved Implementation Plan, and the quality gate is

```bash
ruff check .
.venv/bin/python -m pytest -q
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## License

Proprietary. All rights reserved. See [`LICENSE`](LICENSE) for the terms; it is
the file `pyproject.toml` declares. No permission to use, copy, modify or
distribute is granted by publication of this repository.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contact

Gustavo Mirabal — gst.mirabal@gmail.com

- GitHub: [@GstMirabal](https://github.com/GstMirabal)

Project Link: [https://github.com/GstMirabal/WhastApp-Chat-Extractor](https://github.com/GstMirabal/WhastApp-Chat-Extractor)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[python-shield]: https://img.shields.io/badge/python-3.11%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white
[python-url]: https://www.python.org/downloads/
[license-shield]: https://img.shields.io/badge/license-Proprietary-red.svg?style=for-the-badge
[license-url]: LICENSE
[schema-shield]: https://img.shields.io/badge/export%20schema-v4-green.svg?style=for-the-badge
[schema-url]: docs/decisions/ADR-0003-media-placeholders-in-export.md
