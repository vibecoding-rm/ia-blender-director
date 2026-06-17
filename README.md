# IA Blender Director

> **Pipeline local con IA para producir videos animados en estilo claymation — "El Noticiero de La Cotorra"**

[![CI](https://github.com/devmaikelrm/ia-blender-director/actions/workflows/ci.yml/badge.svg)](https://github.com/devmaikelrm/ia-blender-director/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Blender 4.2 LTS](https://img.shields.io/badge/blender-4.2%20LTS-orange.svg)](https://www.blender.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ¿Qué es esto?

**IA Blender Director** es un pipeline local que convierte una idea escrita en lenguaje natural en un video animado listo para publicar — sin depender de servicios de generación de video cerrados.

La IA actúa como **director técnico**: interpreta la idea, divide en planos, elige cámara, luces, personajes, escenarios y estilo, genera una especificación JSON validada y controla Blender mediante scripts. Blender es siempre la fuente de verdad. **La IA propone — nunca ejecuta código arbitrario.**

```text
Idea / titular
  → Director Agent (plan de planos)
  → shot.json validado
  → Blender (sets, personajes, animación, render)
  → Vision Critic
  → Postproducción (gancho, voz TTS, subtítulos, SFX)
  → Short listo para publicar
```

El proyecto está orientado a producir sátira de noticias con personajes propios en estilo claymation, publicable como Shorts verticales 9:16.

---

## Características

| Funcionalidad | Estado |
|---|---|
| CLI `ai-blender-director` | ✅ Funcional |
| Validación de `ShotSpec` (JSON Schema + Pydantic) | ✅ Funcional |
| Generador local de shots desde prompts | ✅ Funcional |
| Render jobs aislados con manifesto | ✅ Funcional |
| Índice JSONL de renders | ✅ Funcional |
| Sets procedurales (cyberpunk, forest, desert, etc.) | ✅ Funcional |
| Estilo claymation automático | ✅ Funcional |
| Personajes propios: La Cotorra + El Comandante Cerdo | ✅ Funcional |
| Formato vertical 9:16 (`--vertical`) | ✅ Funcional |
| Postproducción Shorts (gancho, TTS, subtítulos, SFX) | ✅ Funcional |
| Cola nocturna (`batch semana.jsonl`) | ✅ Funcional |
| Servidor FastAPI + Web UI | ✅ Funcional |
| Critic visual con passes de control | ✅ Funcional |
| Director Agent con LLM | 🔄 En desarrollo |
| Assets reales riggeados | 🔄 En desarrollo |
| Videos multi-shot (SceneSpec) | 🔄 Roadmap |

---

## Requisitos

- **Python 3.12+**
- **Blender 4.2 LTS** — instalado y disponible como `blender` en el PATH
- **FFmpeg** — para inspeccionar, ensamblar y convertir videos
- **Piper TTS** *(opcional)* — para narración local en español

> Verificado con Blender 4.2.21 LTS y FFmpeg 8.1.1 en Linux.

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/devmaikelrm/ia-blender-director.git
cd ia-blender-director

# 2. Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 3. Instalar el paquete en modo editable
pip install -e .

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus claves (ver sección Configuración)
```

---

## Configuración

Copia `.env.example` a `.env` y completa los valores:

```ini
# API key de Google AI (para el Director Agent)
GOOGLE_API_KEY=tu_api_key_aqui

# URL de ComfyUI (por defecto: local)
COMFY_URL=http://127.0.0.1:8188

# Ejecutable de Blender
BLENDER_EXECUTABLE=blender

# Servidor FastAPI
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
```

> ⚠️ **Nunca subas tu `.env` al repositorio.** Ya está en `.gitignore`.

---

## Uso Rápido

### Generar un plano desde texto

```bash
make generate PROMPT="calle cyberpunk nocturna con lluvia y cámara orbitando al personaje"
```

### Generar y renderizar en un solo paso

```bash
make create PROMPT="bosque con niebla y cámara fija con personaje mirando a cámara"
```

### Validar un spec antes de renderizar

```bash
make validate SHOT=examples/shots/cyberpunk_orbit.json
```

### Renderizar un spec existente

```bash
make render SHOT=examples/shots/cyberpunk_orbit.json PROFILE=preview
# o para calidad final:
make render SHOT=examples/shots/cyberpunk_orbit.json PROFILE=final
```

### Ver el historial de renders

```bash
make jobs
```

### Inspeccionar un job específico

```bash
PYTHONPATH=src python3 -m ai_blender_director.cli show <job_id>
```

### Smoke test rápido

```bash
make smoke-render
```

---

## Perfiles de Render

| Perfil | Resolución | Uso |
|---|---|---|
| `preview` | Baja, pocos samples | Iteración rápida |
| `final` | Completa según spec | Publicación |

---

## Outputs de un Render

Cada job crea una carpeta única en `renders/previews/`:

```text
renders/previews/<timestamp>_<scene>_<shot>/
  shot.json          ← copia exacta del spec usado
  job.json           ← manifiesto pre-render
  manifest.json      ← manifiesto escrito por Blender
  latest_preview.blend
  shot_0001-XXXX.mp4
  passes/
    beauty_frame_0001.png
    subject_mask_frame_0001.png
    depth_proxy_frame_0001.png
    normal_proxy_frame_0001.png
```

Todos los jobs también quedan registrados en `renders/index.jsonl` (append-only).

---

## Estructura del Proyecto

```text
src/ai_blender_director/   CLI, modelos, validación, servidor
scripts/blender/           Scripts ejecutados dentro de Blender
assets/
  characters/              Personajes con asset.json por versión
  environments/            Escenarios con asset.json por versión
  animations/              Animaciones con asset.json por versión
  voices/                  Modelos TTS locales (excluidos del repo)
examples/shots/            ShotSpecs de ejemplo listos para usar
generated/shots/           Shots generados por CLI (excluidos del repo)
renders/                   Outputs locales (excluidos del repo)
workflows/comfy/           Workflows de ComfyUI (futuro)
docs/                      Documentación técnica y editorial
tests/                     Suite de tests unitarios
web/                       Interfaz web del servidor FastAPI
```

---

## Personajes

| Personaje | Descripción |
|---|---|
| **La Cotorra** | Presentadora. Pico articulado, parpadeo, presentación de noticias. |
| **El Comandante Cerdo** | Portavoz del régimen. Mandíbula articulada, dedo acusador. |

Ambos son personajes originales generados por scripts propios con licencia propia. No contienen assets de terceros.

---

## Arquitectura

Ver [`docs/architecture.md`](docs/architecture.md) para el flujo técnico completo y el contrato de `ShotSpec`.

```text
User Prompt
  → Director Agent
  → ShotSpec JSON (validado)
  → Blender Render Worker
  → Preview + Control Passes
  → Vision Critic
  → Revised ShotSpec
  → Final Render
  → Postproducción (TTS, subtítulos, SFX, gancho)
  → Short listo para publicar
```

**Principios clave:**
1. Blender es la fuente de verdad para geometría, cámaras, luces y animación.
2. La IA produce especificaciones — nunca ejecuta código arbitrario.
3. Todo render es reproducible: mismo JSON + seed + assets = mismo video.
4. Local primero: el core no depende de servicios externos de pago.

---

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/project_vision.md`](docs/project_vision.md) | Visión, principios, metas por fase y definición de éxito |
| [`docs/architecture.md`](docs/architecture.md) | Contrato técnico actual, ShotSpec y flujo de render |
| [`docs/roadmap.md`](docs/roadmap.md) | Plan de desarrollo por semanas |
| [`docs/commands.md`](docs/commands.md) | Recetario completo de comandos |
| [`docs/escalado.md`](docs/escalado.md) | Plan de crecimiento, hardware, GPU y costos |
| [`docs/estrategia_contenido.md`](docs/estrategia_contenido.md) | Guía editorial: retención, formatos, guiones |

---

## Tests

```bash
make test
# o directamente:
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

---

## Roadmap

- **Fase 3** → Assets reales riggeados (`.blend` / `.glb`)
- **Fase 4** → Director Agent con LLM (genera `ShotSpec` desde prompts complejos)
- **Fase 5** → Critic visual automático con modelos de visión
- **Fase 6** → Videos multi-shot con `SceneSpec` y ensamblaje
- **Fase 7** → Web UI completa
- **Fase 8** → Escalabilidad, cola de workers, GPU alquilada

Ver [`docs/roadmap.md`](docs/roadmap.md) para detalle semana a semana.

---

## Contribuir

¡Las contribuciones son bienvenidas! Lee la [Guía de Contribución](CONTRIBUTING.md) antes de abrir un Pull Request.

Áreas prioritarias:
- 🤖 Director Agent con LLM
- 🎭 Assets 3D con licencia libre
- 🔍 Vision Critic
- 🌐 Mejoras Web UI

---

## Licencia

Este proyecto está bajo la [Licencia MIT](LICENSE).

Los personajes (La Cotorra, El Comandante Cerdo) son creaciones originales del autor y parte de este mismo repositorio bajo la misma licencia.

---

<p align="center">
  Hecho con Python, Blender y demasiado café ☕
</p>
