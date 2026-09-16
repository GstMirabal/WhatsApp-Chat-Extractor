# Contributing

This is a private, proprietary repository ([`LICENSE`](LICENSE)) that may be
made publicly readable without becoming open to outside code contributions.
Publication grants no license to use, copy, modify or distribute the
software — reading the source is not the same as being invited to change it.

## External pull requests

Not accepted. There is no review process for outside code changes, and none
is planned. A pull request opened against this repository will be closed
without merging.

## Reporting a bug

Open a [GitHub issue](https://github.com/GstMirabal/WhatsApp-Chat-Extractor/issues)
describing:

- What you ran (the exact `wa-extract` command and flags)
- What you expected vs. what happened
- The exit code, if the process ran to completion
- Your platform (macOS/Linux) and Python version

Do **not** attach an exported chat file, a screenshot of the chat panel, or
any other file that could contain a real conversation or contact name — see
[Privacy constraints](README.md#privacy-constraints) in the README. A log
line or a stack trace with no message body is fine.

For a security vulnerability, do not open a public issue — see
[`SECURITY.md`](SECURITY.md).

## How changes actually happen

Every change to this repository, when one is accepted, lands through the
Token-Optimized Agent Pipeline governed by the `.agents` submodule: an
Implementation Plan, an `ai-sprint/[ID]` branch, and a Quality Gate, all
recorded under [`docs/sprints/`](docs/sprints/). That process is internal —
it is not a mechanism for taking outside contributions, only the discipline
this repository's own maintainer works under.

## Questions

Gustavo Mirabal — gst.mirabal@gmail.com ([@GstMirabal](https://github.com/GstMirabal)).
