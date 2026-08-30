# Implementation Plan: Sprint 005 — backend-extractor (P2.5 corpus fidelity)

**Canonical path**: `docs/sprints/005-backend-extractor/IMPLEMENTATION_PLAN.md`
**Branch**: `ai-sprint/005` · **Base**: `main` at `ac806f562853819e071b151a5b14343470d11ae2` (v0.4.0)
**Status**: `APPROVED` (Fase 5, 2026-08-30)

> Español permitido en este documento (`agents.md §1 user_chat`). Fase del
> programa: P2.5 del roadmap reestructurado 2026-08-30.

---

## Context

Sprint 004 cerró P2 y desplegó v0.4.0. Su propia revisión de alcance encontró
cuatro elementos **declarados en los ADR y nunca construidos**, y la sonda del
DOM en vivo forzó una decisión de producto que el humano tomó el 2026-08-30.

| Figura | Valor | Reproduce |
| :--- | :--- | :--- |
| Base SHA | `ac806f5` | `git rev-parse main` |
| Mensajes de media descartados | 3 de las 12 primeras filas sondeadas | `docs/sprints/004-backend-extractor/PHASE_REGISTER.md` |
| `README.md` declarado | `pyproject.toml:9` | `grep -n readme pyproject.toml` |
| `LICENSE` declarado | `pyproject.toml:11` | `grep -n license pyproject.toml` |
| Comandos en `.cursor/commands/` | Solo los del framework | `ls .cursor/commands/` |

### El defecto de corpus

`collect_visible_rows` salta toda fila cuyo `_row_body` sea vacío. Una foto o
una nota de voz no deja **ningún rastro**. La conversación exportada muestra
pregunta → siguiente pregunta, sin señal de que hubo un audio en medio. Para el
consumidor declarado —un agente que aprende cómo el negocio habla con sus
clientes— eso enseña adyacencias que nunca ocurrieron.

ADR-0003 lo corrige: el mensaje de media se emite con `body` vacío y un campo
`kind` que nombra el medio. El contenido del media sigue sin descargarse.

---

## Design

| Decisión | Elección | Rechazado |
| :--- | :--- | :--- |
| Media en el corpus | Registro con `body` vacío y `kind` | Seguir descartando (ADR-0003 opción B) |
| Contenido del media | No se descarga ni se referencia | Descargar junto al JSON (rompe ADR-0001) |
| Transcripción de audio | Fuera de alcance | Enviar audio de clientes a un tercero |
| Detección de `kind` | Sonda del DOM **antes** de escribir el selector | Deducirlo de la estructura (`KI-004-A`: falló tres veces) |
| Media no reconocido | `kind: "unknown"` | Adivinar el tipo |
| Esquema | v4, `kind` obligatorio en todo registro | Campo opcional (haría ambiguo el v3) |
| Superficie Cursor | `.cursor/commands/wa-export.md`, fichero propio del host | Symlink al de `.claude/` (`install.sh` lo sobrescribe) |
| Licencia | `LICENSE` propietaria, coherente con `pyproject.toml:11` | Cambiar a OSS sin decisión del propietario |

### Riesgo principal

La detección de `kind` depende del marcado de WhatsApp Web, igual que la
dirección del mensaje en Sprint 004 — donde tres hipótesis consecutivas fueron
erróneas y las tres se desplegaron. **La sonda va primero.** Los indicios ya
observados en la sonda de Sprint 004 son un punto de partida, no una conclusión:

| Observado | Fila |
| :--- | :--- |
| `data-testid: image-thumb`, aria `Abrir foto` | Imagen |
| `data-testid: ptt-status`, aria `Mensaje de voz` | Nota de voz |

---

## Work

| # | File | Operation | Risk | Assignee (proposed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| W0 | `docs/decisions/ADR-0003-media-placeholders-in-export.md` | create | low | `doc_orchestrator` | ✅ |
| W1 | `docs/roadmaps/docs/extractor/002-delivery-program.md` | modify | low | `orchestrator` | ✅ |
| W2 | (scratchpad) sonda de `kind` contra el DOM en vivo | run | medium | `implementer_agent` | ✅ |
| W3 | `src/whatsapp_chat_extractor/export_one.py` | modify | high | `implementer_agent` | ✅ |
| W4 | `src/whatsapp_chat_extractor/writers.py` | modify | medium | `implementer_agent` | ✅ |
| W5 | `src/whatsapp_chat_extractor/history.py` | modify | low | `implementer_agent` | ✅ |
| W6 | `tests/test_row_fields.py` | modify | low | `implementer_agent` | ✅ |
| W7 | `tests/test_writers.py` | modify | low | `implementer_agent` | ✅ |
| W8 | `.cursor/commands/wa-export.md` | create | low | `skill_architect` | ✅ |
| W9 | `README.md` | create | low | `doc_orchestrator` | ✅ |
| W10 | `LICENSE` | create | low | `doc_orchestrator` | ✅ |
| W11 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | ✅ |
| W12 | `CHANGELOG.md` | modify | low | `doc_orchestrator` | ✅ |

