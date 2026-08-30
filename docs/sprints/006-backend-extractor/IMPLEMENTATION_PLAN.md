# Implementation Plan: Sprint 006 — Criterio de completitud del historial

**Canonical path**: `docs/sprints/006-backend-extractor/IMPLEMENTATION_PLAN.md`
**Branch**: `ai-sprint/006` · **Base**: `main` at `a654e47`
**Status**: `DRAFT` → `APPROVED` → `EXECUTING` → `CLOSED`

> Autorizado en chat el 2026-08-30: `full_run` como objetivo, con `unknown_media`
> y `search_selector_scope` recogidos como observación durante la misma corrida.

---

## Context

La promesa del producto es exportar el historial **completo** de un chat. Nunca se
ha cumplido de forma demostrable: `stopped_reason: chat_start` y `complete: true`
**no se han producido jamás**, ni una sola vez, en ninguna corrida.

El ancla lo describe como «`CHAT_START_SELECTORS` sin verificar», como si faltara
afinar un selector. La lectura del código dice otra cosa, y es más grave:

| Evidencia | Dónde | Qué implica |
| :--- | :--- | :--- |
| `COMPLETE_REASONS = (STOP_CHAT_START,)` | `src/whatsapp_chat_extractor/history.py:44` | Solo el marcador de inicio produce `complete: true` |
| «False is not proof of more history — WA Web **omits the marker in many conversations**» | `src/whatsapp_chat_extractor/export_one.py:451` | El propio código admite que el marcador falta en muchos chats |

Juntas: para toda conversación donde WhatsApp no dibuja el marcador, `complete:
true` es **inalcanzable por diseño**, por correcta que sea la cosecha. El campo no
queda conservador — queda **constante**. Un campo que siempre vale `false` no
distingue un historial completo de uno truncado, que es exactamente la
información por la que existe el campo en un corpus de entrenamiento.

No está establecido cuál de estas dos cosas es cierta, y **el sprint existe para
medirlo, no para asumirlo**:

- **(H1)** El marcador existe en algunos chats y nunca se ha corrido sin tope
  contra uno de ellos. Entonces `complete: true` es alcanzable y falta ejecutarlo.
- **(H2)** El marcador no aparece en ninguno de los chats del operador. Entonces
  el criterio actual es inservible en la práctica y hay que decidir otro.

Mediciones vigentes, cada una con su comando:

| Medición | Valor | Reproduce |
| :--- | :--- | :--- |
| Corrida con tope, 2026-08-30 | 513 mensajes en 12 pasadas | `docs/sprints/005-backend-extractor/IMPLEMENTATION_PLAN.md` (spike W2) |
| Export v4 vivo | 301 filas, 6 con `kind: unknown` | `docs/sprints/005-backend-extractor/IMPLEMENTATION_PLAN.md` (hallazgo 1) |
| Suite actual | 88 passed | `.venv/bin/python -m pytest tests/ -q` |
| Corridas con `complete: true` | **0** | `grep -rl '"complete": true' data/ 2>/dev/null \| wc -l` |

**Terminado cuando**: existe una decisión registrada en ADR sobre qué reporta el
export cuando el marcador no está, esa decisión está implementada y fijada por
tests, y se ha ejecutado al menos una corrida sin tope cuyo resultado —
`complete: true` o `complete: false` con razón explícita — es **evidencia medida,
no inferida**.

---

## Design

### D1 — Medir antes de decidir

El primer trabajo es una **sonda**, no un cambio de código. `KI-004-A` es
explícito: nunca teorizar sobre un DOM de terceros, porque tres hipótesis
sucesivas sobre la dirección del mensaje fueron cada una equivocada y cada una se
publicó. La sonda vuelca la cadena real de atributos en la cabecera del panel
para **N ≥ 5 chats distintos**, incluyendo uno deliberadamente corto, y responde
si el marcador existe y en cuántos.

Sin ese dato, cualquier ADR sobre completitud sería una preferencia, no una
decisión.

### D2 — El criterio de completitud, y por qué no se sintetiza

