# Implementation Plan: Sprint 010 — corpus-consolidation

**Canonical path**: `docs/sprints/010-backend-extractor/IMPLEMENTATION_PLAN.md`
**Branch**: `ai-sprint/009` (folded onto the open sprint branch by human decision — see Approval) · **Base**: `main` at `d0cdbb4`
**Status**: `APPROVED` → `EXECUTING`

> Authored at Phase 1 by `principal_agent`, extracted to this path at Phase 3,
> committed before Phase 5 approves it (`agents.md §2 triple_lock`).
> Spanish permitted here (`agents.md §1 user_chat`); every other artifact English.

---

## Context

El Sprint 009 dejó **1018 ficheros `data/chat_*.json`**, uno por conversación,
todos schema v6, 6,4 MB, 12.942 mensajes. Reproducir:

```
ls data/chat_*.json | wc -l                    # 1018
python3 -c "import json,glob,collections; c=collections.Counter(json.load(open(f))['schema_version'] for f in glob.glob('data/chat_*.json')); print(dict(c))"   # {6: 1018}
du -ch data/chat_*.json | tail -1              # 6.4M
```

Un consumidor del corpus — el caso `ADR-0001 §2` «External AI / learning
systems read the JSON» — tiene que abrir 1018 ficheros y unirlos él mismo. No
hay un artefacto único. El manifiesto (`data/run_manifest_<run_id>.json`)
registra el *resultado* de la ejecución, no el contenido de las conversaciones.

**Estado verificado antes de planificar**: cero `chat_id` duplicados entre los
1018 ficheros — el `--resume` nunca re-exportó nada. Sin `data/chat_index_*` en
disco: no hay nombres reales que consolidar (`ADR-0001` intacto).

```
python3 -c "import json,glob,collections; b=collections.Counter(json.load(open(f))['chat_id'] for f in glob.glob('data/chat_*.json')); print('distinct:',len(b),'dups:',sum(1 for v in b.values() if v>1))"
# distinct: 1018 dups: 0
```

**Cuando está hecho**: `wa-extract consolidate` produce un único
`data/corpus_<run_id>.ndjson` con una línea de cabecera de procedencia y 1018
líneas, una por conversación, cada una con el export v6 entero — sin descartar
ningún campo ni ningún mensaje. Un `chat_id` repetido entre ficheros de entrada
aborta con un error nombrado. Una entrada que no sea v6 aborta.

---

## Design

### D1 — NDJSON, una conversación por línea

Elegido sobre un único objeto JSON `{chats: [...]}`. Razones: (a) es el formato
que un sistema de entrenamiento consume línea a línea sin cargar 6 MB en
memoria; (b) un corte a mitad de escritura deja N líneas válidas y una rota, no
un fichero entero inválido; (c) el Sprint 009 ya eligió NDJSON append-only para
el diario (`ADR-0006` D1) y para el contrato de corpus (`ADR-0007`) — un tercer
formato para el mismo dominio sería incoherencia.

Rechazado: **un objeto JSON único**. Más simple de `json.load` de una vez, pero
obliga al consumidor a leerlo entero y un truncamiento lo invalida completo.

### D2 — La primera línea es una cabecera de procedencia, no una conversación

`{"record": "header", "corpus_schema": 1, "chat_schema": 6, "source_run":
"<run_id>", "generated_at": "<iso>", "chat_count": <n>}`. Un consumidor lee la
primera línea, comprueba `record == "header"`, y sabe cuántas líneas de
conversación esperar y contra qué esquema. Mismo patrón que
`journal.JournalHeader` (`ADR-0006`).

`source_run` se toma del `--from-manifest` si se pasa, o del `run_id` más
reciente presente en `data/run_manifest_*.json`, o `"unknown"` si no hay
ninguno. `chat_count` se escribe **después** de contar las líneas escritas, no
antes — así la cabecera no puede mentir sobre el cuerpo.

### D3 — La línea de conversación es el export v6 verbatim