### Detalle

| # | Contenido |
| :--- | :--- |
| W2 | Ampliar `probe_direction.py` para volcar `data-testid`/`aria-label`/`data-icon` de filas **sin texto**. Sin imprimir cuerpos. Su salida decide W3 |
| W3 | `_row_kind(row) -> str` a partir de lo que W2 mida. `collect_visible_rows` deja de saltar filas sin cuerpo: emite el registro con `kind` |
| W4 | `MessageRecord` gana `kind`; `SCHEMA_VERSION = 4`. `message_count` pasa a contar mensajes, no mensajes de texto |
| W5 | `fallback_message_id` incorpora `kind` — dos notas de voz consecutivas del mismo emisor y minuto colisionarían con la clave actual |
| W6 | Casos por `kind` contra filas stub, incluido `unknown` |
| W7 | Aserciones de esquema v4 |
| W8 | Comando Cursor equivalente al de Claude Code. Fichero propio, **no** symlink: `install.sh` solo escribe `.cursor/commands/` del framework y lo sobrescribiría |
| W9 | README: qué es, requisitos, `login` → `export-one`, cómo leer `complete`, y que `data/` no se commitea nunca |
| W10 | `LICENSE` propietaria que respalde `pyproject.toml:11` |

---

## Dependencies

| Package | Version | Why the standard library and the existing dependencies do not suffice |
| :--- | :--- | :--- |
| None | — | `kind` sale del DOM que Playwright ya expone |

---

## Mechanisms

| Mechanism | Deterministic or agent judgment | Invoker (`RA-16`) |
| :--- | :--- | :--- |
| Clasificación de `kind` | script (`export_one._row_kind`) | `collect_visible_rows` |
| Disparo desde Cursor | comando slash → CLI | `human:/wa-export` |

---

## Cost

| Field | Value | Reproduce |
| :--- | :--- | :--- |
| Delegation | `sequential` | `docs/active_state.json` `delegation_mode` |
| Work units | 13 | Filas de la tabla Work |
| Subagents dispatched | 0 | `sequential` bajo Cursor |
| Prior session ratio | n/a (Cursor / sin transcript medible) | `python3 .agents/scripts/session_cost.py --from-anchor --json` |

---

## Tests

| Check | Fails against the current tree? |
| :--- | :--- |
| Una fila de imagen produce un registro con `kind: "image"` | **Sí** — hoy se descarta |
| Una fila de nota de voz produce un registro con `kind: "voice"` | **Sí** — hoy se descarta |
| Un mensaje de texto lleva `kind: "text"` | **Sí** — el campo no existe |
| Una fila de media desconocida produce `kind: "unknown"`, no se descarta | **Sí** |
| Un pie de foto se conserva en `body` con `kind` de imagen | **Sí** |
| Dos notas de voz del mismo emisor y minuto no se deduplican entre sí | **Sí** — la clave actual las colapsaría |
| `build_export` emite `schema_version: 4` | **Sí** |
| La atribución de turno sigue funcionando | **No** — regresión a proteger (`tests/test_row_fields.py`) |

---

## Verification

| Command | Expected |
| :--- | :--- |
| `ruff check .` | exit `0` |
| `.venv/bin/python -m pytest -q` | exit `0`, cero fallos |
| `.venv/bin/wa-extract export-one --query "<chat>" --max-passes 12` | exit `3` (acotado), JSON escrito |
| `python3 -c "…; print(d['schema_version'], collections.Counter(m['kind'] for m in d['messages']))"` | `4` y un recuento con al menos un `kind` no-`text` |
| `.venv/bin/pip wheel . --no-deps -w "$TMPDIR/w"` | exit `0` — hoy debería fallar por `README.md` ausente |
| `git -C .agents status --porcelain` | vacío |

**Ejecutar el export fuera del sandbox del agente**: Chromium no puede crear su
socket `ProcessSingleton` dentro y aborta (`KI-004-E`).

---

## Documentary impact (T5)

| Artefacto | Qué cambia |
| :--- | :--- |
| `docs/decisions/ADR-0003-…md` | Creado (W0) |
| `docs/roadmaps/…/002-delivery-program.md` | Reestructurado (W1) |
| `docs/architecture/EXTRACTOR_BLUEPRINT.md` | Esquema v4, contrato de `kind` |
| `docs/walkthroughs/EXTRACTOR_WALKTHROUGH.md` | Cómo leer `kind` |
| `CHANGELOG.md` | Entrada Sprint 005 bajo `[Unreleased]` |
| `README.md`, `LICENSE` | Creados |
| `docs/active_state.json` | `current_sprint` a 005 |

