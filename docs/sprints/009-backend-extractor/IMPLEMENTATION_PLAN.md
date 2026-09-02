# Implementation Plan: Sprint 009 — Que la primera corrida completa resiliente no haya que repetirla

**Canonical path**: `docs/sprints/009-backend-extractor/IMPLEMENTATION_PLAN.md`
**Branch**: `ai-sprint/009` · **Base**: `main` at `d0cdbb4`
**Status**: `DRAFT` → `APPROVED` → **`EXECUTING`** → `CLOSED`

> Authored at Phase 1 (Planning) by `principal_agent`, extracted to this path at
> Phase 3, and **committed before Phase 5 approves it**: `agents.md §2 triple_lock`
> names the approved Implementation Plan as its first lock, and a lock cannot close
> over an artifact that does not exist.
>
> Spanish is permitted in this document (`agents.md §1 user_chat`). Every other
> pipeline artifact is English.

---

## Context

El sprint tiene dos mitades y el orden entre ellas es la razón de que vayan
juntas, no una conveniencia de empaquetado.

### Mitad 1 — La reanudación (entregable 2 del roadmap)

`docs/roadmaps/docs/extractor/002-delivery-program.md:125`. Era el entregable 3
del Sprint 006 y nunca se implementó; el propio `manifest.py` lo declara en su
docstring, líneas 21-25: *«Resume is not implemented here, and the manifest is
built to allow it»*.

**El defecto, con su ruta exacta.** `cmd_export_all`
(`src/whatsapp_chat_extractor/__main__.py:242-281`) llama a `build_manifest` en
la línea 264 y a `write_manifest` en la 269, ambas **después** de que
`_export_every_chat` (línea 260) haya retornado. Esa función recorre las 910
conversaciones en un solo bucle (`__main__.py:219-234`). Si el bucle no retorna
—excepción no capturada, `kill`, `Ctrl-C`, muerte del navegador, suspensión del
Mac— la ejecución no alcanza ninguna de las dos líneas y **no se escribe nada**.

Lo que queda en disco tras esa caída son los ficheros
`data/chat_<digest>_<stamp>.json` escritos por `write_chat_export`
(`writers.py:163`). El corpus no se pierde. Lo que se pierde es el **registro de
la ejecución**: qué conversaciones fallaron y por qué, el veredicto de
enumeración de `ADR-0005`, el número de barridos, cuántas quedaron sin intentar,
y el índice `chat_id` → título, irrecuperable porque el digest es de una sola
dirección (`writers.py:96`).

**La magnitud.** Una ejecución de cuenta completa dura **~15 horas** sobre
**910 conversaciones** enumeradas en vivo el 2026-08-31
(`docs/roadmaps/docs/extractor/002-delivery-program.md:18`, fila P3b: *«3
exported, 0 failed, 907 skipped of 910»* y *«A whole-account run is ~15
hours»*). Una caída en la hora 12 destruye el registro de ~700 conversaciones ya
exportadas y obliga a repetir las 15 horas completas.

La cifra **899** que aparece en `CHANGELOG.md` `[0.8.0]` y en `manifest.py:3` es
distinta y no debe confundirse con la anterior: es el tamaño del fixture contra
el que el Sprint 008 midió la recuperación de `sweep_until_stable`, y era también
lo que un barrido único llegaba a ver de una cuenta de 910
(`CHANGELOG.md:136-139`). Este sprint no toca ninguna de las dos.

### Mitad 2 — El contrato del corpus (esquema v6)

**Por qué en este sprint y no en el siguiente.** El Sprint 009 existe para que
la corrida de 15 horas sobreviva. Lo que ocurre inmediatamente después de que
aterrice es una corrida de cuenta completa que escribe **910 ficheros de
conversación**. Cada campo ausente en ese momento cuesta otras 15 horas
retrofitarlo sobre una cuenta viva cuyo contenido habrá cambiado. Este es el
último momento en que arreglar el esquema es barato.

`ADR-0001` fija el consumidor: *«so a separate AI pipeline can later study
requests, behaviour, and sentiment»*. Contra esos tres objetivos el esquema v5
tiene cuatro carencias medibles:

| # | Carencia | Evidencia | Consecuencia para el consumidor |
| :--- | :--- | :--- | :--- |
| 1 | `message_id` se calcula y se descarta | `HarvestedRow` lo lleva (`history.py:72-79`); `MessageAccumulator.consolidate` construye el `MessageRecord` sin él (`history.py:166-179`) | Ningún mensaje es re-identificable entre dos exportaciones: sin re-exportación incremental, sin deduplicación entre ejecuciones, sin cita estable |
| 2 | `timestamp` es la cadena renderizada, no tiempo | `_row_timestamp` devuelve `[HH:MM, D/M/YYYY]` de `data-pre-plain-text`, o solo `HH:MM` del fallback `msg-meta`, o `""` (`export_one.py:655-680`) | Sin latencia de respuesta, sin patrones horarios, sin ordenación temporal entre chats. `D/M` vs `M/D` es indistinguible sin conocer el locale |
| 3 | El locale del navegador no se fija ni se registra | `launch_persistent_context` no pasa `locale` ni `timezone_id` (`session.py:67-72`) | Hace que la carencia 2 sea **irreparable a posteriori**: los ficheros ya escritos no dicen bajo qué formato se renderizaron |
| 4 | `passes_used` no llega al fichero | Está en `HarvestResult` (`history.py:94`) y no en `ChatExport` (`writers.py:68-75`) | Se pierde el rastro de cuánto se esforzó la cosecha, que es el contexto de `completeness` |

