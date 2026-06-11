# IA Blender Director — El Noticiero de La Cotorra

Pipeline local para producir videos animados (sátira de noticias en claymation)
dirigiendo Blender desde especificaciones estructuradas. La IA propone specs
JSON validados — nunca ejecuta código arbitrario — y Blender es la fuente de
verdad. Todo es reproducible: mismo JSON + seed + assets = mismo video.

```text
Idea / titular
  -> Director Agent (plan de planos)
  -> shot.json validado
  -> Blender (sets, personajes, animación, render)
  -> Vision Critic
  -> Postproducción (gancho, voz TTS, subtítulos, SFX)
  -> Short listo para publicar
```

## Estado Actual

Producción de episodios completos con un comando:

- **Elenco original** (licencia propia, generado por script): La Cotorra
  (presentadora, pico articulado, parpadeo) y El Comandante Cerdo (portavoz
  del régimen, mandíbula y dedo acusador).
- **Sets procedurales**: estudio de noticias con pantallas de gráficos
  generados, plaza habanera, cocina, calle cyberpunk, bosque, desierto.
- **Estilo claymation** automático (materiales de arcilla + 12 fps).
- **Postproducción Shorts**: tarjeta de gancho con sting, narración TTS en
  español (piper, local), subtítulos quemados, whoosh en cada corte.
- **Formato vertical 9:16** (`--vertical`) y 16:9.
- **Cola nocturna**: `batch semana.jsonl` produce N episodios en secuencia.
- Critic visual con passes de control, índice de jobs, servidor FastAPI + web UI.

Documentación clave:

- `docs/estrategia_contenido.md` — guía editorial (retención, formatos, guiones).
- `docs/escalado.md` — plan de crecimiento (hardware, GPU alquilada, costos).
- `docs/commands.md` — recetario de comandos.
- `docs/project_vision.md` — visión y principios del proyecto.

## Requisitos

- Python 3.12+
- Blender instalado y disponible como `blender` en el PATH para renderizar.
- FFmpeg para inspeccionar, ensamblar y convertir videos.

En este equipo quedaron verificados Blender 4.2.21 LTS (instalado en `/opt/blender-4.2.21-linux-x64`, symlink en `/usr/local/bin/blender`) y FFmpeg 8.1.1.

## Uso

Generar un plano desde texto:

```bash
make generate PROMPT="calle cyberpunk nocturna con lluvia y cámara orbitando al personaje"
```

Generar y renderizar en un solo paso:

```bash
make create PROMPT="bosque con niebla y camara fija con personaje mirando a camara"
```

Validar un plano:

```bash
PYTHONPATH=src python3 -m ai_blender_director.cli validate examples/shots/cyberpunk_orbit.json
```

Ver el comando que ejecutaría Blender:

```bash
PYTHONPATH=src python3 -m ai_blender_director.cli blender-command examples/shots/cyberpunk_orbit.json --output renders/previews
```

Cuando Blender esté instalado:

```bash
make render SHOT=examples/shots/cyberpunk_orbit.json
```

Cada render crea una carpeta unica dentro de `renders/previews/` con:

- `shot.json`: copia exacta del spec usado.
- `job.json`: manifest creado antes de ejecutar Blender.
- `manifest.json`: manifest escrito por Blender despues del render.
- `latest_preview.blend`: escena generada.
- `shot_0001-XXXX.mp4`: video renderizado.
- `passes/`: imagenes de control para IA visual y critic automatico.

Cada job tambien agrega eventos a `renders/index.jsonl`.

Consultar historial:

```bash
make jobs
PYTHONPATH=src python3 -m ai_blender_director.cli show <job_id>
```

Perfiles:

- `preview`: baja resolucion relativa, menos samples, iteracion rapida.
- `final`: resolucion completa del spec y mas samples.

Atajos:

```bash
make test
make generate
make create
make jobs
make validate
make render SHOT=generated/shots/calle_cyberpunk_nocturna_con_lluvia_y_camara_orbitando_al_personaje.json
make render SHOT=examples/shots/cyberpunk_orbit.json PROFILE=final
make smoke-render
```

## Estructura

```text
src/ai_blender_director/   CLI, modelos y validación
scripts/blender/           Scripts ejecutados dentro de Blender
examples/shots/            Planos de ejemplo
assets/                    Personajes, entornos, animaciones y materiales
renders/                   Salidas locales ignoradas por Git
workflows/comfy/           Workflows futuros de ComfyUI
docs/                      Arquitectura y roadmap
```

## Documentacion

- [Vision del proyecto](docs/project_vision.md): idea base, objetivos, metas, escalabilidad y fases.
- [Arquitectura MVP](docs/architecture.md): contrato tecnico actual y flujo de render.
- [Roadmap](docs/roadmap.md): plan por semanas.
- [Comandos](docs/commands.md): uso practico de la CLI y Makefile.

## Assets

Los shots pueden referenciar assets versionados:

```json
{
  "character": "protagonista_v1",
  "environment": "cyberpunk_street_v1",
  "animation": "walk_v1"
}
```

Cada asset vive con un `asset.json`:

```text
assets/characters/protagonista_v1/asset.json
assets/environments/cyberpunk_street_v1/asset.json
assets/animations/walk_v1/asset.json
```

Por ahora son placeholders procedurales. Cuando agreguemos archivos reales (`.blend`, `.glb`, `.fbx`), el mismo contrato seguirá funcionando.

## Próximo Objetivo

El siguiente paso técnico es reemplazar el generador local por un `Director Agent` que produzca el mismo `shot.json` validado, sin darle permisos directos para ejecutar Python arbitrario.