---

## Out of scope

| Exclusion | Why, and where it goes instead |
| :--- | :--- |
| Descargar ficheros de media | ADR-0001 y ADR-0003 §2 lo prohíben |
| Transcribir notas de voz | ADR-0003 opción D: enviaría audio de clientes a un tercero |
| Ejecución sin tope / `complete: true` | Sprint 006 — es el riesgo abierto de Sprint 004 |
| Volcado de todos los chats | Sprint 007 |
| CI, protección de rama, `/agents:harden` | Sprint 008, bloqueado hasta repo público |
| PRs upstream 004 y 005 | Sprint 008; clon aparte del núcleo |

---

## Abort criterion

Se aborta si la sonda W2 no encuentra **ninguna** señal estable que distinga
tipos de media —ni `data-testid`, ni `aria-label`, ni `data-icon`— sobre las
filas sin texto del chat de prueba.

En ese caso, emitir `kind: "unknown"` para toda fila sin cuerpo sigue siendo
mejor que descartarla (preserva la estructura de turnos), y el sprint se reduce
a esa forma degradada más W8-W10, dejando la clasificación fina para cuando haya
evidencia. Lo que **no** se hará es inventar selectores: `KI-004-A`.

---

## Approval — `triple_lock` lock 1

| Field | Value |
| :--- | :--- |
| **Approved by** | GstMirabal — autorización atendida en sesión `20260830T082619Z-12789` |
| **Date** | 2026-08-30 |
| **Plan commit at approval** | `c090646` — este fichero ya estaba commiteado antes de la aprobación (`§2 triple_lock`) |
| **Scope approved** | W2–W12 tal como están escritos, sin enmiendas |
| **Remaining locks** | Active Sprint ✅ (`ai-sprint/005`) · veredictos QA + Tester ⏳ · OK humano al cierre ⏳ |

*La Fase 5 es una única autorización humana atendida. NO puede envolverse en un
`/loop` desatendido.*

---

## Execution record — 2026-08-30

### Lo que midió W2

Sonda ejecutada dos veces contra un chat real, fuera del sandbox. Ventana de 36
filas, 7 sin texto seleccionable.

| Señal observada | Filas | Conclusión |
| :--- | :--- | :--- |
| `data-testid` + `data-icon` = `ptt-status` | 4 | `kind: voice` |
| `data-testid=image-thumb` + `media-url-provider` | 1 | `kind: image` |
| `img[data-testid=selectable-text]`, `alt_len=2`, no ASCII | 2 | **No previsto — ver abajo** |

`has_img` resultó `True` en las 7 filas, incluidas las notas de voz, así que se
descartó como discriminador y se sustituyó por `alt_len` / `alt_nonascii`.

### Desviaciones respecto al plan aprobado

Tres, todas dentro del alcance W2–W12 y ninguna contradice ADR-0003.

| # | Qué decía el plan | Qué se hizo, y por qué |
| :--- | :--- | :--- |
| 1 | Toda fila sin cuerpo es media, y la no reconocida es `unknown` | Dos de las 7 filas sin cuerpo **no eran media**: eran mensajes de solo emojis, que WhatsApp dibuja como `<img alt>` dentro de un `div[data-testid="selectable-text"]`. Emitirlas como `unknown` habría sido falso. `_row_emoji_body` recupera los caracteres de `alt` y salen como `kind: text` con su cuerpo real |
| 2 | W5: `fallback_message_id` incorpora `kind` para que dos notas de voz consecutivas no colisionen | **La premisa era incorrecta**: dos notas de voz comparten `kind`, emisor, minuto y cuerpo vacío, así que seguirían colisionando. `kind` sí separa una foto de una nota de voz. La separación real se resolvió aguas arriba, en `_row_id`, con el envoltorio `conv-msg-<HEX>` que la sonda encontró en las 7 filas. El límite residual del hash se asertó en un test en vez de darse por resuelto |
| 3 | W8 crea `.cursor/commands/wa-export.md` | Hizo falta además corregir `.gitignore`: excluía `/.cursor/commands/` entero, y git no consulta una negación dentro de un directorio excluido, así que el fichero habría quedado sin trackear. Es el mismo defecto que el Sprint 004 arregló para `/.claude/commands/` |

### Verificación ejecutada

| Comando | Resultado |
| :--- | :--- |
| `ruff check .` | exit `0` |
| `.venv/bin/python -m pytest -q` | 78 pasan (62 antes del sprint) |
| `wa-extract export-one --max-passes 12` | exit `3`, 301 mensajes, `complete: false`, `stopped_reason: max_passes` |
| Recuento por `kind` | `text: 276`, `voice: 10`, `image: 9`, `unknown: 6` |
| Fugas en el fichero | Sin `blob:`, sin `data:image`, sin `https://`, sin el nombre del contacto |
| `pip wheel . --no-deps --no-build-isolation` | exit `0` — fallaba antes por `README.md` ausente |
| `git -C .agents status --porcelain` | vacío |