Alternativas consideradas para el caso «no hay marcador»:

| Opción | Qué hace | Por qué se elige o descarta |
| :--- | :--- | :--- |
| **A. Status quo** | `complete: false` para siempre | **Descartada**: el campo deja de informar. Indistinguible de un truncamiento real |
| **B. Tratar el estancamiento como completo** | `stalled` vuelve a `COMPLETE_REASONS` | **Descartada, y ya se probó**: produjo un export `complete: true` de 217 mensajes de una conversación que el operador sabía mucho más larga (`history.py:39`). Una inferencia no puede registrarse como prueba |
| **C. Tercer estado explícito** | `completeness: proven \| unproven \| truncated` | **Candidata principal**: no finge certeza y sí distingue «llegué al inicio» de «no puedo demostrarlo». `complete` booleano se conserva por compatibilidad, derivado de `proven` |
| **D. Evidencia positiva compuesta** | Altura de scroll estable + sin filas nuevas + botón de carga ausente | **Candidata secundaria**, solo si D1 demuestra (H2). Sigue siendo inferencia; entraría como `unproven`, nunca como `proven` |

La elección entre C y D **no se cierra en este documento**: depende del resultado
de D1. Lo que sí se fija de antemano es la restricción — el mismo principio de
`ADR-0003`: un valor inferido nunca se registra con la forma de uno medido.

### D3 — Observación sin corrección

`unknown_media` y `search_selector_scope` **no se corrigen aquí**. La corrida
larga de W5 es la única actividad que produce el DOM real que ambos necesitan, así
que se recoge la evidencia y se archiva para Sprint 007. Corregirlos con la
muestra actual (6 filas; cero sondas del panel de resultados) sería adivinar.

---

## Work

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| W1 | `scripts/probe_chat_start.py` | create | low | `implementer_agent` | ⏳ |
| W2 | `docs/sprints/006-backend-extractor/DOM_PROBE_NOTES.md` | create | low | `doc_orchestrator` | ⏳ |
| W3 | `docs/decisions/ADR-0004-completeness-criterion.md` | create | high | `principal_agent` | ⏳ |
| W4 | `src/whatsapp_chat_extractor/history.py` | modify | high | `implementer_agent` | ⏳ |
| W5 | `tests/test_completeness.py` | create | medium | `implementer_agent` | ⏳ |
| W6 | `src/whatsapp_chat_extractor/writers.py` | modify | medium | `implementer_agent` | ⏳ |
| W7 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | ⏳ |
| W8 | `README.md` | modify | low | `doc_orchestrator` | ⏳ |

**W1 y la corrida sin tope requieren al operador presente**: login real, elección
de chat y datos personales reales. No son ejecutables de forma desatendida, y por
eso este sprint **no puede envolverse en `/loop`**: no se arma `loop_guard.py
start` porque no habrá iteración desatendida que guardar. La prohibición es el
motivo por el que el guardián no aparece, no un olvido — `rules/loop_governance.md`
gobierna el caso contrario, el de una rutina que sí corre sola.

Orden obligado: W1 → W2 → W3 antes de W4. W4 sin el ADR de W3 sería implementar
una decisión no tomada.

---

## Dependencies

| Package | Version | Why the standard library and the existing dependencies do not suffice |
| :--- | :--- | :--- |
| None | — | La sonda usa Playwright, ya presente. El criterio de completitud es lógica propia |

---

## Mechanisms

| Mechanism | Deterministic or agent judgment | Invoker (`RA-16`) |
| :--- | :--- | :--- |
| `scripts/probe_chat_start.py` | script | `docs/sprints/006-backend-extractor/IMPLEMENTATION_PLAN.md` W1, invocación manual del operador |
| Clasificación de completitud | script (`history.build_result`) | `history.harvest_history` |

Ninguno es de cadencia recurrente: la sonda se ejecuta una vez por sprint bajo
supervisión humana, y la clasificación es una función pura dentro del cosechador.

---

## Cost