Cada línea es `json.dumps(export, ensure_ascii=False)` del contenido del fichero
`data/chat_*.json` tal cual, con **todos** sus campos (`schema_version`,
`chat_id`, `exported_at`, `message_count`, `undated_messages`, `complete`,
`completeness`, `stopped_reason`, `passes_used`, `source_locale`,
`source_timezone`, `messages`) y **todos** los mensajes. Consolidar es unir, no
transformar: nada se aplana, nada se recorta, nada se recalcula.

### D4 — `consolidate` es un subcomando sin navegador

Como `recover` (`ADR-0006` D4). No importa Playwright. Leer 1018 ficheros JSON y
escribir uno no necesita un navegador, y forzar uno haría el comando
inejecutable en una máquina sin Chromium.

### D5 — Un `chat_id` repetido aborta; no se deduplica en silencio

El Sprint 009 dejó cero duplicados, pero una ejecución futura con un `--resume`
mal usado podría dejarlos. Si dos ficheros de entrada llevan el mismo `chat_id`,
`consolidate` aborta con `duplicate chat_id <id> in <file-a> and <file-b>` y
sale `2`. Deduplicar «quedándose con el más reciente» sería una decisión de
producto que este sprint no toma: el operador debe ver el conflicto y resolverlo
borrando el fichero equivocado.

### D6 — Una entrada que no sea `schema_version: 6` aborta

`consolidate` no mezcla esquemas. Si un fichero de entrada no es v6, aborta con
`<file> is schema <n>, expected 6` y sale `2`. Un corpus con líneas de esquemas
distintos es una trampa para el consumidor.

### D7 — Módulo nuevo, no crecimiento de `__main__.py`

La lógica de consolidación vive en `src/whatsapp_chat_extractor/consolidate.py`.
`__main__.py` solo añade `cmd_consolidate` y `_add_consolidate` (el patrón de
`recover`), que llaman al módulo. `__main__.py` ya está en 793 líneas
(`§D6` del Sprint 009, deuda registrada) — no se le añade lógica, solo el
cableado del subcomando.

---

## Work

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| A1 | `src/whatsapp_chat_extractor/consolidate.py` | create | medium | `implementer_agent` | ⏳ |
| A2 | `tests/test_consolidate.py` | create | low | `implementer_agent` | ⏳ |
| B1 | `src/whatsapp_chat_extractor/__main__.py` | modify | low | `implementer_agent` | ⏳ |
| B2 | `tests/test_consolidate_cli.py` | create | low | `implementer_agent` | ⏳ |
| C1 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | ⏳ |
| C2 | `docs/walkthroughs/EXTRACTOR_WALKTHROUGH.md` | modify | low | `doc_orchestrator` | ⏳ |

**Contenido exigible por unidad** (`agents.md §1 unambiguous_action`):