Las cuatro son **aditivas**: ningún campo existente cambia de significado, y
`complete`, `completeness` y `stopped_reason` quedan intactos.

**Qué es cierto cuando el sprint esté hecho.** Una ejecución interrumpida en
cualquier punto deja un diario que permite reconstruir el manifiesto y relanzar
`export-all` sin reabrir ninguna conversación ya exportada; y cada fichero de
conversación que esa ejecución escriba lleva identidad de mensaje, tiempo
normalizado, y constancia del locale bajo el que se leyó.

**Reproducción de los defectos**: `python3 -m pytest tests/ -k "resume or journal
or timestamp"` falla hoy con `no tests ran`.

---

## Design

### D1 — Diario append-only en NDJSON, no reescritura del manifiesto

La alternativa evidente es reescribir `run_manifest_<stamp>.json` entero tras
cada conversación. Se rechaza por dos razones:

1. **Coste cuadrático.** El manifiesto crece hasta 910 entradas; reescribirlo
   910 veces escribe 414.505 entradas en total.
2. **La reescritura es la ventana de corrupción.** `Path.write_text` trunca
   antes de escribir. Una caída durante la reescritura 700 deja el único fichero
   que guarda el registro truncado a cero bytes — se pierde exactamente lo que
   el mecanismo existía para conservar.

Un diario NDJSON invierte ambas: cada conversación cuesta una línea, y una caída
a mitad de línea deja una última línea incompleta que el lector descarta,
conservando las 699 anteriores. El lector **debe** descartar una línea final no
parseable en lugar de abortar; esa es la condición de fallo real.

Durabilidad: tras cada `write`, `flush()` y `os.fsync(fileno)`. Sin `fsync` un
`kill -9` conserva los datos (quedan en el buffer del sistema operativo), pero
un corte de corriente no. 910 `fsync` sobre 15 horas es coste despreciable
frente a una conversación que tarda ~60 s.

### D2 — `run_id` acuñado al inicio, no al escribir

Hoy el sello temporal se genera tres veces con tres llamadas independientes a
`datetime.now(UTC)`: `write_manifest` (`manifest.py:214`), `write_chat_index`
(`manifest.py:251`) y `write_chat_export` (`writers.py:160`). Los tres ficheros
de una misma ejecución pueden llevar sellos distintos, y ninguno identifica la
ejecución.

Se acuña un `run_id` una sola vez al arrancar `cmd_export_all` y se pasa al
diario, al manifiesto y al índice. `--resume` lo toma como argumento; sin
identidad estable no hay nada que nombrar al reanudar. `write_chat_export` **no**
cambia de nombre de fichero: rompería a los lectores existentes y no hace falta.

### D3 — Reanudar re-enumera; no confía en los refs del diario

Un `ref` del diario apunta a una posición y un digest capturados hasta 15 horas
antes. La lista de chats se reordena con cada mensaje entrante — es la causa del
defecto que arregló `ADR-0005`. Reutilizar esos refs abriría conversaciones
equivocadas, que es lo que `H-001` prohíbe.

`--resume` ejecuta `sweep_until_stable` de nuevo y usa el diario **solo** para
el conjunto de `chat_id` con resultado `exported`, que omite. El veredicto de
enumeración del manifiesto reanudado es el de su propio barrido, nunca heredado.

Consecuencia aceptada: las conversaciones aparecidas entre la caída y la
reanudación se exportan; las desaparecidas constan como no encontradas. Una
reanudación es una ejecución nueva que reutiliza trabajo, no la continuación de
la anterior.

### D4 — `recover` es un subcomando aparte, no un efecto de `--resume`

Reconstruir el manifiesto de una ejecución muerta y relanzar la exportación son
necesidades distintas: la primera es forense y no toca el navegador; la segunda
cuesta horas. Fundirlas obligaría a abrir WhatsApp Web para responder «¿qué
llegó a hacer aquella ejecución?». `recover` lee un diario y escribe el
manifiesto, sin Playwright.

Las conversaciones enumeradas ausentes del diario se registran con `skipped` y
razón `run ended before this conversation`, distinguible de `beyond --limit`.
`manifest.py:44-46` ya define `OUTCOME_SKIPPED` con esa semántica: *«Enumerated,
never attempted»*.

