# Implementation Plan: Sprint 012 — backend-extractor

**Canonical path**: `docs/sprints/012-backend-extractor/IMPLEMENTATION_PLAN.md` (extracted here at Phase 3)
**Branch**: `ai-sprint/012` · **Base**: `main` at `6259d5e06119987066e097aa4ac8b8ec0d04f9e8`
**Status**: `DRAFT`

---

## Context

Sprint 011 closed and is sealed on `main` as `v0.10.0` (`git rev-parse main` →
`6259d5e0`, tag `v0.10.0`; `python3 -m pytest -q` → 316 passed, 1 skipped;
`ruff check .` → exit 0). Product scope is complete per the delivery roadmap:
`export-all` covers every conversation, survives a crash (`--resume`,
`recover`), consolidates into one corpus (`consolidate`), and now bounds a
harvest by wall-clock time (`--deadline-seconds`, Sprint 011).

The operator asked this sprint to bundle **everything currently open** that
stands between this state and (a) publishing the repository and (b) running
it routinely against the real WhatsApp Business account. Verified this
session, not carried from memory:

1. **Selector defect, still live.** `export_one.py:49-54`
   `SEARCH_RESULT_SELECTORS` is `('#pane-side div[role="listitem"]',
   '#pane-side div[role="row"]', '[data-testid="cell-frame-container"]',
   '#side div[role="listitem"]')`. `scripts/probe_chat_start.py` runs 1-2
   measured the first entry at 0 matches (always) and the second at 59
   matches on a wrapper that accepts a click and opens nothing; the entry
   that actually opens a chat, `[data-testid="cell-frame-container"]`, is
   third. An operator running `export-one --query "..."` can get a silent
   no-op requiring a manual chat open. No regression test pins the order.
2. **`--deadline-seconds` CLI→harvest wiring is untested** (Sprint 011's own
   Tester Agent, `SPRINT_LOG.md` Phase 7). `commands.py:179` and `:248` both
   thread `args.deadline_seconds` into `harvest_history`, but
   `tests/test_export_all.py`'s existing fakes monkeypatch at the
   `open_chat_by_digest` boundary — one layer above where the flag is
   threaded — so a mutation turning it into a no-op leaves the suite green.
   The same gap covers `test_strength_gaps` F-4: no test drives
   `cmd_export_all` to a truncated chat and asserts `EXIT_INCOMPLETE` (3).
3. **README is stale against the shipped code in three independent ways**:
   the schema badge reads `v4`; the README's own JSON example reads
   `"schema_version": 5`; the real constant (`writers.py:17`) is
   `SCHEMA_VERSION = 6`. Usage documents only `login`, `export-one`,
   `export-all` — `recover` and `consolidate` (`__main__.py` `add_parser`,
   5 subcommands total) are undocumented, as are `--resume` and
   `--deadline-seconds`. The `--write-index` section still describes the
   pre-Sprint-011 batched `data/chat_index_<stamp>.json` writer; the real
   file (Sprint 011 §D5) is the append-only `data/chat_index_<run_id>.ndjson`.
4. **`docs/0_SYSTEM_OVERVIEW.md` drifted the moment its own fix landed.**
   Its header (line 4) and Released section (line 11) state `main` is at
   `136c1e1`, sealed `v0.9.0`, "deployment pending" — this is the exact
   staleness class the file's own note claims was "found and corrected
   2026-09-15," reproduced again by the same sprint's own deployment.
   `python3 .agents/scripts/docs_freshness_check.py` passes anyway (exit 0):
   it does not check version/SHA claims against `git`, so this class of
   drift is currently invisible to the automated gate.
5. **`EXTRACTOR_BLUEPRINT.md` header never advanced past Sprint 008** (`Last
   Audit Sprint: #008`, SHA `d30a1b5`) though its own body already documents
   Sprint 011 content (`grep -n "Sprint 011" docs/architecture/EXTRACTOR_BLUEPRINT.md`
   → 4 hits) — `RA-05 SPRINT_CLOSEOUT` requires the stamp to move with the
   sprint that touches the file.
