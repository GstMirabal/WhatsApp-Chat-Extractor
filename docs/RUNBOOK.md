# Runbook: running `export-all` unattended

How to operate a routine, unattended whole-account export using the
recovery primitives that already exist (`--resume`, `recover`), without new
orchestration code. `docs/PLATFORM_HARDENING.md` covers repository/platform
controls; this document covers running the tool itself.

## The constraint that decides everything: no headless mode

Every browser launch in this codebase is hardcoded `headless=False`
(`session.py`, `launch_context`) — a real, visible Chromium window is
required for the QR login and stays required for every subsequent run. This
is deliberate, not an oversight: WhatsApp Web's own anti-automation checks
are more likely to flag a headless session.

**Consequence**: this cannot run on a headless server or CI runner. It needs
a Mac that is logged in with a GUI session available, whenever a run fires.

**Consequence for the scheduler**: prefer **`launchd`** over plain `cron` on
macOS. A `cron` job runs outside the Aqua GUI session even while a user is
logged in, so a Chromium window it launches may fail to open correctly or
render off-screen. A `launchd` **LaunchAgent** (not a LaunchDaemon — Agents
run inside the logged-in user's GUI session) does not have that problem.

## One-time setup

```bash
.venv/bin/wa-extract login
```

Scan the QR code once. The session persists in `data/browser_profile/`
(gitignored) until WhatsApp expires it — expect to repeat this
occasionally, unattended or not.

## The unattended run itself

```bash
.venv/bin/wa-extract export-all --write-index --deadline-seconds 900
```

- `--deadline-seconds 900` (15 min) bounds each conversation's harvest by
  wall-clock time. Without it, a conversation whose panel never resolves can
  run the full `--max-passes` budget with nobody watching. Pick a value
  comfortably above the ~60s/conversation this project has measured for a
  healthy chat (`README.md` § Exporting every chat), so the deadline only
  ever fires on a genuinely stuck one.
- `--write-index` is optional — only turn it on if the downstream consumer
  of the run needs real conversation names; it is the one file this project
  writes that contains them (`README.md` § Privacy constraints).

Exit codes to check (`README.md` § Usage / `commands.py::_run_exit_code`):

| Exit | Meaning | What to do |
| :--- | :--- | :--- |
| `0` | Enumeration converged, nothing failed, every enumerated conversation has a journal line | Nothing — the run is whole |
| `3` | Enumeration didn't converge, at least one chat failed, or fewer chats landed than were enumerated | Resume it (below) |
| *process killed / crashed, no exit at all* | Something ended the run outright (e.g. a lost WhatsApp session) | Resume it (below) — the journal already has everything the run got to before it died |

## Recovering a run that didn't finish

The run's `run_id` is printed at the start of the run (also derivable from
`data/run_journal_<run_id>.ndjson`, the newest one under `--data-dir`).

**Check what a run actually got to, with no browser at all:**

```bash
.venv/bin/wa-extract recover --run-id <run_id>
```

Rebuilds the manifest from the journal alone — safe to run any time, cheap,
and useful right after a crash before deciding whether to resume.

**Continue the run:**

```bash
.venv/bin/wa-extract export-all --resume <run_id> --write-index --deadline-seconds 900
```

The chat list is enumerated again from scratch (never trusted from the
journal); every conversation the journal already marks `exported` is
stepped over. Safe to run this repeatedly — a `--resume` on an already-`0`
run just re-confirms nothing is left to do.

## Wiring it into `launchd`

A minimal `LaunchAgent` that fires once a day and lets `--resume` absorb
whatever a previous run left unfinished, rather than retrying inside the
plist itself:

```xml
<!-- ~/Library/LaunchAgents/com.example.wa-export.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.example.wa-export</string>
  <key>ProgramArguments</key>
  <array>
    <string>/path/to/repo/.venv/bin/wa-extract</string>
    <string>export-all</string>
    <string>--deadline-seconds</string><string>900</string>
  </array>
  <key>WorkingDirectory</key><string>/path/to/repo</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>3</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/tmp/wa-export.log</string>
  <key>StandardErrorPath</key><string>/tmp/wa-export.err</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.example.wa-export.plist
```

This fires the run once; it does not retry on exit `3` or resume a prior
`run_id` automatically — read `/tmp/wa-export.log` (or the printed manifest
path) and issue the `--resume` command above by hand, or wrap it in a small
shell script that greps the last `run_id` out of the log before the next
scheduled fire. Deliberately not automated further here: this project
documents the recovery primitives it already has rather than adding a
retry/alerting layer (see `docs/sprints/012-backend-extractor/IMPLEMENTATION_PLAN.md`
§ Design).

## Consolidating after a run (or several)

```bash
.venv/bin/wa-extract consolidate
```

Joins every per-conversation `data/chat_*.json` into one NDJSON corpus for
the downstream reader — see `README.md` § Building one corpus.
