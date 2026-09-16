# Security Policy

## Supported versions

This project has no maintained release branches — only the latest tag on
`main` receives fixes. See [`CHANGELOG.md`](CHANGELOG.md) for the current
version.

## Reporting a vulnerability

**Do not open a public GitHub issue for a security vulnerability.** Use one
of:

1. [GitHub private vulnerability reporting](https://github.com/GstMirabal/WhatsApp-Chat-Extractor/security/advisories/new)
   (preferred — keeps the report and any discussion private until a fix
   ships).
2. Email gst.mirabal@gmail.com with a description of the issue and, if
   possible, steps to reproduce it.

Please include:

- What the vulnerability allows (e.g. arbitrary code execution, data
  exposure, credential leakage)
- Steps to reproduce it, or a proof of concept
- The affected version/commit

**Do not** include a real exported chat, a screenshot of a live WhatsApp Web
session, or any other file that could contain a real conversation or contact
name in the report — see
[Privacy constraints](README.md#privacy-constraints) in the README.

## What is in scope

This tool drives a real, authenticated WhatsApp Web session and writes its
output to local disk. Vulnerabilities of particular interest:

- Anything that could exfiltrate an exported conversation, the browser
  session/profile under `data/browser_profile/`, or a real contact name
  beyond what `--write-index` already discloses on request
- Anything that could make the harvester act on the WhatsApp Web page beyond
  reading and scrolling the chat panel (e.g. sending a message, as
  `composer_write_risk` in `docs/active_state.json` already tracks as an
  investigated, not-yet-confirmed hardening candidate)
- Supply-chain issues in this project's own dependency pinning

## Response

This is a single-maintainer project. There is no SLA, but reports are read
and acknowledged as soon as the maintainer sees them.
