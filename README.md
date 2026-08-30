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
| `0` | The harvest reached the start of the chat. `complete` is `true`. |
| `3` | The harvest stopped at the pass cap. The file is valid but truncated. |
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

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## What the export contains

```json
{
  "schema_version": 4,
  "chat_id": "9f60a8baaaab",
  "exported_at": "2026-08-30T08:53:00Z",
  "message_count": 301,
  "complete": false,
  "stopped_reason": "max_passes",
  "messages": [
    { "sender": "contact", "timestamp": "18:29, 28/8/2026",
      "body": "¿lo tienes?", "kind": "text", "order": 137 }
  ]
}
```

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
2. **No contact name is written to disk.** `chat_id` is a digest of the chat
   title; the title itself is hashed and dropped. This is pseudonymization, not
   anonymization: the digest is unsalted, so anyone holding a candidate name can
   confirm a match.
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