### D5 — El índice de títulos sigue tras `--write-index`, en diario aparte

`ADR-0001` prohíbe nombres reales en `data/` por defecto, y `manifest.py:8-19`
mantiene el índice como fichero separado por esa razón. El diario de resultados
**no lleva títulos**. Con `--write-index`, y solo entonces, se escribe un segundo
diario `data/chat_index_<run_id>.ndjson` con la misma disciplina de append.

### D6 — Módulos nuevos, no crecimiento de los ficheros ya grandes

`__main__.py` tiene 421 líneas y `export_one.py` 681, y ambos arrastran
violaciones de complejidad que el roadmap registra
(`002-delivery-program.md:128`). `agents.md §1` fija `max_lines_per_func` en 50 y
`max_indentation` en 3. El diario vive en `journal.py` y el parseo de tiempo en
`timestamps.py`; los ficheros grandes solo los llaman.

**`export_one.py` no se toca en este sprint.** `HarvestedRow` ya lleva
`message_id` y `collect_visible_rows` ya lo rellena, así que la carencia 1 se
arregla enteramente en `history.py`. Dejar intacto el fichero de 681 líneas más
frágil a cambios de DOM es deliberado.

### D7 — Fijar el locale, **registrar** la zona horaria

Son dos decisiones distintas y se resuelven distinto a propósito.

**El locale se fija** a `es-ES` por defecto, vía el parámetro `locale` de
`launch_persistent_context`. Esto no cambia el comportamiento actual: es el
locale que el operador ya tiene, y `es-ES` renderiza `D/M/YYYY`, que es
exactamente lo que documenta el docstring de `_row_timestamp`
(`export_one.py:658`). **Pinta el comportamiento vigente en lugar de alterarlo**,
y lo vuelve conocido por construcción en vez de inferido. Verificado que no
rompe la cosecha: `LOAD_EARLIER_PATTERN` empareja etiquetas en ES y EN
(`export_one.py:380-381`), y `PRE_PLAIN_NAME_PATTERN`, `SPEAKER_LABEL_PATTERN` y
el regex del timestamp son independientes del idioma.

**La zona horaria se lee, no se impone.** Forzar `timezone_id` cambiaría las
horas que el operador ve respecto a todo lo exportado hasta hoy. En su lugar se
resuelve la del navegador con
`page.evaluate("Intl.DateTimeFormat().resolvedOptions().timeZone")` y se
**registra** en el payload. `--timezone` permite imponerla explícitamente cuando
el operador lo decida; sin la bandera, no se decide nada, se constata.

Registrar es siempre seguro; imponer es una decisión, y ninguna decisión sobre la
zona horaria del negocio es mía.

### D8 — `timestamp_iso` **junto al** crudo, jamás en su lugar

`MessageRecord` conserva `timestamp` tal cual y gana `timestamp_iso`. El crudo es
la evidencia: si el parseo resulta estar mal, se puede rehacer sobre los ficheros
ya escritos sin volver a WhatsApp Web. Sustituirlo destruiría esa posibilidad.

`timestamp_iso` es `""` cuando la fila no da fecha — el fallback `msg-meta` de
`export_one.py:673-679` devuelve solo `HH:MM`. Vacío, nunca una fecha inventada
a partir del día de la exportación: es la misma disciplina de `unknown` que
`_row_kind` aplica en `export_one.py:555-557` bajo `KI-004-A`.

La fracción de filas sin fecha **no está medida**. El esquema v6 la vuelve
medible sin una corrida en vivo: `counts` del `ChatExport` incluye cuántos
mensajes quedaron sin `timestamp_iso`, así que la primera corrida completa la
reporta por sí sola.

### D9 — Esquema v6 aditivo, y ningún reescrito de los ficheros v5

Ningún campo de v5 cambia de nombre ni de significado. Los ficheros v5 ya
exportados quedan con timestamps de locale desconocido y sin `message_id`, y
**no se reparan retroactivamente**: no existe registro de bajo qué locale se
renderizaron, así que cualquier reparación sería una conjetura. Se documenta en
`ADR-0007` y se acepta.

### D10 — Dos ADR, no uno

`ADR-0006` cubre el diario y la reanudación; `ADR-0007` cubre el contrato del
corpus. Son decisiones sobre objetos distintos —el registro de la ejecución y el
payload de la conversación— con consumidores distintos. Fundirlas en un ADR
haría ilegible cuál supersede a cuál cuando una de las dos evolucione.

---

## Work

One row per unit. One unit is one atomic commit (`RA-08`) touching **one physical
file** as its structural subject (`agents.md §2 jurisdictional_lock`).

The Work column `Assignee (proposed)` is a staffing proposal from Phase 1. Phase
4.1 (`agent_orchestrator`) is the authority that records the assignee; it may
overwrite this proposal. A Work row is not closed until `agent_assignment.md`
records it.

