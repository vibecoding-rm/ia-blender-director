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
blender --background --python scripts/blender/render_shot.py -- examples/shots/cyberpunk_orbit.json renders/previews
```

Atajos:

```bash
make test
make validate
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

El siguiente paso técnico es hacer que un prompt genere un `shot.json` válido, primero con reglas locales y después con un LLM.
