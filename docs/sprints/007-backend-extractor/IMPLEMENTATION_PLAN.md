# Implementation Plan: Sprint 007 — P3b «All chats» + ADR-0004

**Canonical path**: `docs/sprints/007-backend-extractor/IMPLEMENTATION_PLAN.md`
**Branch**: `ai-sprint/007` · **Base**: `main` at `c3e827a` (v0.6.0)
**Status**: `DRAFT` → `APPROVED` → `EXECUTING` → `CLOSED`

> Autorizado en Fase 1 (Planning) por `principal_agent`, extraído a esta ruta en
> Fase 3 y **commiteado antes de que la Fase 5 lo apruebe**: `agents.md §2
> triple_lock` nombra el Implementation Plan aprobado como su primer candado, y un
> candado no puede cerrarse sobre un artefacto que no existe.
>
> Español permitido en este documento (`agents.md §1 user_chat`). Todo otro
> artefacto del pipeline va en inglés.

---

## Context

El Sprint 006 cerró parcialmente y respondió su única pregunta con una medición:

> **`complete: true` es inalcanzable.** En cinco conversaciones reales, con el
> defecto del harvester ya corregido (W4a, commit `c475239`), `COMPLETE_REASONS`
> no se disparó ni una sola vez.

Reproducible con los dos informes de la sonda:
`python3 scripts/probe_chat_start.py --from-list 5` (corridas 3 y 4, 2026-08-30,
`chat_start_probe_20260830T221517Z.json` y `chat_start_probe_20260830T224020Z.json`).
De cinco chats, **ninguno** paró en `chat_start`; los cinco pararon en `stalled`;
`data-icon` salió vacío en los cinco inventarios de chrome. Tres de cinco
reproducen su conteo de pases y de filas **exactamente** entre corridas, así que
son topes estables y no abandonos: el criterio de aborto del 006 —un marcador
cuya presencia parpadea entre corridas— no se cumplió.

La consecuencia es el problema que este sprint abre: `writers.py:58` publica un
campo `complete` que es **constante `false`**, y un campo constante no puede
distinguir un historial completo de uno truncado, que es exactamente para lo que
existe en un corpus de entrenamiento.

En paralelo, `ADR-0001` promete «all stored chats» y hoy el producto exporta
**una** conversación por invocación (`__main__.py:142`, subcomando `export-one`).
La mitad restante de esa promesa es P3b.

**Qué es cierto cuando esto termina**: una invocación recorre la lista de chats y
exporta cada uno; cada archivo declara su completitud en un campo que puede tomar
más de un valor; y un manifiesto de la corrida dice qué chat salió bien, cuál
falló y por qué.

---

## Design

### D1 — `ADR-0004`: se elige la Opción C, y la medición es la razón

El Sprint 006 dejó cuatro alternativas tabuladas (`006 IMPLEMENTATION_PLAN.md`
§D2) y dejó abierta la elección entre C y D a propósito, para decidir **contra**
la medición y no junto a ella. La medición ya existe, así que la elección se
cierra aquí:

| Opción | Veredicto ahora que hay medición |
| :--- | :--- |
| **A. Status quo** | Descartada por la medición, no por preferencia: el campo es constante `false`. No informa |
| **B. `stalled` cuenta como completo** | Descartada y ya probada mal: produjo un `complete: true` de 217 mensajes sobre una conversación mucho más larga (`history.py:38-44`). Una inferencia no se registra como prueba |
| **C. Tercer estado explícito** | **ELEGIDA.** `completeness: proven \| unproven \| truncated`. No finge certeza y sí distingue «llegué al inicio» de «no puedo demostrarlo» |
| **D. Evidencia positiva compuesta** | **Absorbida dentro de C, no descartada.** El 006 la condicionó a que se demostrara (H2), y (H2) se demostró. Por eso la evidencia compuesta es lo que separa `unproven` de `truncated` — y nunca produce `proven` |

El mapeo queda fijado así, y cada estado se deriva de una condición observable:

| `completeness` | Condición | Evidencia |
| :--- | :--- | :--- |
| `proven` | `stopped_reason == "chat_start"` | El marcador de inicio se observó. Hoy inalcanzable; el estado se conserva porque el día que WhatsApp lo emita, el export debe poder decirlo |
| `unproven` | `stopped_reason == "stalled"` **y** el panel no estaba cargando en el último pase | El panel dejó de producir historia y no había spinner. Es la Opción D: inferencia honesta, nombrada como inferencia |
| `truncated` | `stopped_reason == "max_passes"`, **o** `stalled` con el panel aún cargando | La cosecha paró por el tope duro, o se rindió sobre un panel que seguía trayendo datos. `chat_41d97` en la corrida 3 es este caso exacto (175 pases, `loading-spinner: 1`) |

`complete` (booleano) **se conserva** y se deriva como `completeness == "proven"`.
No se elimina: hay exports v4 en `data/` de corridas anteriores y un lector que
espere el campo no debe romperse. Es compatibilidad, no indecisión.

### D2 — Medir la lista de chats antes de escribir el enumerador

`KI-004-A` es la lección más cara de este proyecto: nunca teorizar sobre un DOM
de terceros. Tres hipótesis sucesivas sobre la dirección del mensaje fueron cada
una equivocada y cada una se publicó.

Sobre la lista de chats hay exactamente **un** dato medido y es insuficiente:
`open_nth_from_list` (`scripts/probe_chat_start.py:616`) leyó `list_size` en el
selector `[data-testid="cell-frame-container"]`, y una medición separada contó
**59** filas bajo `#pane-side div[role="row"]`. Nada de eso responde las dos
preguntas de las que depende el enumerador:

1. **¿La lista está virtualizada?** Es decir: ¿`query_selector_all` sobre el
   selector de la lista devuelve *todas* las conversaciones, o solo las
   renderizadas? Si es lo segundo, «exportar todos los chats» exige hacer scroll
   del propio `#pane-side`, no solo del panel de mensajes.
2. **¿El índice es estable?** WhatsApp reordena la lista cuando llega un mensaje.
   Si el índice `n` cambia de conversación a mitad de corrida, un enumerador por
   índice exporta un chat dos veces y se salta otro, **sin error visible**. Esa
   es la misma clase de fallo silencioso que H-001.

Por eso W5 es una **sonda**, no código de producto, y W7 no se escribe hasta que
W6 tenga números. Si la sonda dice que la lista no se virtualiza y el índice es
estable, el enumerador es trivial; si dice lo contrario, la identidad estable es
el digest del título (`pseudonymous_chat_id`), no la posición.

### D3 — Política de fallo: continuar, y dejarlo escrito

Un fallo en un chat **no** aborta la corrida. La razón no es comodidad: una
corrida de N conversaciones que se cae en la número 3 desperdicia el login manual
y las dos exportaciones ya hechas. Se continúa, y el manifiesto registra el
fallo con su motivo.

Lo que **sí** aborta la corrida es perder la sesión (WhatsApp Web desconectado):
sin sesión, cada intento siguiente fallaría igual, y seguir intentando produciría
un manifiesto lleno de fallos idénticos que no dice nada.

Sin reintentos en este sprint. Un reintento sin haber medido *por qué* falla un
chat es adivinar cuántas veces adivinar.

### D4 — El manifiesto y el índice del operador son un archivo, no dos

`ADR-0001` prohíbe escribir nombres reales en `data/`. Pero el entregable 4 del
roadmap pide un índice que el operador pueda mapear de vuelta —y mapear de vuelta
significa, inevitablemente, guardar la relación `título → chat_id`.

Se resuelve con separación física, no con criptografía:

| Archivo | Contenido | Git |
| :--- | :--- | :--- |
| `data/run_manifest_<stamp>.json` | Por chat: `chat_id`, `completeness`, `message_count`, `outcome`, `reason`. **Sin títulos** | gitignored (`data/`) |
| `data/chat_index_<stamp>.json` | `chat_id` → título en claro. **El único archivo con nombres** | gitignored (`data/`), y nombrado aparte para que el operador pueda borrarlo sin perder el manifiesto |

Escribir el índice es opcional, detrás de una bandera explícita (`--write-index`).
Un archivo con nombres reales no se crea por defecto.

### D5 — Qué se promueve del probe al paquete, y qué no

