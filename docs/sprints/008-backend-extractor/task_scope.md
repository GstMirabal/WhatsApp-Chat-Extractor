# Task Scope — Sprint 008 (backend-extractor)

Source: `docs/sprints/008-backend-extractor/IMPLEMENTATION_PLAN.md` (`## Work`)
and `agent_assignment.md` (Phase 4.1, staffing authority).
Phase 4.3 of `workflows/pipeline_workflow.md`, authored by `rule_validator`.

`agents.md §2 jurisdictional_lock` and `no_interference` both read this file: no
two in-progress units may name the same `File`, and each unit is one atomic
commit over one physical file.

Mode: **claude-code**, `delegation_mode: native`. `Model` and `Effort` are
required from Sprint 28 onward under every harness
(`scripts/check_task_scope.py:38`), and are transcribed from the `claude_code`
column of `.agents/config/model_tiers.json` by the profile's tier:

| Tier | Model | Effort | Profiles |
| :--- | :--- | :--- | :--- |
| `gate` | `opus` | `high` | `qa_agent`, `tester_agent`, `principal_agent` |
| `author` | `sonnet` | `medium` | `orchestrator`, `rule_validator`, `doc_orchestrator`, `implementer_agent`, … |
| `mechanical` | `haiku` | `low` | `devops_agent`, `git_sync_agent`, `topology_mapper` |

---

## Work

| # | File | Operation | Risk | Assignee | Model | Effort | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| A1 | `docs/sprints/008-backend-extractor/GATE_CHANNEL_DIAGNOSIS.md` | create | low | `orchestrator` | sonnet | medium |✅ cf68e0d |
| A2 | `docs/active_state.json` | modify | low | `orchestrator` | sonnet | medium |✅ untracked (anchor is gitignored) |
| A3 | `docs/0_SYSTEM_OVERVIEW.md` | modify | low | `doc_orchestrator` | sonnet | medium |✅ 3669a49 |
| B1 | `docs/decisions/ADR-0005-enumeration-completeness.md` | create | medium | `doc_orchestrator` | sonnet | medium | ✅ 1d184b6 |
| B2 | `src/whatsapp_chat_extractor/chat_list.py` | modify | high | `implementer_agent` | opus | high | ✅ e09967b |
| B3 | `tests/test_chat_list.py` | modify | medium | `implementer_agent` | sonnet | medium | ✅ 8ba1960 |
| B4 | `src/whatsapp_chat_extractor/manifest.py` | modify | medium | `implementer_agent` | sonnet | medium | ✅ d30a1b5 |
| B5 | `tests/test_manifest.py` | modify | low | `implementer_agent` | sonnet | medium | ✅ d30a1b5 |
| B6 | `src/whatsapp_chat_extractor/__main__.py` | modify | medium | `implementer_agent` | sonnet | medium | ✅ d30a1b5 |
| B7 | `tests/test_export_all.py` | modify | low | `implementer_agent` | sonnet | medium | ✅ d30a1b5 |
| B8 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | sonnet | medium | ✅ 329e420 |
| C1 | `scripts/probe_unknown_rows.py` | create | medium | `implementer_agent` | sonnet | medium |✅ 3669a49 |
| C2 | `tests/test_probe_unknown_rows.py` | create | medium | `implementer_agent` | sonnet | medium |✅ 3669a49 |
| C3 | `docs/sprints/008-backend-extractor/PROBE_UNKNOWN_ROWS_RUN.md` | create | low | `doc_orchestrator` | sonnet | medium |✅ 0db538a |
| D1 | `docs/PLATFORM_HARDENING.md` | modify | low | `doc_orchestrator` | sonnet | medium |✅ c9990b3 |
| D2 | `docs/audits/UPSTREAM_FINDING_008_BOOT_MISROUTE.md` | create | low | `rule_validator` | sonnet | medium |✅ 347a777 |
| D3 | `docs/audits/UPSTREAM_FINDING_009_POST_CONDITION.md` | create | low | `rule_validator` | sonnet | medium |✅ 347a777 |
| D4 | `docs/audits/UPSTREAM_FINDING_010_AUDIT_PLAN_FILTER6.md` | create | low | `rule_validator` | sonnet | medium |✅ 347a777 |
| D5 | `docs/audits/UPSTREAM_FINDING_011_MAKEFILE_UNQUOTED.md` | create | low | `rule_validator` | sonnet | medium |✅ 347a777 |

Nineteen units, nineteen distinct files: no `File` value repeats, so
`no_interference` cannot be violated by concurrent dispatch.

### Deviations from one-file-per-commit

| Units | Commit | Why |
| :--- | :--- | :--- |
| B4–B7 | `d30a1b5` | A schema migration cannot leave the suite green in any intermediate state. Four separate commits would publish three red ones, which `RA-08`'s "atomic" is meant to prevent, not require. `jurisdictional_lock` is unaffected: the units ran sequentially in one session, never concurrently |
| A3, C1, C2 | `3669a49` | A3 is a two-line header correction that the same commit's new probe needed reflected in the topology table |
| B8 + walkthrough | `329e420` | `RA-14` patch propagation: the walkthrough asserted the defect was open in the same words the blueprint was correcting |

### Added during execution, outside the approved Work table

| # | File | Why |
| :--- | :--- | :--- |
| D6 | `docs/audits/UPSTREAM_FINDING_012_BRIDGE_CLOBBERS_HOST_COMMANDS.md` | Found while drafting D2–D5. The anchor's `upstream` summary counted eight findings and named `_004`–`_011`, but `acknowledged_gaps` separately recorded a twelfth with no file. Same class and same destination as the four approved; drafted rather than left out. Commit `347a777` |

---

## Tier escalation

One unit departs from its profile's tier. `token_economy_agent` requires the
reason to be recorded rather than inferred.

| # | Profile tier | Applied | Reason |
| :--- | :--- | :--- | :--- |
| B2 | `author` (sonnet / medium) | `opus` / `high` | The only unit whose subject is a new termination-bearing algorithm rather than an edit to an existing one. `sweep_until_stable` must converge under an adversarial reordering fixture while remaining bounded, and a wrong stop condition reintroduces the exact silent undercount the sprint exists to remove — the failure mode is loss with no error. Every other B unit is a mechanical propagation of B2's result |

---

## Ordering constraints

`Status` moves to `✅ <sha>` as each commit lands. Two dependencies are hard:

| Constraint | Reason |
| :--- | :--- |
| A1 precedes Phase 7 | It decides whether the gates are dispatched as subagents at all |
| B1 precedes B4 | ADR-0005 names the three values that `manifest.py` then emits |
| B2 precedes B3–B7 | Those units propagate `sweep_until_stable`'s signature and result |
| C1 precedes C2 | The test file addresses the probe's real function names |
| C3 is operator-gated | It records a live WhatsApp Web run no agent can start |
