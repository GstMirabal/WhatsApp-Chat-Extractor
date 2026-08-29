# Implementation Plan: Sprint 004 — backend-extractor (P2 happy path)

**Canonical path**: `docs/sprints/004-backend-extractor/IMPLEMENTATION_PLAN.md`
**Branch**: `ai-sprint/004` · **Base**: `main` at `b090ed3bbac7851c40b6ff37b0114a20535a5abf` (v0.3.0)
**Status**: `APPROVED` (2026-08-29) → `EXECUTING`

> Español permitido en este documento (`agents.md §1 user_chat`). Todo el resto de
> artefactos del pipeline es inglés. Fase del programa: ADR-0002 §2.1 P2.

---

## Context

P1 (#003) demostró la cadena completa en Mac: QR → sesión persistente → un chat →
JSON en `data/`. La prueba produjo `data/Rocio_Luca_de_Tena_20260827T152444Z.json`
con **84 mensajes**, capturados con `--scroll-passes 8`.

Ese fichero no cumple su propósito declarado. El destino del JSON es **corpus de
aprendizaje para un agente**, y 84 mensajes son los que quedaban visibles en el
DOM tras ocho scrolls — no la conversación. El roadmap situaba "historial
completo" en P3; se adelanta a P2 porque un corpus truncado por un número
arbitrario de scrolls no es un entregable parcial, es un entregable inválido.

| Figura | Valor | Reproduce |
| :--- | :--- | :--- |
| Base SHA | `b090ed3` | `git rev-parse HEAD` (= `last_close_commit` del ancla) |
| Mensajes P1 | 84 | `python3 -c "import json;print(len(json.load(open('data/Rocio_Luca_de_Tena_20260827T152444Z.json'))['messages']))"` |
| Código actual | 655 líneas, 5 módulos | `find src -name '*.py' \| xargs wc -l \| tail -1` |
| Tests actuales | 106 líneas, 2 suites | `wc -l tests/*.py` |
| Criterio de salida | Un chat → JSON con `complete: true` y `message_count` > 84 | Ver §Verification |

### Defecto raíz: virtualización del DOM

`export_one.scroll_message_panel` (líneas 176-192) hace N scrolls al tope y luego
`collect_visible_messages` (líneas 195-228) lee el DOM **una sola vez**. WhatsApp
Web **recicla** las filas de mensaje: las que salen del viewport se eliminan del
DOM. Subir el número de pasadas no arregla nada — lo empeora: cuanto más arriba
llega el scroll, más mensajes **recientes** se han descartado ya del DOM cuando
por fin se recolecta.

La corrección no es "más scroll". Es **recolectar de forma incremental durante el
scroll y deduplicar**.

---

## Design

| Decisión | Elección | Rechazado |
| :--- | :--- | :--- |
| Alcance del volcado | **Un chat por invocación**, historial completo | Volcado de todos los chats (queda en P3) |
| Estrategia de captura | Cosecha incremental: scroll → recolectar → deduplicar → repetir | Scroll al tope y recolectar una vez (defecto actual) |
| Identidad de mensaje | `data-id` del row cuando exista; si no, hash de `(sender, timestamp, body)` | Índice posicional (inestable bajo virtualización) |
| Terminación | Marcador de inicio de chat **o** N pasadas consecutivas sin ids nuevos, **más** tope duro de pasadas | Solo tope duro (no distingue "terminado" de "cortado") |
| Honestidad del corpus | El JSON declara `complete` y `stopped_reason` | Escribir un volcado parcial indistinguible de uno completo |
| Testabilidad | Acumulador **puro** en `history.py`, separado de la capa Playwright | Lógica de dedupe dentro de la función que maneja `page` |
| Formato de salida | JSON únicamente, `schema_version: 2` | Texto plano / CSV (el consumidor es un agente) |
| Superficie de disparo | CLI `wa-extract` (lógica) + comando slash que lo envuelve | Skill Three-File (sin decisiones que delegar todavía) |
| Ubicación del comando | `.claude/commands/wa-export.md`, raíz de `commands/` | Dentro de `.claude/commands/agents/` (symlink del framework) |
| Datos exportados | Siguen en `data/`, gitignored (`.gitignore:29`) | Commitear chats reales al repositorio |

### Orden de los mensajes

El scroll va hacia arriba, así que cada pasada descubre mensajes **más antiguos**
que los ya vistos. El acumulador conserva el orden de aparición dentro de cada
pasada y **antepone** el bloque nuevo al acumulado. El campo `order` se asigna
una sola vez, al final, sobre la secuencia consolidada — nunca durante la cosecha,
donde todavía puede aparecer un prefijo más antiguo.

---

## Work

Una fila = un commit atómico (`RA-08`) sobre **un** fichero físico como sujeto
estructural (`agents.md §2 jurisdictional_lock`).

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| W1 | `src/whatsapp_chat_extractor/history.py` | create | medium | `implementer_agent` | ⏳ |
| W2 | `src/whatsapp_chat_extractor/export_one.py` | modify | high | `implementer_agent` | ⏳ |
| W3 | `src/whatsapp_chat_extractor/writers.py` | modify | low | `implementer_agent` | ⏳ |
| W4 | `src/whatsapp_chat_extractor/__main__.py` | modify | low | `implementer_agent` | ⏳ |
| W5 | `tests/test_history.py` | create | low | `implementer_agent` | ⏳ |
| W6 | `tests/test_writers.py` | modify | low | `implementer_agent` | ⏳ |
| W7 | `.claude/commands/wa-export.md` | create | low | `skill_architect` | ⏳ |
| W8 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | ⏳ |
| W9 | `CHANGELOG.md` | modify | low | `doc_orchestrator` | ⏳ |

### Detalle por unidad

| # | Contenido |
| :--- | :--- |
| W1 | `MessageAccumulator` puro: `add_pass(rows) -> int` (devuelve ids nuevos), `consolidate() -> list[MessageRecord]` asignando `order`. Más `harvest_history(page, *, max_passes, stall_threshold) -> HarvestResult` con la capa Playwright. `HarvestResult` lleva `messages`, `complete`, `stopped_reason`, `passes_used`. |
| W2 | Añadir `_row_id(row) -> str` (lee `data-id`, con fallback a hash estable de `sender\|timestamp\|body`). `collect_visible_messages` pasa a devolver filas con su id. Añadir `at_chat_start(page) -> bool` para el marcador de inicio. `scroll_message_panel` pasa a scroll de **una** pasada (`scroll_one_pass`), porque el bucle vive en W1. |
| W3 | `ChatExport` v2: añadir `schema_version: int`, `message_count: int`, `complete: bool`, `stopped_reason: str`. `build_export` los rellena. Fichero de salida sin cambio de nombre. |
| W4 | Sustituir `--scroll-passes` por `--max-passes` (tope duro, default 2000) y `--stall-threshold` (default 3). Log de progreso cada pasada (`ids nuevos / total`). Salir con código `3` cuando el volcado termine con `complete: false`, para que el comando slash lo distinga de un éxito. |
| W5 | Tests del acumulador con secuencias de pasadas simuladas: solapamiento, duplicados, bloque nuevo íntegro, pasada vacía, estabilización tras `stall_threshold`. Cero WhatsApp en vivo. |
| W6 | Aserciones de esquema v2 sobre `build_export` y `write_chat_export`. |
| W7 | `/wa-export` — recibe el fragmento de nombre del chat, ejecuta `wa-extract export-one --query …`, informa ruta, `message_count` y `complete`. |
| W8 | Contrato de historial completo: identidad de mensaje, terminación, esquema v2, y qué significa `complete: false`. |
| W9 | Entrada de Sprint 004 bajo `[Unreleased]`. |

---

## Dependencies

| Package | Version | Why the standard library and the existing dependencies do not suffice |
| :--- | :--- | :--- |
| None | — | `playwright` ya es dependencia (P1); el dedupe usa `hashlib` y `dict` de stdlib |

---

## Mechanisms

| Mechanism | Deterministic or agent judgment | Invoker (`RA-16`) |
| :--- | :--- | :--- |
| Cosecha incremental con dedupe | script (`history.harvest_history`) | `__main__.cmd_export_one` |
| Detección de fin de historial | script (`export_one.at_chat_start` + umbral de estancamiento) | `history.harvest_history` |
| Disparo de la exportación | comando slash → CLI | `human:/wa-export` |

Ningún mecanismo recurrente se delega a juicio de agente: la decisión de "¿queda
historial?" es una comparación de conjuntos de ids, determinista y testeable.

---

## Cost

| Field | Value | Reproduce |
| :--- | :--- | :--- |
| Delegation | `sequential` | `docs/active_state.json` `delegation_mode` |
| Work units | 9 | Filas de la tabla Work |
| Subagents dispatched | 0 | `sequential` bajo Cursor |
| Prior session ratio | n/a (Cursor / sin transcript medible) | `python3 .agents/scripts/session_cost.py --from-anchor --json` |

---

## Tests

| Check | Fails against the current tree? |
| :--- | :--- |
| Una secuencia de pasadas con solapamiento produce cada mensaje una sola vez | **Sí** — no existe acumulador; hoy se recolecta una vez |
| El volcado se detiene por marcador de inicio y reporta `complete: true` | **Sí** — no existe criterio de terminación |
| El volcado se detiene por tope duro y reporta `complete: false` | **Sí** — hoy nada distingue completo de truncado |
| `build_export` emite `schema_version`, `message_count`, `complete`, `stopped_reason` | **Sí** — esquema v1 no los tiene |
| `open_chat_by_query` sigue resolviendo el título del chat | **No** — regresión a proteger (`tests/test_export_search.py`) |
| `write_chat_export` sigue escribiendo `<slug>_<stamp>.json` en `data/` | **No** — regresión a proteger (`tests/test_writers.py`) |

---

## Verification

Códigos de salida leídos con `$?` directo, nunca a través de una tubería.

| Command | Expected |
| :--- | :--- |
| `ruff check .` | exit `0` |
| `python3 -m pytest -q` | exit `0`, cero fallos, suites nuevas incluidas |
| `python3 -m py_compile $(find src tests -name '*.py')` | exit `0` |
| `wa-extract export-one --query "<chat de prueba>"` | exit `0`, imprime la ruta del JSON |
| `python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['schema_version'],d['message_count'],d['complete'])" <ruta>` | `2 <N> True` con `N` > 84 |
| `git -C .agents status --porcelain` | vacío (`submodule_purity`) |

---

## Documentary impact (T5)

| Artefacto | Qué cambia |
| :--- | :--- |
| `docs/architecture/EXTRACTOR_BLUEPRINT.md` | Contrato de historial completo y esquema v2 |
| `docs/roadmaps/docs/extractor/002-delivery-program.md` | P2 → CLOSED; nota de que "historial completo" se adelantó de P3 |
| `docs/walkthroughs/EXTRACTOR_WALKTHROUGH.md` | Recorrido con `/wa-export` y lectura de `complete` |
| `CHANGELOG.md` | Entrada Sprint 004 bajo `[Unreleased]` |
| `docs/active_state.json` | `current_sprint` abierto a 004; `acknowledged_gaps.spike` reemplazado por la cifra P2 |
| `docs/sprints/004-backend-extractor/` | `task_scope.md`, `agent_assignment.md`, `skill_assignment.md`, `PHASE_REGISTER.md`, `SPRINT_LOG.md` |

---

## Out of scope

| Exclusion | Why, and where it goes instead |
| :--- | :--- |
| Volcado de todos los chats | Decisión del humano 2026-08-29: primero un chat probado. Va a P3 / Sprint 005 |
| Media, reacciones, estados de entrega | ADR-0001 limita el producto a texto. Fuera del repositorio |
| Análisis IA (solicitudes, sentimiento), bot | ADR-0001 lo marca OUT OF REPO |
| Reintentos ante caída de sesión a mitad de volcado | P3 "retries / partial failure"; W1 lo mitiga parcialmente vía `complete: false` |
| Corrección del bug de `session_start.py --boot` | Clase framework. `docs/audits/UPSTREAM_FINDING_004_SESSION_START_BOOT_ROOT.md` → PR al núcleo desde un clon aparte |
| Limpieza del ancla obsoleta en `.agents/docs/active_state.json` | `§3 strict_rule` prohíbe al host editar el submódulo. Va en el mismo PR upstream |
| Reparación de los MCP caídos (`graphify`, `git-sync-agent`) | Entorno, no producto. `acknowledged_gaps.graphify` ya lo registra |

---

## Abort criterion

Se aborta el sprint y se revierte la rama si, al ejecutar contra WhatsApp Web
real, **ninguna** identidad de mensaje resulta estable: es decir, si `data-id`
está ausente en las filas y el hash de `(sender, timestamp, body)` produce
colisiones sobre el chat de prueba de P1 (dos mensajes distintos con la misma
clave, comprobable comparando `message_count` contra el recuento de claves
únicas).

Sin identidad estable, la deduplicación no puede probarse correcta y el volcado
"completo" sería una afirmación no verificada — peor que el truncado honesto de
hoy. En ese caso el sprint se replantea sobre la opción de ventana acotada
(`--desde-fecha` / `--últimos-N`), que no requiere identidad estable.

---

## Approval — `triple_lock` lock 1

| Field | Value |
| :--- | :--- |
| **Approved by** | GstMirabal (`gst.mirabal@gmail.com`), aprobación atendida en chat |
| **Date** | 2026-08-29 |
| **Plan commit at approval** | Commiteado en `ai-sprint/004` antes de la primera unidad de trabajo |
| **Remaining locks** | Active Sprint · veredictos QA + Tester · OK humano al cierre |

*La Fase 5 es una única autorización humana atendida. NO puede envolverse en un
`/loop` desatendido (`workflows/pipeline_workflow.md`, `rules/loop_governance.md`).*