6. **`pyproject.toml:7`** declares `version = "0.4.0"`; the latest tag is
   `v0.10.0` (`git describe --tags --abbrev=0`).
7. **Naming inconsistency going into publication.** The GitHub remote,
   `identity.config.json:6` (`repo_slug`), and the README's own clone command
   and Contact link all read `GstMirabal/WhastApp-Chat-Extractor` (typo); the
   local directory was already corrected to `WhatsApp-Chat-Extractor`. Human
   decision already taken: rename the remote to match (see *Public-repository
   actions*).
8. **Platform docs absent** — `CONTRIBUTING.md`, `SECURITY.md`,
   `CODE_OF_CONDUCT.md`, `NOTICE.md` are not present at the host root (`ls .`);
   `LICENSE` is. Open since Sprint 006 per `docs/PLATFORM_HARDENING.md`.
9. **A stale hotfix-ID reference risks a real collision.**
   `docs/active_state.json` → `acknowledged_gaps.search_open_defect` labels
   item 1 above "candidate hotfix H-002." `docs/hotfixes/H-002-docs.md`
   already exists, closed, about an unrelated defect (Sprint 008's Global
   Roadmap staleness). Per `KI-H001-C` the next free id is derived from
   `docs/hotfixes/H-*.md`, never from prose — `ls docs/hotfixes/` → `H-001`,
   `H-002`, `H-003` exist, so the free id is `H-004`.
10. **The repository is private on GitHub's free plan**
    (`gh repo view --json isPrivate,visibility` → `true`, `PRIVATE`), which
    returns `403` on branch protection/rulesets (`docs/PLATFORM_HARDENING.md`).
    This is a plan/visibility decision, not a code defect.
11. **Two Dependabot PRs are open and stale** (`gh pr list`: `#3`
    `actions/setup-python` 4→7, wait: `#4` `actions/checkout` 4→7, `#3`
    `actions/setup-python` 5→7, opened 2026-08-30). Their last check runs
    (`gh pr checks 3|4`) are 1-3s zero-step failures from the billing-block
    era, not current signal.
12. **No orchestration exists for an unattended full run.** A whole-account
    export is ~15h (`docs/PLATFORM_HARDENING.md`, measured 2026-08-31:
    enumeration ~3min + ~60s/conversation × 910). `--resume`/`recover`
    (Sprint 009) already provide crash recovery; nothing documents how an
    operator wires that into a cron/launchd job.

**Explicitly re-verified and found NOT to need action this sprint**: the
`EXTRACTOR_WALKTHROUGH.md` (content already covers Sprints 009-011 in full,
despite an initial suspicion it hadn't); `data/` has never been committed in
any commit, ever (`git log --all --diff-filter=A --name-only -- data/` →
empty); a targeted grep for a filled-in real contact name in early sprint
docs and query examples found nothing (`grep -rniE
"query[\"']?\s*[:=]\s*[\"'][A-ZÁÉÍÓÚÑ][a-záéíóúñ]+" …` → no hits) — still
worth a final human pass per `PLATFORM_HARDENING.md`'s own note that this
check "deserves a check by a person, because neither is mechanical."

---

## Design

- **One sprint, not several**, per explicit operator decision — same
  precedent as Sprint 011's own bundling
  (`docs/sprints/011-backend-extractor/IMPLEMENTATION_PLAN.md` § Context).
- **Item 1 (selector) is a normal Work row on `ai-sprint/012`, not an
  `RA-03` hotfix branch.** `RA-03` governs defects handled *outside* the
  sprint pipeline; this one is deliberately inside it. *Rejected*: opening
  `hotfix/H-004` — nothing about this defect is time-critical mid-sprint, and
  splitting it back out would fragment the operator's own bundling decision
  for no safety benefit.
- **Item 2 (coverage gap) is closed by extending the existing fake-`Page`
  pattern one layer deeper** (`tests/test_export_all.py`'s
  `open_chat_by_digest` monkeypatch moves to monkeypatching
  `harvest_history` directly, so the assertion can see what
  `deadline_seconds` value it received), not by building a
  Playwright-driving harness. *Rejected*: a real-browser integration
  harness — this project's standing rule is no live WhatsApp in CI (README §
  Contributing; `docs/PLATFORM_HARDENING.md`), and the named gap is a pure
  argument-propagation question, answerable by monkeypatching one function.