| # | Operación y criterio de terminación |
| :--- | :--- |
| A1 | Define `CORPUS_SCHEMA_VERSION = 1`, `read_chat_files(data_dir) -> list[dict]` (glob `chat_*.json`, orden estable por nombre), `build_header(chats, source_run) -> dict`, `resolve_source_run(data_dir, from_manifest) -> str`, y `write_corpus(chats, header, out_path) -> Path` (cabecera primero, luego una línea `json.dumps(chat, ensure_ascii=False)` por conversación). `read_chat_files` lanza `ValueError` con el mensaje de `§D5` ante un `chat_id` repetido y con el de `§D6` ante un `schema_version != 6`. Ninguna función supera 50 líneas ni 3 niveles de indentación. Termina cuando `ruff check .` sale `0`. |
| A2 | Cubre: tres ficheros v6 sintéticos bajo `tmp_path` producen un NDJSON de 4 líneas, cabecera con `chat_count: 3` y `chat_schema: 6`, y cada línea de conversación `json.loads`-eable e idéntica al fichero de entrada; un `chat_id` repetido lanza `ValueError` nombrando ambos ficheros; un fichero `schema_version: 5` lanza `ValueError` nombrando el fichero y el número; `chat_count` de la cabecera se cuenta tras escribir el cuerpo, verificado con un cuerpo de 0 conversaciones dando `chat_count: 0`; el orden de las líneas es estable entre dos ejecuciones. Termina cuando los cinco casos pasan. |
| B1 | Añade `cmd_consolidate(args)` y `_add_consolidate(sub)` con `--data-dir` (default `data/`), `--from-manifest <path>` (opcional) y `--out <path>` (opcional, default `data/corpus_<source_run>.ndjson`). `cmd_consolidate` no importa Playwright y no lo importa ningún módulo que él importe. Registra `_add_consolidate(sub)` en `build_parser`. Sale `0` en éxito, `2` ante `ValueError` de `consolidate`. Termina cuando `ruff check .` sale `0` y ninguna función nueva supera 50 líneas. |
| B2 | Cubre la orquestación con el patrón `monkeypatch` de `tests/test_resume.py`, sin navegador: `consolidate` sobre un `tmp_path` con 2 ficheros v6 escribe `data/corpus_<run>.ndjson` con 3 líneas y sale `0`; un `chat_id` duplicado en el `tmp_path` hace salir `2` y no escribe fichero; `--out` explícito determina la ruta; prueba que `import playwright` bloqueado no impide `consolidate` (patrón de `sys.meta_path` de `tests/test_export_all.py` si existe, o `monkeypatch` de `sys.modules`). Termina cuando los casos pasan. |
| C1 | Añade `wa-extract consolidate` a la tabla de componentes y una subsección «Corpus consolidation» describiendo el formato NDJSON (cabecera + una línea por conversación, contrato v6 verbatim) y los dos abortos (`chat_id` repetido, esquema ≠ 6). Referencia este plan, no lo reproduce. Termina cuando ninguna ruta declarada en el blueprint falta del árbol. |
| C2 | Añade una sección operativa: cómo generar el corpus único tras una ejecución, el comando, dónde queda el fichero, y cómo leerlo línea a línea (`for line in open(...): json.loads(line)`), saltándose la primera. Actualiza el pie a `#010`. Termina cuando el comando citado existe en `--help`. |

---

## Dependencies

| Package | Version | Why the standard library and the existing dependencies do not suffice |
| :--- | :--- | :--- |
| None | — | `json`, `pathlib` y `glob` bastan. NDJSON es una línea `json.dumps` por registro; no hay biblioteca que añadir. |

---

## Mechanisms

| Mechanism | Deterministic or agent judgment | Invoker (`RA-16`) |
| :--- | :--- | :--- |
| Unión de los `chat_*.json` en un NDJSON | script — `consolidate.write_corpus`, sin criterio de agente | `src/whatsapp_chat_extractor/__main__.py` `cmd_consolidate`, subcomando `consolidate` |
| Detección de `chat_id` repetido entre ficheros de entrada | script — comparación de conjuntos en `consolidate.read_chat_files` | idem |
| Validación de `schema_version == 6` de cada entrada | script — comprobación por fichero en `consolidate.read_chat_files` | idem |

Ninguno es un instrumento del framework: son funciones del paquete del host,
invocadas por el CLI que las contiene.

---

## Cost

| Field | Value | Reproduce |
| :--- | :--- | :--- |
| Delegation | `native` | `docs/active_state.json` `delegation_mode` |
| Work units | 6 | Count of rows in the Work table |
| Subagents dispatched | 4 planned (2 `implementer_agent`, 2 `doc_orchestrator`) | Phase 4.1 `agent_assignment.md` is the authority |
| Prior session ratio | measured at Phase 1 open | `python3 .agents/scripts/session_cost.py --from-anchor --json` |

---

## Tests

| Check | Fails against the current tree? |
| :--- | :--- |
| `python3 -m pytest tests/test_consolidate.py -q` | **Yes** — the file does not exist; this is the new capability |
| `python3 -m pytest tests/test_consolidate_cli.py -q` | **Yes** — same |
| `python3 -m pytest -q` (283 passed / 1 skipped now) | **No** — must stay green, rising only by the count of added tests |

---

## Verification