`open_nth_from_list` vive hoy en `scripts/probe_chat_start.py`, que es un
instrumento de medición, no producto. Se promueve al paquete la *capacidad*
—abrir el chat `n` de la lista, verificando el título como hace H-001— y **no**
el código tal cual: la sonda recarga la página entera entre chats
(`_reload_to_chat_list`), lo cual es correcto para una sonda de cinco chats y
desastroso para una corrida de cincuenta.

La enumeración además **elimina del camino** el defecto `search_open_defect`
(candidato H-002): recorrer la lista no usa búsqueda, así que
`_open_first_result` no participa. El defecto no se corrige en este sprint; se
vuelve irrelevante para la ruta nueva y sigue registrado para `export-one`.

---

## Work

Una fila por unidad. Una unidad es un commit atómico (`RA-08`) que toca **un solo
archivo físico** como sujeto estructural (`agents.md §2 jurisdictional_lock`).

La columna `Assignee (proposed)` es una propuesta de Fase 1. La Fase 4.1
(`agent_orchestrator`) es la autoridad que registra el asignado.

### Bloque A — Decidir y fijar el contrato de completitud

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| W1 | `docs/decisions/ADR-0004-completeness-criterion.md` | create | high | `principal_agent` | ⏳ |
| W2 | `src/whatsapp_chat_extractor/history.py` | modify | high | `implementer_agent` | ⏳ |
| W3 | `src/whatsapp_chat_extractor/writers.py` | modify | high | `implementer_agent` | ⏳ |
| W4 | `tests/test_completeness.py` | create | medium | `implementer_agent` | ⏳ |

### Bloque B — Medir la lista de chats (requiere operador)

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| W5 | `scripts/probe_chat_list.py` | create | medium | `implementer_agent` | ⏳ |
| W6 | `docs/sprints/007-backend-extractor/CHAT_LIST_PROBE_NOTES.md` | create | low | `doc_orchestrator` | ⏳ |

### Bloque C — Enumerar, exportar y declarar el resultado

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| W7 | `src/whatsapp_chat_extractor/chat_list.py` | create | high | `implementer_agent` | ⏳ |
| W8 | `tests/test_chat_list.py` | create | medium | `implementer_agent` | ⏳ |
| W9 | `src/whatsapp_chat_extractor/manifest.py` | create | high | `implementer_agent` | ⏳ |
| W10 | `tests/test_manifest.py` | create | medium | `implementer_agent` | ⏳ |
| W11 | `src/whatsapp_chat_extractor/__main__.py` | modify | high | `implementer_agent` | ⏳ |

### Bloque D — Documentar

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| W12 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | ⏳ |
| W13 | `README.md` | modify | low | `doc_orchestrator` | ⏳ |
| W14 | `docs/0_SYSTEM_OVERVIEW.md` | modify | low | `doc_orchestrator` | ⏳ |
| W15 | `CHANGELOG.md` | modify | low | `principal_agent` | ⏳ |

**Orden obligado**: A → B → C → D. W7 no empieza sin las mediciones de W6; W11
no empieza sin W7 y W9. W14 corrige además una línea obsoleta detectada en la
Fase 0 de esta sesión: `docs/0_SYSTEM_OVERVIEW.md:9` dice «Next: Sprint 005»
mientras su propia cabecera declara auditoría en el #006.

---

## Dependencies

| Package | Version | Why the standard library and the existing dependencies do not suffice |
| :--- | :--- | :--- |
| None | — | El sprint no añade ninguna. `playwright` y `pytest` ya están presentes desde el Sprint 003; el manifiesto y el índice se serializan con `json` de la biblioteca estándar, igual que `writers.py` |

---

## Mechanisms

| Mechanism | Deterministic or agent judgment | Invoker (`RA-16`) |
| :--- | :--- | :--- |
| `scripts/probe_chat_list.py` — sonda de la lista de chats | script (Python, ejecución manual por el operador) | `docs/sprints/007-backend-extractor/CHAT_LIST_PROBE_NOTES.md` §«Cómo se corre», invocación humana; declarado en su docstring `invoked_by:` |
| `wa-extract export-all` — enumeración + exportación | script (subcomando del CLI) | `src/whatsapp_chat_extractor/__main__.py` `build_parser`; documentado en `README.md` |
| Escritura del manifiesto de corrida | script (`manifest.py`, llamado por `cmd_export_all`) | `src/whatsapp_chat_extractor/__main__.py` `cmd_export_all` |
| Clasificación de completitud | script (`history.build_result`, función pura) | `src/whatsapp_chat_extractor/history.py` `harvest_history` |