- **Item 12 (unattended runs) is closed with a runbook, not new code**
  (`docs/RUNBOOK.md`) — operator decision. `--resume`/`recover` already give
  crash recovery; a cron/launchd wrapper is operator configuration, not a
  library feature. *Rejected*: a retry/alerting script — new code surface
  and a candidate new dependency (e.g. for a webhook alert) for something a
  documented pattern over the existing CLI already covers.
- **Public-repository actions (rename, visibility, branch protection, secret
  scanning, Dependabot merges) are not Work rows.** They touch no local file
  as their structural subject, so `jurisdictional_lock` does not apply to
  them the way it applies to a commit. They are sequenced strictly *after*
  every Work row lands and Phase 7 gates pass, listed in their own section
  below, and — per explicit operator decision — executed by this session
  with a **separate confirmation immediately before each one**, since every
  one of them is either hard to reverse or externally visible.
- **The stale "candidate hotfix H-002" label in `docs/active_state.json`
  is corrected in this sprint** (Work row 9), in the same sprint that fixes
  the defect it describes, rather than left to drift further — the same
  failure class `docs/hotfixes/H-002-docs.md` itself exists to record.
- **`docs/active_state.json` is edited by `principal_agent`, not
  `implementer_agent`** — it is the state anchor, not source/doc content;
  every other Work row is documentation or source and follows the normal
  assignment.

---

## Work

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `src/whatsapp_chat_extractor/export_one.py` | modify | medium | `implementer_agent` | ⏳ |
| 2 | `tests/test_open_first_result.py` | create | low | `implementer_agent` | ⏳ |
| 3 | `tests/test_export_all.py` | modify | low | `implementer_agent` | ⏳ |
| 4 | `README.md` | modify | low | `implementer_agent` | ⏳ |
| 5 | `docs/0_SYSTEM_OVERVIEW.md` | modify | low | `doc_orchestrator` | ⏳ |
| 6 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | ⏳ |
| 7 | `pyproject.toml` | modify | low | `implementer_agent` | ⏳ |
| 8 | `identity.config.json` | modify | low | `implementer_agent` | ⏳ |
| 9 | `docs/active_state.json` | modify | low | `principal_agent` | ⏳ |
| 10 | `CONTRIBUTING.md` | create | low | `doc_orchestrator` | ⏳ |
| 11 | `SECURITY.md` | create | low | `doc_orchestrator` | ⏳ |
| 12 | `CODE_OF_CONDUCT.md` | create | low | `doc_orchestrator` | ⏳ |
| 13 | `NOTICE.md` | create | low | `doc_orchestrator` | ⏳ |
| 14 | `docs/RUNBOOK.md` | create | low | `doc_orchestrator` | ⏳ |