### Bloque A-C — Reanudación

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| A1 | `src/whatsapp_chat_extractor/journal.py` | create | medium | `implementer_agent` | ⏳ |
| A2 | `tests/test_journal.py` | create | low | `implementer_agent` | ⏳ |
| B1 | `src/whatsapp_chat_extractor/manifest.py` | modify | medium | `implementer_agent` | ⏳ |
| B2 | `tests/test_manifest.py` | modify | low | `implementer_agent` | ⏳ |
| C1 | `src/whatsapp_chat_extractor/__main__.py` | modify | high | `implementer_agent` | ⏳ |
| C2 | `tests/test_export_all.py` | modify | low | `implementer_agent` | ⏳ |
| C3 | `tests/test_resume.py` | create | low | `implementer_agent` | ⏳ |

### Bloque E — Contrato del corpus (esquema v6)

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| E1 | `src/whatsapp_chat_extractor/session.py` | modify | medium | `implementer_agent` | ⏳ |
| E2 | `src/whatsapp_chat_extractor/timestamps.py` | create | medium | `implementer_agent` | ⏳ |
| E3 | `tests/test_timestamps.py` | create | low | `implementer_agent` | ⏳ |
| E4 | `src/whatsapp_chat_extractor/history.py` | modify | medium | `implementer_agent` | ⏳ |
| E5 | `src/whatsapp_chat_extractor/writers.py` | modify | high | `implementer_agent` | ⏳ |
| E6 | `tests/test_history.py` | modify | low | `implementer_agent` | ⏳ |
| E7 | `tests/test_writers.py` | modify | low | `implementer_agent` | ⏳ |

### Bloque D — Documentación

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| D1 | `docs/decisions/ADR-0006-run-journal-and-resume.md` | create | low | `doc_orchestrator` | ⏳ |
| D2 | `docs/decisions/ADR-0007-corpus-contract-v6.md` | create | low | `doc_orchestrator` | ⏳ |
| D3 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | ⏳ |
| D4 | `docs/0_SYSTEM_OVERVIEW.md` | modify | low | `doc_orchestrator` | ⏳ |

**Contenido exigible por unidad** (`agents.md §1 unambiguous_action`):