Ninguna cadencia recurrente de este sprint se delega a juicio de agente: las
cuatro son deterministas y las cuatro tienen invocador nombrado. `RA-16
INVOCATION_COVERAGE`: ningún workflow, script, skill ejecutable, hook o gate se
integra sin un invocador declarado y verificable, o una excepción tipada en
`config/invocation_exceptions.json` que diga por qué no lo tiene.

---

## Cost

| Field | Value | Reproduce |
| :--- | :--- | :--- |
| Delegation | `native` | `docs/active_state.json` `delegation_mode` |
| Work units | 15 | Conteo de filas en las cuatro tablas de Work |
| Subagents dispatched | 2 previstos (`qa_agent`, `tester_agent` en Fase 7) | Los gates corren en contexto fresco bajo ambas herramientas; la autoría va secuencial en el padre |
| Prior session ratio | n/a al abrir (sin transcript previo bajo esta herramienta) | `python3 .agents/scripts/session_cost.py --from-anchor --json` |
| **Ratio de ESTA sesión (medido al cierre)** | **22,4× en el ciclo 7 — por encima del umbral duro de 15×** | `python3 .agents/scripts/session_cost.py --session dfadf1f8-34d8-4608-8f38-cb3d85f64cdf` |

**Corrección de arnés.** Esta sección decía `sequential` / `0 subagentes` /
«Cursor sin transcript». El ancla se reclamó como `cursor` porque
`commands/start.md` fijaba `--tool cursor` para ambos arneses hasta `v4.24.0`, y
el texto del comando llegó desde el espejo `v4.23.0` — segundos antes de que
`sync_agents_pin.py` instalara justamente esa corrección. La sesión es Claude
Code: `RA-18` no aplica, y los tiers salen de `config/model_tiers.json`
`claude_code` (`gate` opus/high, `author` sonnet/medium, `mechanical` haiku/low),
no de `audit_cursor_models.py`.

**Divergencia declarada** (`start_workflow.md` `delegation_conflict`): el arnés
puede instanciar los ocho roles, pero las instrucciones operativas de esta sesión
prohíben lanzar subagentes sin que el humano lo pida. La autoría corre secuencial
en el agente padre y esto queda **reportado, no absorbido**; el fan-out está
disponible a petición.

**El umbral duro se superó, y esta sección se actualiza porque `rules/token_economy.md`
§3.1 lo exige.** Medido al cierre: 482 turnos, 7 ciclos de contexto, **cuatro de
ellos por encima de 15×** (15,0× · 15,9× · 19,5× · 21,3× · 22,4×), con 123,9 M de
lectura de caché. El coste es el área bajo el diente de sierra, y la compactación
reinicia el eje sin reducirla.

Causas, en orden de contribución y sin adornos:

| Causa | Evidencia |
| :--- | :--- |
| El sprint se planificó grande y se ejecutó entero en una sesión | 15 units planificados + 6 añadidos, bloques A–D seguidos |
| Tres corridas de sonda con dos defectos corregidos entre ellas | Cada ciclo de corrección fue leer, parchear, testear y re-registrar |
| **Dos subagentes de gate que consumieron ~430 k tokens y no entregaron hallazgos** | `af56a8f` 3 invocaciones · `a90db59` 2; la reverificación hubo que hacerla igualmente |
| Verificación posterior a los gates que encontró el defecto de subcuenta | Trabajo necesario, pero fuera del presupuesto planificado |

Lo que habría contenido el coste, para el 008: cerrar tras el Bloque A y abrir un
sprint aparte para P3b. El tamaño se marcó como riesgo en esta misma sección al
planificar («15 unidades es grande») y no se actuó sobre esa marca.

---

## Tests

