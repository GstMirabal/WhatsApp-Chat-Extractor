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
| W2 | (scratchpad) sonda de `kind` contra el DOM en vivo | run | medium | `implementer_agent` | ⏳ |
| W3 | `src/whatsapp_chat_extractor/export_one.py` | modify | high | `implementer_agent` | ⏳ |
| W4 | `src/whatsapp_chat_extractor/writers.py` | modify | medium | `implementer_agent` | ⏳ |
| W5 | `src/whatsapp_chat_extractor/history.py` | modify | low | `implementer_agent` | ⏳ |
| W6 | `tests/test_row_fields.py` | modify | low | `implementer_agent` | ⏳ |
| W7 | `tests/test_writers.py` | modify | low | `implementer_agent` | ⏳ |
| W8 | `.cursor/commands/wa-export.md` | create | low | `skill_architect` | ⏳ |
| W9 | `README.md` | create | low | `doc_orchestrator` | ⏳ |
| W10 | `LICENSE` | create | low | `doc_orchestrator` | ⏳ |
| W11 | `docs/architecture/EXTRACTOR_BLUEPRINT.md` | modify | low | `doc_orchestrator` | ⏳ |
| W12 | `CHANGELOG.md` | modify | low | `doc_orchestrator` | ⏳ |

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