| # | Operación y criterio de terminación |
| :--- | :--- |
| A1 | Define `JOURNAL_SCHEMA_VERSION`, `open_journal(run_id, data_dir)`, `write_header(...)`, `append_outcome(...)` y `read_journal(path)`. Cada append llama a `flush()` y `os.fsync()`. `read_journal` descarta una última línea no parseable y emite `logger.warning` con el número de línea; ninguna otra línea inválida se tolera. Termina cuando `ruff check .` sale `0` y ninguna función supera 50 líneas ni 3 niveles de indentación. |
| A2 | Cubre: cabecera y tres resultados releídos en orden; última línea truncada a mitad de un carácter UTF-8 descartada conservando las anteriores; fichero de cero bytes devuelve cabecera `None` y lista vacía sin lanzar; `os.fsync` invocado una vez por append, verificado con `monkeypatch`. Termina cuando los cuatro casos pasan. |
| B1 | Añade `manifest_from_journal(header, outcomes, enumerated_refs)` que devuelve un `RunManifest`, marcando `skipped` con razón `run ended before this conversation` cada `chat_id` enumerado ausente del diario. Añade el parámetro `run_id` a `write_manifest` y `write_chat_index`, sustituyendo la llamada interna a `datetime.now`. Reescribe el docstring del módulo, líneas 21-25, que hoy afirma que la reanudación no está implementada. Termina cuando `tests/test_manifest.py` pasa. |
| B2 | Cubre: reconstrucción desde diario parcial produce los `skipped` esperados; `run_id` explícito determina el nombre del fichero; `summarize` cuenta los `skipped` reconstruidos. Termina cuando los tres casos pasan. |
| C1 | Acuña `run_id` al inicio de `cmd_export_all`; abre el diario y escribe la cabecera **después** de `sweep_until_stable` y **antes** de la primera conversación; hace append de cada resultado dentro del bucle de `_export_every_chat`; añade `--resume <run_id>`, `--timezone <tz>` y el subcomando `recover --run-id <run_id>` que no importa Playwright; pasa `passes_used`, `source_locale` y `source_timezone` a `build_export` en la línea 188. Termina cuando `ruff check .` sale `0` y ninguna función nueva supera 50 líneas. |
| C2 | Añade el caso que hoy no existe: una excepción en la conversación 2 de 3 deja un diario del que `manifest_from_journal` reconstruye 1 `exported` y 2 `skipped`. Termina cuando ese caso falla contra el árbol actual y pasa contra el modificado. |
| C3 | Cubre la orquestación de `--resume`: un diario con 2 de 3 `exported` produce una ejecución que llama a `open_chat_by_digest` exactamente una vez, y el manifiesto final contiene las 3 conversaciones. Sin navegador, con el patrón de `monkeypatch` de `tests/test_export_all.py`. Termina cuando ese caso pasa. |
| E1 | Añade `locale="es-ES"` a `launch_persistent_context` y expone `DEFAULT_LOCALE` como constante del módulo. Añade `resolve_timezone(page)` que devuelve `Intl.DateTimeFormat().resolvedOptions().timeZone` vía `page.evaluate`, y `""` si la evaluación falla. No fija `timezone_id` salvo que el llamante pase uno. Termina cuando `ruff check .` sale `0` y `tests/` sigue en verde. |
| E2 | Define `parse_rendered(raw, *, locale)` que convierte `"HH:MM, D/M/YYYY"` en ISO-8601 sin zona (`YYYY-MM-DDTHH:MM`) y devuelve `""` para cualquier entrada sin fecha, vacía o no emparejable. No infiere el día a partir de la fecha de exportación. Termina cuando `tests/test_timestamps.py` pasa. |
| E3 | Cubre: `"14:32, 3/9/2026"` bajo `es-ES` da `2026-09-03T14:32`; `"14:32"` da `""`; `""` da `""`; una cadena de cuerpo de mensaje da `""`; el día 13 o mayor confirma que el orden es `D/M` y no `M/D`. Termina cuando los cinco casos pasan. |
| E4 | `MessageAccumulator.consolidate` deja de descartar `message_id` (líneas 166-179) y lo escribe en el `MessageRecord`; añade `timestamp_iso` llamando a `timestamps.parse_rendered`. Mantiene el `row.get("kind", "text")` que permite reproducir fixtures v3. Termina cuando `tests/test_history.py` pasa. |
| E5 | Sube `SCHEMA_VERSION` a `6`. `MessageRecord` gana `message_id` y `timestamp_iso`. `ChatExport` gana `passes_used`, `source_locale`, `source_timezone` y `undated_messages` (cuántos mensajes quedaron sin `timestamp_iso`). `build_export` acepta los tres primeros como argumentos y deriva el cuarto. Documenta v6 en el docstring de `ChatExport` con el mismo formato que v3, v4 y v5. Termina cuando `tests/test_writers.py` pasa. |
| E6 | Cubre: `message_id` sobrevive a `consolidate` y coincide con el de `HarvestedRow`; dos filas con el mismo `message_id` siguen deduplicándose; `timestamp_iso` vacío no impide consolidar. Termina cuando los tres casos pasan. |
| E7 | Cubre: un export v6 lleva los cuatro campos nuevos; `undated_messages` cuenta los `timestamp_iso` vacíos; `complete` sigue derivándose de `completeness` y no de un argumento. Termina cuando los tres casos pasan. |
| D1 | Registra las decisiones D1 a D6 como ADR, con el formato de `docs/decisions/ADR-0005-enumeration-completeness.md`. Termina cuando el fichero existe y `docs/0_SYSTEM_OVERVIEW.md` lo enlaza. |
| D2 | Registra las decisiones D7 a D10 como ADR, incluida explícitamente la de `§D9`: los ficheros v5 no se reparan. Declara qué supersede de `ADR-0001` y qué no. Termina cuando el fichero existe y `docs/0_SYSTEM_OVERVIEW.md` lo enlaza. |
| D3 | Añade `journal.py` y `timestamps.py` a la tabla de componentes; describe el ciclo diario → manifiesto y el contrato v6. Termina cuando ninguna ruta declarada en el blueprint falta en el árbol. |
| D4 | Añade `journal.py` y `timestamps.py` a la tabla §6; enlaza `ADR-0006` y `ADR-0007`; y **corrige la línea 9**, que hoy declara `Released: v0.7.0` e `In flight: Sprint 008` mientras el Master Ledger ya selló `v0.8.0` y `v0.8.1`. Termina cuando la línea 9 nombra `v0.8.1` y el Sprint 009. |

---

## Dependencies

`rules/code_craft.md §7` — every dependency is permanent code you do not control.

| Package | Version | Why the standard library and the existing dependencies do not suffice |
| :--- | :--- | :--- |
| None | — | El diario usa `json`, `os` y `pathlib`; el parseo de tiempo usa `re` y `datetime`. Todos ya importados en el paquete. NDJSON no necesita biblioteca: es una línea `json.dumps` por registro, y el formato de fecha es uno solo y conocido (`§D7`), no un problema general de locales que justifique `babel` o `dateutil`. |

---

## Mechanisms

