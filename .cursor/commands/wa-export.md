---
description: "Export one WhatsApp chat's full history to JSON (Keyword: wa-export)"
argument-hint: "<chat name fragment>"
---

Export the full history of one WhatsApp chat to `data/`, using the chat name
fragment in `$ARGUMENTS`.

1. If `$ARGUMENTS` is empty, ask which chat to export and stop. Do not guess a
   chat: the export opens whatever the search matches first.
2. Run, from the repository root:

   ```
   .venv/bin/wa-extract export-one --query "$ARGUMENTS"
   ```

   A visible Chromium window opens on the operator's Mac. If it shows a QR
   instead of the chat list, the session has expired — tell the operator to run
   `.venv/bin/wa-extract login` and scan it, then stop.

   Run it outside any sandboxed shell. Chromium cannot create its
   `ProcessSingleton` socket inside one and aborts before reaching WhatsApp.

3. Read the exit code directly, never through a pipe:

   | Exit | Meaning | What to report |
   | :--- | :--- | :--- |
   | `0` | Full history reached | Path, `message_count`, and `stopped_reason` |
   | `3` | Stopped at the pass cap — the dump is truncated | Same, plus that `complete` is `false` and the run needs a higher `--max-passes` |
   | `2` | Timed out waiting for the session or the chat | The logged message; do not retry silently |
   | `1` | The chat search matched nothing | The query that failed |

4. Report the JSON path the command printed on stdout, together with
   `message_count`, `complete`, `stopped_reason` and a count of `messages` by
   `kind`, all read from that file. State `complete` explicitly every time — a
   truncated corpus reported as a success is the failure this command exists to
   prevent.

Schema v4 (ADR-0003): every message carries a `kind` of `text`, `image`, `voice`
or `unknown`. A media message is a record with an empty `body`; no media file is
downloaded or referenced. `unknown` marks a medium the DOM probe has not yet
identified — it is a stated gap, not a defect to work around.

Constraints:

- Never print message bodies into the transcript. The export holds a real
  person's conversation; report counts and the file path, not content.
- Never commit anything under `data/`. It is gitignored and holds customer data.
- One chat per invocation. Exporting every chat is Sprint 007 and has no command
  yet.