| Field | Value | Reproduce |
| :--- | :--- | :--- |
| Delegation | `sequential` | `docs/active_state.json` `delegation_mode` |
| Work units | 8 | Recuento de filas de la tabla Work |
| Subagents dispatched | 0 | Cursor `sequential` |
| Prior session ratio | n/a (Cursor / sin transcript) | `python3 .agents/scripts/session_cost.py --from-anchor --json` |

---

## Tests

| Check | Fails against the current tree? |
| :--- | :--- |
| Un chat corto con marcador de inicio visible exporta `complete: true` | **Sí — este es el defecto**: nunca se ha producido |
| Un cosechado que se detiene por estancamiento reporta `complete: false` | **No — regresión a proteger** (`history.py:39`, ya corregido) |
| Un cosechado que agota `max_passes` reporta `complete: false` | **No — regresión a proteger** |
| El estado de completitud distingue «probado» de «no demostrable» | **Sí — este es el defecto**: hoy ambos colapsan en `false` |
| Las 88 pruebas actuales siguen pasando | **No — regresión a proteger** |

---

## Verification

| Command | Expected |
| :--- | :--- |
| `.venv/bin/python -m pytest tests/ -q` | `88 passed` o más, cero fallos |
| `.venv/bin/python -m ruff check .` | `All checks passed!` |
| `python3 .agents/scripts/check_task_scope.py --sprint-dir docs/sprints/006-backend-extractor` | exit `0` |
| `python3 .agents/scripts/check_gate_log.py --sprint-dir docs/sprints/006-backend-extractor` | exit `0` |
| `python3 .agents/scripts/submodule_purity.py` | exit `0` |

Los códigos de salida se leen con `$?` directamente, nunca a través de una tubería.

---

## Documentary impact (T5)

| Artefacto | Qué cambia |
| :--- | :--- |
| `docs/decisions/ADR-0004-completeness-criterion.md` | Nuevo. Qué reporta el export cuando el marcador de inicio no existe |
| `docs/architecture/EXTRACTOR_BLUEPRINT.md` | El contrato de completitud y el esquema resultante |
| `README.md` | Cómo leer `complete` / `completeness`; hoy documenta un booleano que siempre vale `false` |
| `CHANGELOG.md` | Entrada de Sprint 006 bajo `[Unreleased]` |
| `docs/sprints/006-backend-extractor/DOM_PROBE_NOTES.md` | Nuevo. Evidencia DOM medida, incluida la de `unknown_media` y el panel de resultados |

---

## Out of scope

| Exclusion | Why, and where it goes instead |
| :--- | :--- |
| Acotar `SEARCH_RESULT_SELECTORS` fuera de `#pane-side` | H-001 ya convierte un clic errado en aborto, así que el riesgo residual es una ejecución fallida, no un corpus mal atribuido. Evidencia DOM se recoge en W2 → **Sprint 007** |
| Identificar los 6 `kind: unknown` | 6 de 301 filas no bastan para distinguir vídeo de documento de sticker. Muestra ampliada en W2 → **Sprint 007** |
| Descarga o referencia de ficheros de medios | Restricción de privacidad vigente desde `ADR-0003`. No se reabre |
| Corregir el desvío de arranque de sesión (`UPSTREAM_FINDING_008`) | Es *framework-class*: `§3 strict_rule` prohíbe al host parchear el submódulo → **PR al núcleo desde un clon separado** |
| Facturación de GitHub y alcance del token de CI | Plataforma, no código → **`/agents:harden`** |

---

## Abort criterion

Se aborta y se revierte si, tras la sonda W1 sobre al menos 5 chats, **no puede
establecerse ni (H1) ni (H2)** — es decir, si la presencia del marcador resulta no
reproducible entre corridas sobre el mismo chat. Un criterio de completitud
construido sobre una señal intermitente sería peor que el actual: convertiría un
campo inútil pero honesto en uno que miente de forma intermitente.

En ese caso el sprint se cierra con la sonda y sus notas como único entregable, y
la decisión de diseño se eleva al humano con la evidencia sobre la mesa.