| Mechanism | Deterministic or agent judgment | Invoker (`RA-16`) |
| :--- | :--- | :--- |
| Append de un resultado por conversación al diario | script — `journal.append_outcome`, sin criterio de agente | `src/whatsapp_chat_extractor/__main__.py` `_export_every_chat` |
| Reconstrucción del manifiesto desde un diario | script — `manifest.manifest_from_journal` | `src/whatsapp_chat_extractor/__main__.py` `cmd_recover`, subcomando `recover` |
| Omisión de conversaciones ya exportadas al reanudar | script — diferencia de conjuntos sobre `chat_id` | `src/whatsapp_chat_extractor/__main__.py` `_export_every_chat` bajo `--resume` |
| Normalización del timestamp renderizado a ISO-8601 | script — `timestamps.parse_rendered`, formato único y conocido | `src/whatsapp_chat_extractor/history.py` `MessageAccumulator.consolidate` |
| Resolución de la zona horaria del navegador | script — `session.resolve_timezone`, una evaluación JS, sin criterio de agente | `src/whatsapp_chat_extractor/__main__.py` `cmd_export_all` |

`RA-16 INVOCATION_COVERAGE`: no workflow, script, executable skill, hook or gate
merges without a declared, verifiable invoker, or a typed exception in
`config/invocation_exceptions.json` stating why it has none. Ninguno de los cinco
mecanismos es un instrumento del framework: son funciones del paquete del host,
invocadas por el CLI que las contiene.

---

## Cost

| Field | Value | Reproduce |
| :--- | :--- | :--- |
| Delegation | `native` | `docs/active_state.json` `delegation_mode` |
| Work units | **19** (18 approved + `E8` added during Phase 6) | Count of rows in Work tables (7 + 8 + 4). `E8` = `tests/test_completeness.py`, which asserts the schema literal and was missed at Phase 1; rationale in `task_scope.md` § Amendment during Phase 6 |
| Subagents dispatched | 0 planned at Phase 1 | Phase 4.1 `agent_assignment.md` is the authority |
| Ratio at Phase 1 open | 4.1 | `python3 .agents/scripts/session_cost.py --from-anchor --json` |
| **Ratio at Phase 3 close** | **7.8** (peak 192.467) | idem, tras los commits de Fase 3 |

**Umbral blando de 5× cruzado durante la Fase 1, y actualizado aquí antes de
continuar** (`rules/token_economy.md` §3). El umbral duro de 15× no está
cruzado.

Qué lo movió, para que la Fase 6 no repita el patrón sin saberlo: el ratio pasó
de 4.1 a 7.8 en una sola fase porque el alcance se renegoció **después** de
redactar el plan. El análisis del corpus leyó `writers.py`, `history.py`,
`session.py` y dos esqueletos AST, y la ampliación a v6 obligó a reescribir el
documento entero en vez de parchearlo. Fue trabajo útil —descubrió cuatro
carencias del esquema y el momento correcto para arreglarlas— pero el coste
pertenece a la renegociación de alcance, no a la planificación.

Consecuencia operativa para la Fase 6: las 19 unidades se despachan en contexto
fresco por unidad (`jurisdictional_lock` ya lo exige por fichero), y **no** se
reabre el alcance dentro de la ejecución. Una tercera ampliación de este sprint
se rechaza y va al Sprint 010.

---

## Tests

**Reproduce before repairing.** A test that passes against the current tree proves
nothing about a defect claimed to exist in it.

| Check | Fails against the current tree? |
| :--- | :--- |
| Una excepción en la conversación 2 de 3 deja un diario del que se reconstruye el manifiesto (C2) | **Yes** — es el defecto: hoy no se escribe nada y no existe diario |
| `--resume` con 2 de 3 ya exportadas abre exactamente 1 conversación (C3) | **Yes** — hoy `--resume` no existe |
| Una última línea truncada no invalida el diario (A2) | **Yes** — hoy no existe `journal.py` |
| `message_id` sobrevive a `consolidate` (E6) | **Yes** — hoy se descarta en `history.py:166-179` |
| `"14:32, 3/9/2026"` da `2026-09-03T14:32`, y `"14:32"` da `""` (E3) | **Yes** — hoy no existe `timestamps.py` |
| Un export lleva `source_locale` y `undated_messages` (E7) | **Yes** — hoy `ChatExport` no tiene esos campos |
| Un fallo de una conversación no termina la ejecución (`tests/test_export_all.py:78`) | **No** — regresión a proteger, `§D3` del Sprint 006 |
| El límite registra el resto como `skipped` (`tests/test_export_all.py:110`) | **No** — regresión a proteger |
| La enumeración parcial sale de la ejecución (`tests/test_export_all.py:136`) | **No** — regresión a proteger, `ADR-0005` |
| Dos filas con el mismo `message_id` siguen deduplicándose (E6) | **No** — regresión a proteger: `message_id` pasa a escribirse, y debe seguir sirviendo de clave |
| `complete` se deriva de `completeness`, nunca se acepta como argumento (E7) | **No** — regresión a proteger, `ADR-0004` |

---

## Verification

Read exit codes with `$?` directly; **never through a pipe**.