Row 1 detail: reorder `SEARCH_RESULT_SELECTORS` so
`[data-testid="cell-frame-container"]` is tried before
`#pane-side div[role="row"]` (measured as the selector that actually opens a
chat; `#pane-side div[role="listitem"]` stays first since it costs nothing at
0 matches and removing dead entries is not this row's purpose). Row 2 must
fail against the *current* order before row 1 lands (`KI-H001-B`).

Row 3 detail: two new tests — (a) `_export_open_chat` forwards
`args.deadline_seconds` to `harvest_history` unchanged (fake `harvest_history`
records the kwargs it received); (b) `cmd_export_all` returns
`EXIT_INCOMPLETE` (3) end-to-end when a chat's harvest reports
`completeness="truncated"` (closes `test_strength_gaps` F-4 for
`cmd_export_all`; `cmd_export_one`'s own real-`sync_playwright()` launch
remains untested by design, unchanged project convention).

---

## Dependencies

| Package | Version | Why the standard library and the existing dependencies do not suffice |
| :--- | :--- | :--- |
| None | — | — |

*This sprint adds no dependency: the test-coverage rows extend the existing
monkeypatch pattern; the runbook documents `cron`/`launchd` as operator
configuration, outside this package.*

---

## Mechanisms

| Mechanism | Deterministic or agent judgment | Invoker (`RA-16`) |
| :--- | :--- | :--- |
| None proposed | — | This sprint adds no new recurring mechanism to the pipeline. The runbook (row 14) documents an operator-owned `cron`/`launchd` pattern outside `.agents`' own automation, not a mechanism this framework invokes. |

---

## Cost

| Field | Value | Reproduce |
| :--- | :--- | :--- |
| Delegation | `native` | `docs/active_state.json` `delegation_mode` |
| Work units | 14 | Count of rows in Work table |
| Subagents dispatched | 0 (not yet executing) | — |
| Prior session ratio | 6.8× (most recent cycle), over the soft threshold (5×), under the hard bound (15×) | `python3 .agents/scripts/session_cost.py --from-anchor --json` |

Soft-threshold breach note: this cycle's cost is research-heavy (verifying
every Context claim against `git`/code/`gh` before writing this plan, per
`KI-006-F` — recording an inference with the confidence of a measurement is
this project's recurring failure). No action beyond recording it here; watch
the ratio again after Phase 6 begins.

---

## Tests

| Check | Fails against the current tree? |
| :--- | :--- |
| New: `_open_first_result` opens the chat via `[data-testid="cell-frame-container"]` when `#pane-side div[role="row"]` also matches | **Yes** — current order clicks the `role="row"` wrapper first and opens nothing |
| New: `_export_open_chat` forwards `deadline_seconds` to `harvest_history` unchanged | **Yes** — no test references `deadline_seconds` at this boundary today (`grep -rn "deadline_seconds" tests/` → 0 hits) |
| New: `cmd_export_all` returns `EXIT_INCOMPLETE` (3) when a chat truncates | **Yes** — `test_strength_gaps` F-4, no test names `EXIT_INCOMPLETE` for `cmd_export_all` today |
| Existing suite after rows 1-3 | **No** — regression guard; must still pass 100% |

---

## Verification

| Command | Expected |
| :--- | :--- |
| `ruff check .` | exit `0` |
| `python3 -m pytest -q` | all pass, 0 regressions vs. 316 passed / 1 skipped baseline |
| `git rev-parse main` vs. text in `docs/0_SYSTEM_OVERVIEW.md` line 4 | match after row 5 |
| `grep -n "Last Audit Sprint" docs/architecture/EXTRACTOR_BLUEPRINT.md` | reads `#012` after row 6 |
| `grep -n "schema_version\|Schema v" README.md` and `grep -n "SCHEMA_VERSION" src/whatsapp_chat_extractor/writers.py` | both read `6` after row 4 |
| `python3 -c "import ast,pathlib"` AST walk (max 50 lines / depth 3) over `src/whatsapp_chat_extractor/` | 0 violations, unchanged from Sprint 011 |
| `ls CONTRIBUTING.md SECURITY.md CODE_OF_CONDUCT.md NOTICE.md` | all four exist after rows 10-13 |

---

## Documentary impact (T5)

| Artefacto | Qué cambia |
| :--- | :--- |
| `README.md` | Badge de schema v4→v6; agrega `recover`, `consolidate`, `--resume`, `--deadline-seconds` a Usage; corrige la sección `--write-index` al comportamiento append-only real; corrige el nombre del repo en el clone command y el link de Contact |
| `docs/0_SYSTEM_OVERVIEW.md` | Header y sección Released sincronizados con `main` real (`v0.10.0`, sellado) |
| `docs/architecture/EXTRACTOR_BLUEPRINT.md` | Header `Last Audit Sprint`/Date/SHA avanzado a #012 |
| `docs/active_state.json` | `acknowledged_gaps.search_open_defect` corregido de "candidate hotfix H-002" a la referencia correcta tras el fix |
| `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `NOTICE.md` | Creados por primera vez |
| `docs/RUNBOOK.md` | Nuevo — cómo operar `export-all` de forma desatendida con `--resume`/`recover` |

---

## Out of scope

| Exclusion | Why, and where it goes instead |
| :--- | :--- |
| `test_strength_gaps` F-6 (enumeration is an unvalidated `str`) | No mencionado por el operador como prioridad para este sprint; queda carried en `docs/active_state.json` como ya venía |
| Los 11 (verificado: 12) hallazgos upstream del framework en `docs/audits/` | Deuda de gobernanza de `.agents`, jurisdicción nucleus (`agents.md §4 feedback_upstream`) — no se resuelve desde un sprint host |
| Script de orquestación (reintentos/alertas) para la corrida de ~15h | Operator decision: runbook en lugar de código nuevo (ver Design) |
| `composer_write_risk` (hardening candidate) | Ya investigado y registrado como "RESOLVED AS NOT OBSERVED" en `docs/active_state.json`; no es un defecto confirmado, no hay nada que parchear |

---

## Public-repository actions (Phase 8, human-gated — not Work rows)

Ejecutadas por esta sesión únicamente después de que las filas 1-14 estén
mergeadas y Phase 7 (Double-Gate) haya aprobado — nunca contra un `main` que
todavía va a cambiar debajo. Cada una pide confirmación explícita e
individual en el momento de ejecutarla (decisión del operador), porque cada
una es difícil de revertir o visible externamente.

| # | Acción | Comando de referencia |
| :--- | :--- | :--- |
| a | Renombrar el repo remoto | `gh repo rename WhatsApp-Chat-Extractor` |
| b | Actualizar el remote local | `git remote set-url origin https://github.com/GstMirabal/WhatsApp-Chat-Extractor.git` |
| c | Rebasear y re-correr CI en los 2 PRs de Dependabot, mergear si quedan verdes | `gh pr checks 3`, `gh pr checks 4`, `gh pr merge --squash` |
| d | Pasar el repositorio a público | `gh repo edit --visibility public` (confirmación explícita — irreversible en los hechos: GitHub permite revertir a privado, pero el contenido ya distribuido no) |
| e | Aplicar branch protection con los 4 checks requeridos | comando exacto en `docs/PLATFORM_HARDENING.md` § *"What unlocks when the repository becomes public"* punto 1 |
| f | Confirmar que `ci_gate.py` ya lee el requirement | `python3 .agents/scripts/ci_gate.py <PR>` → exit `0` |
| g | Secret scanning + push protection | `docs/PLATFORM_HARDENING.md` punto 3 |
| h | Private vulnerability reporting | `docs/PLATFORM_HARDENING.md` punto 4 |

---

## Abort criterion

Decidido antes de ejecutar, no renegociable una vez hundido el costo:

- Si la fila 1 (reorder de selectores) rompe cualquier test existente de
  `test_open_chat_verification.py` o `test_probe_chat_start.py` de forma que
  no pueda resolverse con un ajuste acotado a esos dos archivos, se revierte
  solo la fila 1 y se documenta como carried — no bloquea el resto del
  sprint.
- Si al llegar a la acción **(d)** (pasar a público) aparece cualquier
  archivo bajo `data/` en `git log --all --diff-filter=A -- data/` que no
  apareció en la verificación de este plan, se **aborta todo el bloque de
  acciones públicas** (d-h) hasta que el hallazgo se investigue y, si
  corresponde, se purgue del historial — publicar con una conversación real
  filtrada no es reversible.

---

## Approval — `triple_lock` lock 1

| Field | Value |
| :--- | :--- |
| **Approved by** | *(pendiente)* |
| **Date** | *(pendiente)* |
| **Plan commit at approval** | *(pendiente — se completa en Phase 3)* |
| **Remaining locks** | Active Sprint · QA + Tester verdicts · Human OK at close |

*Phase 5 is a single attended human authorization. It MUST NOT be wrapped inside an
unattended `/loop` (`workflows/pipeline_workflow.md`, `rules/loop_governance.md`).
Any `/loop` this sprint does run — Phases 6-8 only — is governed by
`scripts/loop_guard.py start`, which fails closed.*
