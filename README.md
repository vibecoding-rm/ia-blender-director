# IA Blender Director

Pipeline local para dirigir Blender desde especificaciones estructuradas.

La idea del proyecto no es que una IA use el escritorio sin control. El flujo base es:

```text
Prompt creativo
  -> shot.json validado
  -> script bpy en Blender
  -> preview/render
  -> critic visual y correcciones
  -> render final
```

## Estado Actual

Este repo arranca con un MVP:

- Esquema Python para validar planos (`ShotSpec`).
- CLI local para validar y preparar comandos de render.
- Script Blender `bpy` que crea una escena simple con cámara, luz, objeto, keyframes y render.
- Ejemplo en `examples/shots/cyberpunk_orbit.json`.
- Tests básicos sin dependencias externas.

## Requisitos

- Python 3.12+
- Blender instalado y disponible como `blender` en el PATH para renderizar.
- FFmpeg para inspeccionar, ensamblar y convertir videos.

En este equipo quedaron verificados Blender 4.0.2 y FFmpeg 6.1.1.

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

Perfiles:

- `preview`: baja resolucion relativa, menos samples, iteracion rapida.
- `final`: resolucion completa del spec y mas samples.

Atajos:

```bash
make test
make generate
make create
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

## Próximo Objetivo

El siguiente paso técnico es reemplazar el generador local por un `Director Agent` que produzca el mismo `shot.json` validado, sin darle permisos directos para ejecutar Python arbitrario.