| Command | Expected |
| :--- | :--- |
| `ruff check .` | exit `0` |
| `python3 -m pytest -q` | exit `0`, cero fallos y cero regresiones sobre los 11 ficheros de test existentes |
| `python3 -m pytest tests/test_journal.py tests/test_resume.py tests/test_timestamps.py -q` | exit `0` |
| `python3 -c "from whatsapp_chat_extractor.writers import SCHEMA_VERSION; assert SCHEMA_VERSION == 6"` | exit `0` |
| `git status --porcelain data/` | vacío — ninguna conversación exportada llega al índice de git |
| `git -C .agents status --porcelain` | vacío (`agents.md §3 jurisdiction`) |
| `python3 .agents/scripts/check_task_scope.py --sprint-dir docs/sprints/009-backend-extractor` | exit `0` |
| `python3 .agents/scripts/check_gate_log.py --sprint-dir docs/sprints/009-backend-extractor` | exit `0` |

---

## Documentary impact (T5)

| Artefacto | Qué cambia |
| :--- | :--- |
| `docs/decisions/ADR-0006-run-journal-and-resume.md` | Se crea: formato del diario, identidad de ejecución, y la decisión de que reanudar re-enumera |
| `docs/decisions/ADR-0007-corpus-contract-v6.md` | Se crea: los cuatro campos nuevos, el locale fijado y la zona horaria registrada, y la decisión de no reparar los ficheros v5 |
| `docs/architecture/EXTRACTOR_BLUEPRINT.md` | Se añaden `journal.py` y `timestamps.py`; se describe el contrato v6 |
| `docs/0_SYSTEM_OVERVIEW.md` | Tabla §6: filas de `journal.py` y `timestamps.py`; enlaces a `ADR-0006` y `ADR-0007`; corrección de la línea 9, hoy sellada en `v0.7.0` / Sprint 008 en vuelo |
| `docs/roadmaps/docs/extractor/002-delivery-program.md` | Fila P5: el entregable 2 pasa de `PROPOSED` a su estado de cierre con sello de fecha (`H-002` se abrió por no haberlo hecho en el Sprint 008), y se registra que el contrato del corpus se adelantó a este sprint |
| `CHANGELOG.md` | Entrada de sprint bajo `[Unreleased]` en el cierre (`RA-05`), incluyendo la rotura de esquema v5 → v6 |
| `src/whatsapp_chat_extractor/manifest.py` | Docstring del módulo, líneas 21-25: deja de afirmar que la reanudación no está implementada |
| `src/whatsapp_chat_extractor/writers.py` | Docstring de `ChatExport`: entrada de v6 con el mismo formato narrativo que v3, v4 y v5 |

**Measured figures.**

| Cifra | Comando o fuente que la reproduce |
| :--- | :--- |
| 910 conversaciones, ~15 h por ejecución | `docs/roadmaps/docs/extractor/002-delivery-program.md:18` (fila P3b, medición en vivo del 2026-08-31) |
| 899 conversaciones (fixture del Sprint 008, **no** la cuenta en vivo) | `CHANGELOG.md:34-38`; `src/whatsapp_chat_extractor/manifest.py:3` |
| 421 líneas en `__main__.py`, 681 en `export_one.py` | `wc -l src/whatsapp_chat_extractor/__main__.py src/whatsapp_chat_extractor/export_one.py` |
| 414.505 escrituras de entrada bajo reescritura completa (`§D1`) | `python3 -c "print(sum(range(1, 911)))"` |
| `kind: unknown` 9,6 % (30/311); `sender: unknown` 3,9 % (5/129) | `docs/roadmaps/docs/extractor/002-delivery-program.md:124`, corrida en vivo de #007 |
| Ratio de sesión previa 4.1 | `python3 .agents/scripts/session_cost.py --from-anchor --json` |

---

## Out of scope