| Check | Fails against the current tree? |
| :--- | :--- |
| Un `HarvestResult` con `stopped_reason="stalled"` y panel quieto declara `completeness="unproven"` | **Sí — este es el defecto.** Hoy `HarvestResult` no tiene campo `completeness` (`history.py:70-76`) |
| Un `HarvestResult` con `stopped_reason="stalled"` y panel cargando declara `completeness="truncated"` | **Sí — este es el defecto.** Hoy ambos casos son indistinguibles: los dos dan `complete: false` |
| `build_export` emite `schema_version: 5` y un campo `completeness` | **Sí — este es el defecto.** `writers.py:15` fija `SCHEMA_VERSION = 4` |
| `complete` sigue presente y vale `completeness == "proven"` | **No — es una regresión a proteger.** El campo existe hoy y no debe desaparecer |
| `pseudonymous_chat_id` sigue siendo estable y sin sal | **No — es una regresión a proteger.** Cubierto por `tests/test_writers.py` |
| El enumerador visita cada `chat_id` exactamente una vez sobre una lista simulada | **Sí — este es el defecto.** No existe enumerador |
| Un fallo en un chat no aborta la corrida y queda en el manifiesto con su motivo | **Sí — este es el defecto.** No existe política de fallo |
| El manifiesto no contiene ningún título de chat | **Sí — este es el defecto.** No existe manifiesto |
| El índice de chats solo se escribe con `--write-index` | **Sí — este es el defecto.** No existe índice |
| Las 116 pruebas actuales siguen pasando | **No — es una regresión a proteger** |

Ninguna prueba de este sprint abre un navegador ni toca WhatsApp Web: se usan
dobles del `Page` de Playwright, como ya hace `tests/test_history.py`.

---

## Verification

Los códigos de salida se leen con `$?` directamente, **nunca a través de una
tubería**, que reporta el código del último comando de la tubería.

| Command | Expected |
| :--- | :--- |
| `ruff check .` | `All checks passed!`, exit `0` |
| `python3 -m pytest tests/ -q` | exit `0`, ≥ 116 pruebas pasando más las nuevas de W4, W8 y W10 |
| `python3 -c "import whatsapp_chat_extractor.chat_list, whatsapp_chat_extractor.manifest"` | exit `0`, sin salida |
| `python3 -m whatsapp_chat_extractor export-all --help` | exit `0`, muestra `--write-index` y la política de fallo |
| `python3 skills/token-saver-auditor/scripts/audit_plan.py docs/sprints/007-backend-extractor/IMPLEMENTATION_PLAN.md` (con CWD en `.agents/`) | `[OK] audit_plan`, exit `0` |
| `git ls-files data/ \| wc -l` | `0` — ninguna conversación exportada versionada |
| `git -C .agents status --porcelain` | vacío — el host no escribe dentro del submódulo (`agents.md §3 jurisdiction`) |

**Verificación que exige operador** (no puede correr desatendida: login real,
chats reales, datos personales reales):

| Command | Expected |
| :--- | :--- |
| `python3 scripts/probe_chat_list.py --scroll-passes 20` | Un informe JSON en `data/` que responda D2.1 (¿virtualiza?) y D2.2 (¿índice estable?) con números |
| `python3 -m whatsapp_chat_extractor export-all --limit 3` | Tres archivos de chat más un manifiesto cuyas tres filas declaren su `outcome` |

---

## Documentary impact (T5)

| Artefacto | Qué cambia |
| :--- | :--- |
| `docs/decisions/ADR-0004-completeness-criterion.md` | Nuevo. Qué reporta el export cuando no puede probarse un inicio; elige la Opción C con la medición del 006 como fundamento |
| `docs/architecture/EXTRACTOR_BLUEPRINT.md` | Contrato de completitud (los tres estados y su condición), esquema v5, y el módulo de enumeración |
| `README.md` | Semántica de `completeness` y de `complete`; subcomando `export-all`; qué es `--write-index` y por qué está apagado por defecto |
| `docs/0_SYSTEM_OVERVIEW.md` | Sección 6 gana `chat_list.py`, `manifest.py` y `scripts/probe_chat_list.py`; se corrige la línea 9, que apunta al Sprint 005 |
| `CHANGELOG.md` | Entrada del Sprint 007 bajo `[Unreleased]`, incluido el salto de esquema v4 → v5 como cambio observable por el consumidor |
| `docs/sprints/007-backend-extractor/CHAT_LIST_PROBE_NOTES.md` | Nuevo. Procedimiento y tablas de evidencia, **vacías** hasta que la sonda corra |
| `docs/roadmaps/docs/extractor/002-delivery-program.md` | Fila P3b a `CLOSED` con el resultado medido, en el Cierre de Sprint |