| Command | Expected |
| :--- | :--- |
| `ruff check .` | exit `0` |
| `python3 -m pytest -q` | `283 + <new>` passed, `1` skipped, exit `0` |
| `python3 -c "import ast,glob; [print(f,n.name,n.end_lineno-n.lineno+1) for f in ['src/whatsapp_chat_extractor/consolidate.py','src/whatsapp_chat_extractor/__main__.py'] for n in ast.walk(ast.parse(open(f).read())) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.end_lineno-n.lineno+1>50]"` | no output (no function over 50 lines) |
| `.venv/bin/wa-extract consolidate --data-dir data` then `head -1 data/corpus_*.ndjson` | header line with `"record": "header"`, `"chat_count": 1018` |
| `wc -l data/corpus_*.ndjson` | `1019` (1 header + 1018 conversations) |
| `python3 -c "import sys; sys.modules['playwright']=None; import whatsapp_chat_extractor.consolidate"` | no `ImportError` — the module is browserless |

---

## Documentary impact (T5)

| Artefacto | Qué cambia |
| :--- | :--- |
| `src/whatsapp_chat_extractor/consolidate.py` | Nuevo módulo: lee `chat_*.json`, valida v6 y unicidad de `chat_id`, escribe `corpus_<run_id>.ndjson` |
| `src/whatsapp_chat_extractor/__main__.py` | Nuevo subcomando `consolidate` (cableado; sin lógica) |
| `tests/test_consolidate.py`, `tests/test_consolidate_cli.py` | Nuevos: contrato del NDJSON, los dos abortos, la orquestación CLI sin navegador |
| `docs/architecture/EXTRACTOR_BLUEPRINT.md` | Componente `consolidate` + subsección del formato de corpus |
| `docs/walkthroughs/EXTRACTOR_WALKTHROUGH.md` | Sección operativa: generar y leer el corpus único |
| `CHANGELOG.md` | Entrada `### Added` bajo `[Unreleased]` en el cierre |

---

## Out of scope

| Exclusion | Why, and where it goes instead |
| :--- | :--- |
| Nombres reales / `chat_index` en el corpus | `ADR-0001`: el corpus queda pseudónimo. Un consumidor que necesite títulos usa el `chat_index` por separado, bajo `--write-index`, sin mezclarlo aquí |
| Deduplicar `chat_id` repetidos | `§D5`: se aborta, no se decide por el operador. Una política de dedup es un sprint aparte si alguna vez hace falta |
| Convertir v5 a v6 al vuelo | `ADR-0007` `§D9`: los v5 no se reparan. `consolidate` los rechaza; migrarlos es otra decisión |
| `§D5`/`§D6`/`T-2`/`KI-009-H` del Sprint 009 | Registrados en el roadmap como P6; este sprint es solo la consolidación. Si el operador quiere agruparlos aquí, es una renegociación de alcance a decidir antes de la Fase 5 |
| Timeout de reloj en el bucle de cosecha (`KI-009-H`) | No lo toca la consolidación. Roadmap P6, con la enmienda sistémica de H-003 §5 |

---

## Abort criterion

Si al ejecutar `consolidate` sobre `data/` real resulta que **sí** hay `chat_id`
duplicados (contra lo verificado en Context), el sprint se detiene: el diseño
`§D5` asume cero duplicados como estado de partida y un conflicto real cambia la
pregunta de «unir» a «resolver conflictos», que es otro sprint.

---

## Approval — `triple_lock` lock 1

| Field | Value |
| :--- | :--- |
| **Approved by** | Human (repository owner), attended |
| **Date** | 2026-09-10 |
| **Plan commit at approval** | committed with this line; approval given in the same session, against this text |
| **Execution branch** | `ai-sprint/009`, by explicit human choice — Sprint 009 is not yet deployed, and the owner chose to fold this work onto the open branch rather than wait. `RA-12` deviation is deliberate and recorded here; Sprint 009's deployment will carry both |
| **Remaining locks** | Active Sprint · QA + Tester verdicts · Human OK at close |

*Phase 5 is a single attended human authorization. It MUST NOT be wrapped inside an
unattended `/loop` (`workflows/pipeline_workflow.md`, `rules/loop_governance.md`).
Any `/loop` this sprint does run — Phases 6-8 only — is governed by
`scripts/loop_guard.py start`, which fails closed.*
