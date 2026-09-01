# Skill Assignment — Sprint 008 (backend-extractor)

Source: `docs/sprints/008-backend-extractor/IMPLEMENTATION_PLAN.md`.
Phase 4.2 of `workflows/pipeline_workflow.md`. Drafted from this template.

Mode: **claude-code**, `delegation_mode: native`.

After writing this file, run:
`python3 scripts/check_forge_ladder.py --sprint-dir docs/sprints/008-backend-extractor`
(exit `2` rejects an empty forge destination or submodule contamination).

---

## 1. Priority ladder (record every rung)

`rules/skills_and_integrations.md §1`:

State the outcome of each rung. A ladder that terminates at an early rung says
so and leaves the rest as `not reached`.

| Rung | Source | Result | Evidence |
| :--- | :--- | :--- | :--- |
| P1 | `skills/manifest_skills.json` | resolved — the ladder terminates here | `omni-context-minimizer` and `python-quality-auditor` cover every tooling need this sprint has; no unit requires a capability the library lacks |
| P2 | `autoskills-3rd` | not reached | P1 resolved |
| P3 | `https://skills.sh/` (WebSearch/WebFetch; simulated JSON allowed in tests) | not reached | P1 resolved |
| P4 | Three-File Standard at Destination | not reached | P1 resolved |

**When this sprint builds a new skill**, the third rung's outcome MUST be recorded
as a machine-readable trail — a JSON object carrying `source`, `query` and a
boolean `hit`, shaped `{"source": "skills.sh", "query": "<term>", "hit": <bool>}`
with `<bool>` replaced by the real value. No HTTP in `make verify`.
`scripts/check_forge_ladder.py` requires that trail beside a named skill and its
`SKILL.md` path, and exits `2` without it.

---

## 2. Per-unit tool resolution

`scripts/probe_unknown_rows.py` (C1) is a **host application script**, not a
skill: it is operator-invoked against a live WhatsApp Web session, exactly like
`scripts/probe_chat_start.py` (#006) and `scripts/probe_chat_list.py` (#007).
The Three-File Standard does not apply to it.

| Unit | Skill / tool | Destination | P1–P4 trail |
| :--- | :--- | :--- | :--- |
| A1 | none | N/A | P1 resolved |
| A2 | none | N/A | P1 resolved |
| A3 | none | N/A | P1 resolved |
| B1 | none | N/A | P1 resolved |
| B2 | `omni-context-minimizer` | N/A | P1 resolved |
| B3 | `omni-context-minimizer` | N/A | P1 resolved |
| B4 | none | N/A | P1 resolved |
| B5 | none | N/A | P1 resolved |
| B6 | `omni-context-minimizer` | N/A | P1 resolved |
| B7 | none | N/A | P1 resolved |
| B8 | none | N/A | P1 resolved |
| C1 | `python-quality-auditor` | N/A | P1 resolved |
| C2 | none | N/A | P1 resolved |
| C3 | none | N/A | P1 resolved |
| D1 | none | N/A | P1 resolved |
| D2 | none | N/A | P1 resolved |
| D3 | none | N/A | P1 resolved |
| D4 | none | N/A | P1 resolved |
| D5 | none | N/A | P1 resolved |

`Destination` for a forged skill: `host:.claude/skills/<name>/` (default),
`profile:<path>`, or `nucleus:PR`. Writing under `.agents/skills/` from a
host session is PROHIBITED (`strict_rule`).

---

## 3. Skills used

| Skill | Why |
| :--- | :--- |
| `omni-context-minimizer` | `chat_list.py` (345), `__main__.py` (416) and `tests/test_chat_list.py` (376) all exceed the 200-line ceiling in `agents.md §2 ast_skeleton`; the skeleton precedes every partial read |
| `python-quality-auditor` | Ruff/Mypy/Bandit sweep over the new `scripts/probe_unknown_rows.py` before it reaches the Quality Gate |

## 4. Skills considered and rejected

| Candidate | Why rejected |
| :--- | :--- |
| `graphify` | Its MCP server cannot start — `.agents/venv_skillopt` is absent and no `graphify-out/` exists (accepted gap in the anchor). The sprint touches six named files, so `graph_sovereignty`'s recursive-grep concern does not arise |
| `token-saver-auditor` | Its `audit_plan.py` already ran as the Phase 1 gate (exit `0`); the skill is not re-invoked per unit |
| `readme-standardizer` | This sprint changes no `README.md` |
| `contract-writer` | No API contract changes; the manifest schema change is documented by ADR-0005 and the Blueprint |

## 5. Gaps

None that block execution. The `graphify` MCP failure is pre-existing, recorded
in `docs/active_state.json` under `acknowledged_gaps.graphify`, and owned by
`/agents:harden` plus a `venv_skillopt` build — not by this sprint.