**Cifras medidas.** Toda cifra en Context, Design y Verification lleva el comando
que la reproduce. Una cifra sin su comando es memoria, no evidencia.

Las tablas de `CHAT_LIST_PROBE_NOTES.md` se escriben **vacías** y se llenan solo
cuando la sonda corre. Rellenarlas desde la corrida del 006 o desde la estructura
documentada de WhatsApp sería `KI-004-A` otra vez.

---

## Out of scope

| Exclusion | Why, and where it goes instead |
| :--- | :--- |
| Corregir `search_open_defect` (candidato H-002) | La enumeración lo saca del camino sin tocarlo (§D5). Sigue afectando a `export-one` y sigue registrado en `docs/active_state.json`; se corrige por `RA-03` si alguien lo reporta en producción |
| Clasificar `unknown_media` (30 de 311 filas, 9.6 % en la corrida 3) | Necesita las firmas capturadas en el JSON de la corrida 3 y un análisis propio. Va a Sprint 008 o a un sprint de fidelidad dedicado |
| Reintentos por chat | Sin medir por qué falla un chat, un reintento es adivinar (§D3). Vuelve cuando el manifiesto de la primera corrida real tenga motivos de fallo reales |
| Descargar contenido multimedia | `ADR-0003` lo prohíbe y no se reabre aquí |
| Los cuatro hallazgos upstream abiertos (`_008`, `_010`, `_011`, `_012`) | `agents.md §3 strict_rule` prohíbe al host parchear el submódulo. Van por `§4 feedback_upstream`, en un clon separado, y no son trabajo de este sprint |
| CI ejecutándose y branch protection | Bloqueo de plataforma, no de código. Es Sprint 008 / P4, vía `/agents:harden` |

---

## Abort criterion

Este sprint se detiene y se revierte si la sonda W5 mide que **la posición de un
chat en la lista no es estable entre dos lecturas separadas por una corrida de
exportación**, y el digest del título tampoco alcanza para reidentificarlo
(porque el título cambió, o porque dos conversaciones comparten título).

En ese caso no existe identidad estable para una conversación, «exportar cada
chat exactamente una vez» no es verificable, y el Bloque C se abandona: el sprint
cerraría con el Bloque A entregado y el hallazgo escrito, igual que el 006 cerró
con su medición. Implementar un enumerador que no puede demostrar que no duplica
ni se salta conversaciones sería publicar una inferencia con forma de garantía —
el error exacto contra el que se escribió `ADR-0004`.

---

## Approval — `triple_lock` lock 1

**APROBACIÓN COMPLETA, humano, 2026-08-31.** Los cuatro bloques (W1–W15) quedan
autorizados y `ADR-0004` se confirma en la **Opción C**. Los bloques dejan de ser
tramos de autorización y siguen siendo el **orden obligado** de ejecución, porque
C depende de los números que produce B:

| Tramo | Unidades | Qué entrega | Depende de |
| :--- | :--- | :--- | :--- |
| A | W1–W4 | `ADR-0004` y el esquema v5 | Nada. Todo verificable sin navegador |
| B | W5–W6 | La medición de la lista de chats | Operador presente |
| C | W7–W11 | Enumeración, manifiesto, `export-all` | Los números de B |
| D | W12–W15 | Documentación y Ledger | A y C |

| Field | Value |
| :--- | :--- |
| **Approved by** | Humano (operador del proyecto), en sesión |
| **Date** | 2026-08-31 |
| **Plan commit at approval** | `dd815a6` |
| **Scope approved** | W1–W15, los cuatro bloques. `ADR-0004` = Opción C |
| **Remaining locks** | Active Sprint ✅ · veredictos QA + Tester ⏳ · OK humano al cierre ⏳ |

*La Fase 5 es una única autorización humana atendida. NO debe envolverse en un
`/loop` desatendido (`workflows/pipeline_workflow.md`, `rules/loop_governance.md`).
Cualquier `/loop` que este sprint llegue a correr —solo Fases 6-8— está gobernado
por `scripts/loop_guard.py start`, que falla cerrado.*

> **No borrar la frase anterior.** `audit_plan.py` Filter 6 rechaza cualquier plan
> que nombre `/loop` sin nombrar también `loop_guard.py`, y este pie nombra ambos.
