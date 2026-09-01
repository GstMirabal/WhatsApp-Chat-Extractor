# Implementation Plan: Sprint 008 — backend-extractor

**Canonical path**: `docs/sprints/008-backend-extractor/IMPLEMENTATION_PLAN.md`
**Branch**: `ai-sprint/008` · **Base**: `main` at `ac6ddd9`
**Status**: `DRAFT` → `APPROVED` → `EXECUTING` → `CLOSED`

> Authored at Phase 1 (Planning) by `principal_agent`, extracted to this path at
> Phase 3, and **committed before Phase 5 approves it**: `agents.md §2 triple_lock`
> names the approved Implementation Plan as its first lock, and a lock cannot close
> over an artifact that does not exist.
>
> Spanish is permitted in this document (`agents.md §1 user_chat`). Every other
> pipeline artifact is English.

---

## Context

El Sprint 007 cerró y se desplegó (`v0.7.0`, tag en `ac6ddd9`, PR #8 fusionado).
`export-all` recorre las 910 conversaciones de la cuenta y escribe un manifiesto
de corrida. Lo que dejó abierto no son mejoras: son **tres defectos medidos y un
fallo de proceso**, todos registrados en `docs/active_state.json` después de que
ambas puertas de la Fase 7 hubiesen aprobado.

**D1 — La enumeración pierde conversaciones en silencio.** `sweep_chat_list`
avanza el panel un `client_height` por pasada y deduplica por digest. Si la lista
se reordena a mitad del barrido — un solo mensaje entrante lo provoca — una
conversación baja por debajo de la posición ya barrida y no se ve nunca. No hay
duplicados: la pérdida es limpia. Medido contra la geometría real (899
conversaciones, ventana de 70 filas, filas de 76 px):

| Reordenamientos | Encontradas | Reproducir |
| :--- | :--- | :--- |
| 1 cada 5 lecturas | 882 / 899 | `python3 -m pytest tests/test_chat_list.py::test_a_reordering_list_makes_the_sweep_UNDERCOUNT_silently -q` |
| 1 cada 2 lecturas | 856 / 899 | mismo fichero, `ReorderingPane(every=2)` |

Lo agrava el reporte: `enumeration_complete` sigue devolviendo `true`, porque el
pie del panel **sí** se alcanzó. El booleano no distingue «vi toda la lista» de
«llegué al final de una lista que se movió debajo de mí». Es exactamente el
defecto que `ADR-0004` ya resolvió para `complete` en el fichero de exportación,
sin aplicar todavía a la enumeración.

**D2 — `sender: unknown` al 3.9%, sin diagnosticar.** 5 de 129 mensajes en la
corrida en vivo de 007, contra 0 de 513 en la de 004. O depende de la
conversación o es una regresión; no se sabe. `KI-004-A` prohíbe teorizar sobre
este DOM y ya han llegado a producción **tres hipótesis de dirección erróneas**,
la última dejando una exportación de 513 mensajes con todos los remitentes en
`unknown`. Por tanto este sprint **mide, no arregla**.

**D3 — `kind: unknown` al 9.6%.** 30 de 311 filas en la corrida 3 del probe,
frente a 6/301 en el Sprint 005 y 2/54 en la corrida 2: las muestras anteriores
subestimaban la tasa. Hay firmas capturadas para hasta 12 filas desconocidas por
chat. Misma restricción `KI-004-A`: medir primero.

**F1 — La doble puerta no entregó evidencia.** En la Fase 7 del Sprint 007 QA
(`af56a8f`) y Tester (`a90db59`) emitieron veredicto y **ninguno de los dos
entregó hallazgos**: QA devolvió solo la línea de veredicto en tres
invocaciones, dos de ellas con `tool_uses=0`; Tester ejecutó 48 llamadas de
herramienta en 12.6 min y devolvió una línea, dos veces. ~430k tokens de
subagente para veredictos sin evidencia, y el orquestador acabó reverificando
sus propias afirmaciones — la postura «el autor revisa su propio trabajo» que la
doble puerta existe para impedir. El ancla lo deja escrito: establecer si la
truncación es del canal de resultado o de los perfiles de agente **antes de
volver a despachar puertas**.

**Coste.** La sesión previa (`dfadf1f8`) recorrió 7 ciclos de contexto con
ratios `12.2 · 14.1 · 15.0 · 15.9 · 19.5 · 21.3 · 23.6` — **cuatro por encima
del límite duro de 15x** (`rules/token_economy.md §3.1`). Este sprint agrupa más
unidades que el 007, así que la escalada de coste es un riesgo declarado, no un
descubrimiento posterior. Reproducir:
`python3 .agents/scripts/session_cost.py --from-anchor --json`.

**Qué es cierto cuando esto termina.** `sweep_until_stable` recupera 899/899 bajo
reordenamiento a `every=5` de forma determinista y offline; el manifiesto declara
la enumeración como uno de tres valores en vez de un booleano que no puede
mentir hacia el lado seguro; existe un probe ejecutable que captura las firmas
DOM de las filas `unknown` de D2 y D3; y la Fase 7 se despacha con un canal de
evidencia diagnosticado o no se despacha.

---

## Design

**Decisión 1 — Barrido convergente como función nueva, no como reescritura de
`sweep_chat_list`.** Se añade `sweep_until_stable`, que repite el barrido de una
sola pasada acumulando la unión de digests y se detiene cuando **dos barridos
consecutivos no aportan ninguna conversación nueva**, o al agotar `max_sweeps`.
`sweep_chat_list` se conserva intacta como primitiva de una pasada.

*Rechazado*: reescribir `sweep_chat_list` para que converja internamente.
Habría invalidado sus once tests existentes, que documentan el comportamiento de
una pasada y siguen siendo ciertos, y habría mezclado dos responsabilidades en
una función que ya está en el límite de complejidad de `agents.md §1`.

**Decisión 2 — La convergencia NO se reporta como prueba.** Que dos barridos
coincidan es evidencia estadística, no una demostración: una conversación puede
esquivar ambos. `ADR-0004` ya estableció esta epistemología para el fichero de
exportación al mostrar que `complete: true` era inalcanzable. `ADR-0005` la
extiende a la enumeración con tres valores:

| Valor | Significado |
| :--- | :--- |
| `converged` | Se alcanzó el pie del panel y los dos últimos barridos no aportaron nada nuevo |
| `unconverged` | Se alcanzó el pie, pero los barridos seguían aportando al agotarse `max_sweeps` |
| `truncated` | Nunca se alcanzó el pie del panel (tope de pasadas) |

**Falla cerrado**: un estado no reconocido es `truncated`, nunca `converged`.

*Rechazado*: reutilizar los nombres de `ADR-0004` (`proven` / `unproven`).
`proven` sería inalcanzable aquí por la misma razón que allí, y un valor que la
implementación no puede emitir jamás es ruido en el esquema, no una garantía.

**Decisión 3 — El manifiesto sube a esquema v2, la exportación se queda en v5.**
`MANIFEST_SCHEMA_VERSION` pasa de `1` a `2`; `enumeration_complete: bool` se
sustituye por `enumeration: str` más `sweeps: int`. `writers.SCHEMA_VERSION`
(v5) **no se toca**: son dos esquemas independientes y este sprint no cambia la
forma de un fichero de chat exportado.

**Decisión 4 — D2 y D3 comparten un único probe.** Ambos defectos se observan en
la misma pasada del DOM sobre las mismas filas: `_row_sender` devuelve `unknown`
y `_row_kind` devuelve `unknown` para filas del mismo panel. Dos scripts
recorrerían WhatsApp Web dos veces para leer los mismos nodos.
`scripts/probe_unknown_rows.py` captura ambas firmas en un recorrido.

*Rechazado*: arreglar la clasificación en este sprint. `KI-004-A` lo prohíbe sin
datos, y el historial concreto de este repositorio (tres hipótesis de dirección
enviadas y erróneas) es la razón por la que la regla existe.

**Decisión 5 — F1 se resuelve antes que nada y decide la postura de la Fase 7.**
Es una unidad de diagnóstico sin código. Su resultado no es opcional: determina
si las puertas se despachan como subagentes o se ejecutan en sesión. Ir a la
Fase 7 sin haberlo respondido repetiría un gasto de ~430k tokens ya medido como
improductivo.

**Decisión 6 — El orden de ejecución protege el valor.** Bloques A → B → C → D.
Si el sprint se detiene por coste, lo que queda entregado es el defecto con
prueba determinista (B), no un probe que nadie ha corrido todavía.

---

## Work

One row per unit. One unit is one atomic commit (`RA-08`) touching **one physical
file** as its structural subject (`agents.md §2 jurisdictional_lock`).

The Work column `Assignee (proposed)` is a staffing proposal from Phase 1. Phase
4.1 (`agent_orchestrator`) is the authority that records the assignee; it may
overwrite this proposal. A Work row is not closed until `agent_assignment.md`
records it. Do not rename columns on existing `task_scope.md` files to match
this heading.

### Bloque A — Preflight (sin código; desbloquea la Fase 7)

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| A1 | `docs/sprints/008-backend-extractor/GATE_CHANNEL_DIAGNOSIS.md` | create | low | `orchestrator` | ⏳ |
| A2 | `docs/active_state.json` | modify | low | `orchestrator` | ⏳ |
| A3 | `docs/0_SYSTEM_OVERVIEW.md` | modify | low | `doc_orchestrator` | ⏳ |

- **A1** — Despachar una invocación de prueba a `qa-agent` con una instrucción que
  exija un hallazgo estructurado, y comparar lo devuelto con lo que el agente
  ejecutó. Verdicto escrito: `channel` (la truncación es del transporte de
  resultado) o `profile` (el perfil del agente no emite hallazgos). Registrar la
  postura resultante para la Fase 7 de este sprint.
- **A2** — Corregir `current_sprint.phase`, que aún dice `Branch pushed, NOT
  merged` cuando PR #8 se fusionó en `57a76b3` y se selló en `ac6ddd9`.
- **A3** — Corregir la cabecera: líneas 2-4 y 9 declaran `v0.6.0` publicado y el
  Sprint 007 «in flight» sobre `c3e827a`.

### Bloque B — D1: subconteo de enumeración (el núcleo del sprint)

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| B1 | `docs/decisions/ADR-0005-enumeration-completeness.md` | create | medium | `doc_orchestrator` | ⏳ |
| B2 | `src/whatsapp_chat_extractor/chat_list.py` | modify | high | `implementer_agent` | ⏳ |
| B3 | `tests/test_chat_list.py` | modify | medium | `implementer_agent` | ⏳ |
| B4 | `src/whatsapp_chat_extractor/manifest.py` | modify | medium | `implementer_agent` | ⏳ |
| B5 | `tests/test_manifest.py` | modify | low | `implementer_agent` | ⏳ |
| B6 | `src/whatsapp_chat_extractor/__main__.py` | modify | medium | `implementer_agent` | ⏳ |
| B7 | `tests/test_export_all.py` | modify | low | `implementer_agent` | ⏳ |
| B8 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | ⏳ |

- **B2** — Añadir `sweep_until_stable(page, *, max_passes, settle_ms, max_sweeps)`
  devolviendo un `TypedDict` con `refs`, `enumeration`, `sweeps`. Reindexar
  `ChatRef["index"]` sobre la unión final para que siga siendo contiguo y en
  orden de lista. `sweep_chat_list` no se modifica.
- **B3** — Conservar
  `test_a_reordering_list_makes_the_sweep_UNDERCOUNT_silently` sin cambios: sigue
  siendo cierto sobre la primitiva de una pasada. Añadir tests de convergencia
  sobre `sweep_until_stable` a `every=5` y `every=2`, más un test de que un panel
  que nunca alcanza el pie clasifica `truncated`.
- **B4** — `MANIFEST_SCHEMA_VERSION` `1` → `2`; sustituir `enumeration_complete`
  por `enumeration` y `sweeps`.
- **B6** — `__main__.py:266` pasa hoy `enumeration_complete=complete`; cambiar la
  llamada de enumeración a `sweep_until_stable` y propagar los campos nuevos.

### Bloque C — D2 + D3: probe de filas `unknown` (offline; la medición en vivo la corre el operador)

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| C1 | `scripts/probe_unknown_rows.py` | create | medium | `implementer_agent` | ⏳ |
| C2 | `tests/test_probe_unknown_rows.py` | create | medium | `implementer_agent` | ⏳ |
| C3 | `docs/sprints/008-backend-extractor/PROBE_UNKNOWN_ROWS_RUN.md` | create | low | `doc_orchestrator` | ⏳ |

- **C1** — Sigue el patrón operador-ejecutable ya establecido por
  `scripts/probe_chat_start.py` y `scripts/probe_chat_list.py`. Para cada fila en
  la que `_row_sender` o `_row_kind` devuelva `unknown`, volcar la firma DOM:
  clases del contenedor, `data-*` presentes, `aria-label`, presencia de
  `data-pre-plain-text`, y qué selectores conocidos fallaron. **No clasifica y no
  propone una corrección**: `KI-004-A`.
- **C3** — Se rellena con la corrida en vivo. **Unidad bloqueada por el
  operador**: requiere una sesión autenticada de WhatsApp Web, que ningún agente
  puede iniciar. Ver «Out of scope».

### Bloque D — Plataforma y deuda upstream

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| D1 | `docs/PLATFORM_HARDENING.md` | modify | low | `devops_agent` | ⏳ |
| D2 | `docs/audits/UPSTREAM_FINDING_008_BOOT_MISROUTE.md` | create | low | `rule_validator` | ⏳ |
| D3 | `docs/audits/UPSTREAM_FINDING_009_POST_CONDITION.md` | create | low | `rule_validator` | ⏳ |
| D4 | `docs/audits/UPSTREAM_FINDING_010_AUDIT_PLAN_FILTER6.md` | create | low | `rule_validator` | ⏳ |
| D5 | `docs/audits/UPSTREAM_FINDING_011_MAKEFILE_UNQUOTED.md` | create | low | `rule_validator` | ⏳ |

- **D1** — Ejecutar `/agents:harden` y registrar qué controles quedan y cuáles
  siguen bloqueados. La facturación de GitHub es externa: ver «Out of scope».
- **D2-D5** — El ancla afirma que ocho hallazgos esperan un PR al núcleo, pero
  solo existen en disco `_003` a `_007`: **cuatro no tienen fichero**. Redactarlos
  con el formato de `UPSTREAM_FINDING_004`. Bajo `RA-15`, cada uno se genericiza
  antes de salir del host; bajo `§3 jurisdiction`, el PR al núcleo se trabaja en
  un clon separado y **no** en este sprint.

---

## Dependencies

`rules/code_craft.md §7` — every dependency is permanent code you do not control.
Before adding one, check the standard library, then what is already present. The
commit that adds it must also carry `Dependency: <name> — <reason>`.

| Package | Version | Why the standard library and the existing dependencies do not suffice |
| :--- | :--- | :--- |
| None | — | El barrido convergente es lógica de conjuntos y bucles sobre la `Page` de Playwright ya presente; el probe reutiliza el arnés de `scripts/probe_chat_list.py`. |

---

## Mechanisms

| Mechanism | Deterministic or agent judgment | Invoker (`RA-16`) |
| :--- | :--- | :--- |
| Barrido convergente de la lista de chats | script (`sweep_until_stable`, criterio de parada fijo) | `wa-extract export-all` vía `__main__.py` |
| Probe de filas `unknown` | script | `human:python3 scripts/probe_unknown_rows.py` (docstring del módulo) |
| Diagnóstico del canal de puertas (A1) | agent judgment — **una sola vez, no recurrente** | `human:/agents:pipeline` Fase 7 de este sprint |

A1 es un juicio de agente y no tiene alternativa determinista, pero **no es un
mecanismo recurrente**: se ejecuta una vez para decidir una postura y no vuelve
a correr en cada sprint ni en cada commit, así que el Filtro 5 no aplica.

`RA-16 INVOCATION_COVERAGE`: no workflow, script, executable skill, hook or gate
merges without a declared, verifiable invoker, or a typed exception in
`config/invocation_exceptions.json` stating why it has none.

---

## Cost

| Field | Value | Reproduce |
| :--- | :--- | :--- |
| Delegation | `native` | `docs/active_state.json` `delegation_mode` |
| Work units | 19 | Count of rows in Work tables |
| Subagents dispatched | Decidido por A1; techo declarado **6** | `docs/sprints/008-backend-extractor/GATE_CHANNEL_DIAGNOSIS.md` |
| Prior session ratio | **23.6** (peor de 7 ciclos: 12.2 · 14.1 · 15.0 · 15.9 · 19.5 · 21.3 · 23.6) | `python3 .agents/scripts/session_cost.py --from-anchor --json` |

La sesión previa superó el límite duro de 15x en cuatro ciclos. Este plan agrupa
19 unidades, más que el Sprint 007. Mitigación declarada por adelantado: el orden
A → B → C → D deja el valor probado (B) antes que el trabajo dependiente del
operador (C) y el administrativo (D), y el criterio de aborto de coste de abajo
detiene el sprint en un límite medido en lugar de descubrirlo al final.

Soft (5×) / hard (15×) thresholds force an update to this section before new
work continues — they are not observational-only once a measurable Claude
transcript exists for this tool.

---

## Tests

**Reproduce before repairing.** A test that passes against the current tree proves
nothing about a defect claimed to exist in it.

| Check | Fails against the current tree? |
| :--- | :--- |
| `test_a_reordering_list_makes_the_sweep_UNDERCOUNT_silently` | **No** — pasa hoy y debe seguir pasando: documenta el límite de la primitiva de una pasada, que este sprint no cambia |
| `sweep_until_stable` recupera 899/899 con `ReorderingPane(every=5)` | **Yes** — la función no existe; este es el defecto D1 |
| `sweep_until_stable` recupera 899/899 con `ReorderingPane(every=2)` | **Yes** — el caso peor medido (856/899 hoy) |
| Un panel que nunca alcanza el pie clasifica `truncated`, nunca `converged` | **Yes** — no hay clasificación que ejercitar |
| El manifiesto emite `enumeration` y `sweeps` con `schema_version: 2` | **Yes** — el campo es hoy `enumeration_complete: bool` en v1 |
| Las 194 pruebas actuales siguen pasando | **No** — regresión a proteger |

---

## Verification

The exact commands, and what each must return. Read exit codes with `$?` directly;
**never through a pipe**, which reports the exit code of the last command in it.

| Command | Expected |
| :--- | :--- |
| `python3 -m pytest -q` | `$?` = `0`; ≥ 194 passed y ninguna de las actuales convertida en `xfail` o borrada |
| `python3 -m pytest tests/test_chat_list.py -q` | `$?` = `0`; incluye los tests de convergencia nuevos a `every=5` y `every=2` |
| `ruff check .` | `$?` = `0` |
| `python3 .agents/scripts/detect_drift.py` | `$?` = `0` |
| `python3 .agents/scripts/submodule_purity.py` | `$?` = `0` — ninguna escritura del host dentro de `.agents` |
| `git -C .agents status --porcelain` | Salida vacía |
| `python3 scripts/probe_unknown_rows.py --help` | `$?` = `0` — el probe es invocable sin sesión de WhatsApp |
| `python3 .agents/scripts/session_cost.py --from-anchor --json` | Registrado en la sección Cost al cierre, superado o no el umbral |

---

## Documentary impact (T5)

| Artefacto | Qué cambia |
| :--- | :--- |
| `docs/decisions/ADR-0005-enumeration-completeness.md` | Nuevo. La enumeración pasa de booleano a tres valores; declara que la convergencia no es prueba |
| `docs/architecture/EXTRACTOR_BLUEPRINT.md` | Línea 54: los campos del manifiesto sustituyen `enumeration_complete` por `enumeration` + `sweeps`; esquema de manifiesto v2 |
| `docs/walkthroughs/EXTRACTOR_WALKTHROUGH.md` | Línea 46: el subconteo deja de ser «open defect» y pasa a mitigado con la recuperación medida |
| `docs/0_SYSTEM_OVERVIEW.md` | Cabecera al Sprint 008 y `v0.7.0`; `scripts/probe_unknown_rows.py` en la tabla de topología (§6) |
| `CHANGELOG.md` | Entrada del Sprint 008 bajo `[Unreleased]` — Master Ledger, `agents.md §0` |
| `docs/active_state.json` | `enumeration_undercount` cerrado con la recuperación medida; `sender_unknown_rate` y `unknown_media` reapuntados al probe; `gate_evidence_channel` resuelto por A1 |
| `docs/audits/UPSTREAM_FINDING_008..011` | Cuatro borradores que el ancla daba por existentes y no estaban en disco |

**Measured figures.** Every number in Context / Design / Verification carries
the command that reproduces it. A figure without its command is memory, not
evidence (`021-030-program-queue.md` J6 / T5).

---

## Out of scope

| Exclusion | Why, and where it goes instead |
| :--- | :--- |
| Corregir la clasificación de `sender: unknown` y `kind: unknown` | `KI-004-A` prohíbe teorizar sobre este DOM sin datos, y tres hipótesis de dirección ya se enviaron erróneas. Destino: Sprint 009, con los datos de C1 |
| La corrida en vivo del probe (C3) | Requiere una sesión autenticada de WhatsApp Web; ningún agente puede escanear el QR. Destino: el operador ejecuta C1 y este sprint registra el resultado en C3, o C3 se cierra como no medido |
| Habilitar la facturación de GitHub Actions | Externo al repositorio y a cualquier agente. Destino: acción humana; D1 registra el bloqueo, que va por quinta ocurrencia |
| El PR al núcleo con los hallazgos upstream | `§3 jurisdiction` y `§4 feedback_upstream`: se trabaja en un clon separado, nunca como escritura dentro de `.agents`. Destino: D2-D5 dejan los borradores; el PR es un acto distinto |
| Limpiar el candado obsoleto en `.agents/docs/active_state.json` | `--takeover` ahí sería una escritura del host dentro del submódulo (`§3 strict_rule`). Destino: se corrige aguas arriba con `UPSTREAM_FINDING_008` (D2) |
| Bajar `--load-wait-ms` para acortar la corrida de ~15 h | Una sola observación no basta para ajustarlo, y el coste del error es declarar un tope que el panel no había alcanzado. Destino: sigue en `full_run_duration`, P4 |
| Tocar `writers.SCHEMA_VERSION` (v5) | Este sprint no cambia la forma de un fichero de chat exportado; solo el manifiesto |

---

## Abort criterion

The observation that stops this sprint and reverts it, decided **before** execution
starts.

**Aborto técnico (Bloque B).** Si `sweep_until_stable` **no** alcanza 899/899 con
`ReorderingPane(every=5)` dentro de `max_sweeps`, el barrido convergente no es la
corrección y el Bloque B se revierte. En ese caso no se envía una recuperación
parcial disfrazada de arreglo: se registra la recuperación medida en el ancla, se
conserva `ADR-0005` (la clasificación de tres valores es correcta con o sin la
corrección, y `unconverged` describe exactamente ese resultado) y D1 vuelve al
Sprint 009 con otro diseño. Un `every=2` que no converja **no** aborta: se
registra como el peor caso medido y se clasifica `unconverged`.

**Aborto de coste (todo el sprint).** Si el ratio de contexto de esta sesión
supera **15x** (`rules/token_economy.md §3.1`) antes de que el Bloque B esté
verificado, el sprint se cierra con el Bloque A y el Bloque B entregados, y los
Bloques C y D pasan íntegros al Sprint 009. La sesión previa llegó a 23.6x, así
que este umbral es un resultado observado, no una precaución hipotética.

**Aborto de proceso (Fase 7).** Si A1 no consigue determinar si la truncación es
de canal o de perfil, las puertas de la Fase 7 se ejecutan en sesión y el sprint
lo declara explícitamente como una desviación de la doble puerta — nunca se
despachan subagentes cuyo veredicto ya se sabe que llega sin evidencia.

---

## Approval — `triple_lock` lock 1

| Field | Value |
| :--- | :--- |
| **Approved by** | _pendiente_ |
| **Date** | _pendiente_ |
| **Plan commit at approval** | _pendiente_ |
| **Remaining locks** | Active Sprint · QA + Tester verdicts · Human OK at close |

*Phase 5 is a single attended human authorization. It MUST NOT be wrapped inside an
unattended `/loop` (`workflows/pipeline_workflow.md`, `rules/loop_governance.md`).
Any `/loop` this sprint does run — Phases 6-8 only — is governed by
`scripts/loop_guard.py start`, which fails closed.*