El build necesitó `--no-build-isolation` y una instalación previa de
`setuptools` en `.venv`: el aislamiento de build exige red y el entorno del
agente no alcanza PyPI.

### Hallazgos abiertos, no resueltos en este sprint

| # | Hallazgo | Por qué no se toca aquí |
| :--- | :--- | :--- |
| 1 | 6 de 301 filas salen como `kind: unknown` — un medio que la sonda no vio (vídeo, documento, sticker o GIF) | El plan acepta explícitamente `unknown` para medios no reconocidos. Identificarlos exige otra sonda contra filas dispersas por el historial; candidato a Sprint 006 |
| 2 | Las 25 filas de media/`unknown` llevan `timestamp` de `H:MM` **sin fecha**, frente a `H:MM, D/M/YYYY` en las 273 de texto | La fecha solo vive en `data-pre-plain-text`, que las filas sin cuerpo no tienen. **No se sintetiza**: una fecha fabricada sería indistinguible de una medida, que es justo el fallo contra el que se escribió ADR-0003. Queda declarado en el blueprint y en el README, y `order` conserva la secuencia |
| 3 | `.cursor/commands/wa-export.md` es un fichero extra dentro del directorio que `commands_stale()` compara | Sin efecto práctico: en modo submódulo esa función ya devuelve `True` siempre (`UPSTREAM_FINDING_006`). Anotado allí |
| 4 | **`open_chat_by_query` no abre el chat y aun así reporta éxito** | Defecto **HIGH** heredado de `#003`, no introducido por este sprint. Detalle abajo. Excede W2–W12; requiere decisión de ruta (hotfix `RA-03` o Sprint 006) |

### Hallazgo 4 — la búsqueda no entra en el chat (HIGH)

Reportado por el operador el 2026-08-30: al lanzar el export, la búsqueda se
escribe pero **no entra en la conversación**; hay que clicarla a mano.

Tres fallos independientes, todos en `src/whatsapp_chat_extractor/export_one.py`:

| Línea | Qué hace | Por qué no detecta el fallo |
| :--- | :--- | :--- |
| `180-189` `_open_first_result` | Clica `#pane-side div[role="listitem"]` y hace `return` | Ese selector casa con la lista de chats normal, que existe haya o no resultados de búsqueda. Clica el primer elemento y retorna **sin verificar que se abriera una conversación** |
| `211` `open_chat_by_query` | Espera `MESSAGE_PANEL_SELECTORS` | Si ya hay una conversación abierta, el selector **ya está satisfecho** antes de buscar, así que la espera pasa al instante y el fallo es indetectable |
| `219-222` | `read_open_chat_title(page) or query`, y loguea `Opened chat for query=%r` | Lee el título de lo que haya abierto y **nunca lo compara con `query`** |

**Evidencia medida en esta sesión.** La sonda W2 lanzada con `--query "test"`
—una cadena que no nombra ningún chat— devolvió éxito y midió una ventana de 36
filas con 7 sin cuerpo, **idéntica** a la que devolvió después
`--query "<nombre real>"`. No es que `"test"` coincidiera: la función no abrió
nada y midió la conversación que ya estaba en pantalla. Una segunda ejecución de
`"test"`, con ninguna conversación abierta, sí falló con `RuntimeError`, que es
el comportamiento coherente con este diagnóstico.

**Impacto.** El cuelgue es el síntoma benigno, porque el operador lo ve. El grave
es el silencioso: si nadie clica, el export se escribe **sobre el chat
equivocado y sale con éxito**. Como `chat_id` es un digest y el título no se
almacena (contrato de identidad, `#004`), desde el fichero **no hay forma de
saber de qué conversación es**. Un corpus atribuido al cliente equivocado es
peor que un corpus ausente.

**Corrección propuesta**, a decidir por el humano, no aplicada aquí:

1. Restringir `SEARCH_RESULT_SELECTORS` al panel de resultados de búsqueda, no a
   `#pane-side` entero, sondeando el DOM primero (`KI-004-A`).
2. Antes de buscar, cerrar cualquier conversación abierta, o capturar el
   `chat_id` del panel actual para exigir que **cambie** tras la búsqueda. Una
   espera sobre un selector ya satisfecho no es una espera.
3. Comparar `read_open_chat_title()` con `query` y abortar cuando no encajen. El
   título ya se lee; hoy solo no se comprueba.
4. Test de regresión: un stub cuyo panel ya está abierto y cuya búsqueda no
   cambia nada debe hacer fallar `open_chat_by_query`, no pasar.