| Exclusion | Why, and where it goes instead |
| :--- | :--- |
| Ejecutar `scripts/probe_unknown_rows.py` en vivo y clasificar las tasas `unknown` | Entregable 1 del Sprint 009 en el roadmap. Exige una sesión de WhatsApp Web con el operador presente. Se mantiene en `002-delivery-program.md:124` |
| `chat_kind` (`direct`/`group`) y el rol del hablante en grupos | La lectura de `sender_from_speaker_label` (`export_one.py:631-635`) indica que en un grupo el título es el nombre del grupo, así que toda etiqueta ≠ título devuelve `me`. **No está medido**: no hay test de grupos ni observación en vivo. Corregir sin medir es el error contra el que se escribió `KI-004-A`. Va a una sonda, junto al entregable 1 |
| Respuestas citadas, reacciones y reenvíos | `grep -rn "quoted\|reply\|reaction\|forward" src/` no devuelve nada. Exigen sondas DOM nuevas, del tipo de `probe_unknown_rows.py`. Trabajo de sonda, no de esquema |
| Reparar los ficheros v5 ya exportados | `§D9`: no consta bajo qué locale se renderizaron, así que cualquier reparación sería conjetura. Documentado en `ADR-0007`, no programado |
| Reintentar automáticamente una conversación fallida | `manifest.py:23-25` lo excluyó en el Sprint 007 con su razón intacta: reintentar sin haber medido por qué falla es adivinar cuántas veces adivinar. Depende del entregable 1 |
| Las 5 violaciones de complejidad preexistentes en `export_one.py` y `__main__.py` | Arrastradas, no programadas (`002-delivery-program.md:128`). Este sprint se compromete a no añadir ninguna, no a retirar las existentes |
| Hueco de test `F-4` (condición de salida de `cmd_export_all`) | Exige un arnés de Playwright que este sprint no construye (`002-delivery-program.md:127`). La Puerta 2 del Sprint 008 lo arrastró aquí; se vuelve a arrastrar, y esta vez con su razón escrita: `C1` toca `cmd_export_all`, pero el arnés es una unidad de trabajo propia y no un efecto colateral de añadir `--resume` |
| Hueco de test `F-6` — `enumeration` es un `str` sin validar | Arrastrado a este sprint por la Puerta 2 del Sprint 008 junto a `F-4`. `docs/sprints/008-backend-extractor/PHASE_REGISTER.md:72` lo clasificó: *«el clasificador es su único productor; un validador es una decisión de diseño, no un arreglo»*. La unidad `B1` toca `manifest.py` y podría alojarlo, pero introducir una decisión de diseño no medida en un sprint ya ampliado una vez es exactamente la deriva que `§D9` evita en el otro bloque. Va al Sprint 010 junto al contrato del corpus, **nombrado aquí para que no se pierda una segunda vez** |
| Renombrar los ficheros `data/chat_<digest>_<stamp>.json` para llevar el `run_id` | Rompería a todo lector existente del corpus y no hace falta: el diario correlaciona por `chat_id` |
| La contribución al núcleo por el defecto de `session_start.py` en modo submódulo | **Ya registrada**, no pendiente: `docs/audits/UPSTREAM_FINDING_004_SESSION_START_BOOT_ROOT.md` (2026-08-29) y `_008_BOOT_MISROUTE.md`. `agents.md §3 strict_rule` prohíbe corregirlo desde el host. Lo único que este sprint aporta es una línea de recurrencia en esos borradores: ambos se observaron contra el pin `v4.23.0` y persisten en `v4.24.0` |
| La contribución al núcleo por el `on_commit.py` duplicado en `PreToolUse` | **Ya registrada**: `docs/audits/UPSTREAM_FINDING_003_PRETOOLUSE_ON_COMMIT.md` (2026-08-27), que cita la misma cadena de comando no bloqueante. Misma aportación: recurrencia bajo `v4.24.0` |

---

## Abort criterion

Se aborta el sprint y se revierte `ai-sprint/009` si se observa cualquiera de
estas tres condiciones:

1. **El diario no sobrevive a la caída que justifica el sprint.** Si el caso C2
   —excepción en la conversación 2 de 3— no consigue reconstruir el manifiesto
   desde el diario tras tres rondas de corrección, el mecanismo no resuelve el
   problema que motivó el sprint.
2. **La reanudación reabre una conversación ya exportada.** Si el caso C3 mide
   más de una llamada a `open_chat_by_digest` con 2 de 3 ya exportadas, la
   reanudación no ahorra las 15 horas y añade riesgo de `H-001` —abrir la
   conversación equivocada— sin contrapartida.
3. **Fijar el locale altera la cosecha.** Si `tests/` deja de estar en verde tras
   la unidad E1, o si el emparejador de «cargar mensajes anteriores» deja de
   encontrar su control, el bloque E se revierte **entero** y el sprint continúa
   solo con la reanudación. El bloque E existe para que la primera corrida
   completa no haya que repetirla; un bloque E que pone en riesgo esa corrida se
   contradice a sí mismo.

Dos observaciones **no** abortan: que la reanudación exporte conversaciones
llegadas después de la caída es comportamiento declarado en `§D3`; y que
`timestamp_iso` quede vacío en una fracción de las filas es comportamiento
declarado en `§D8`, medido por `undated_messages`, no un fallo.

---

## Approval — `triple_lock` lock 1

| Field | Value |
| :--- | :--- |
| **Approved by** | `GstMirabal` (operator), attended, in session `20260902T085030Z-72792` |
| **Date** | 2026-09-02 |
| **Plan commit at approval** | `8203712` |
| **Gates at approval** | `audit_plan.py` exit `0` · `check_task_scope.py` exit `0` · `check_forge_ladder.py` exit `0` |
| **Status** | `APPROVED` → Phase 6 Execution |
| **Remaining locks** | Active Sprint ✅ · QA + Tester verdicts ⏳ Phase 7 · Human OK at close ⏳ Phase 8 |

*Phase 5 is a single attended human authorization. It MUST NOT be wrapped inside an
unattended `/loop` (`workflows/pipeline_workflow.md`, `rules/loop_governance.md`).
Any `/loop` this sprint does run — Phases 6-8 only — is governed by
`scripts/loop_guard.py start`, which fails closed.*
