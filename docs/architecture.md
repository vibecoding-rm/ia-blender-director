# Arquitectura MVP

## Principios

1. Blender es la fuente de verdad para geometria, camaras, luces, personajes y movimiento.
2. La IA no ejecuta acciones arbitrarias: produce especificaciones que el sistema valida.
3. Cada plano debe ser reproducible mediante archivo JSON, seed y assets versionados.
4. Los renders intermedios deben poder alimentar ComfyUI u otro backend visual.

## Flujo

```text
User Prompt
  -> Director
  -> ShotSpec JSON
  -> Validator
  -> Blender Render Worker
  -> Preview
  -> Vision Critic
  -> Revised ShotSpec
  -> Final Render
```

## Modelo Central

`ShotSpec` representa un plano individual:

- `scene`: descripcion breve del entorno.
- `style`: estilo visual.
- `duration_seconds`: duracion del plano.
- `fps`: frames por segundo.
- `resolution`: ancho y alto.
- `camera`: tipo de movimiento.
- `lighting`: descripcion de luz.
- `subject`: personaje u objeto principal.
- `action`: accion principal.
- `weather`: efecto ambiental opcional.
- `seed`: semilla reproducible.
- `character`: asset opcional de personaje.
- `environment`: asset opcional de escenario.
- `animation`: asset opcional de animacion.

## Asset Registry

Los assets se describen con manifiestos `asset.json`:

```text
assets/characters/<id>/asset.json
assets/environments/<id>/asset.json
assets/animations/<id>/asset.json
```

Campos base:

- `id`
- `type`
- `name`
- `source`
- `path`
- `metadata`

Si `path` es `null`, Blender usa un placeholder procedural. Esto permite estabilizar contratos antes de introducir assets reales.

## Fase 1

La Fase 1 solo busca probar control programatico:

- Crear escena.
- Crear objeto placeholder.
- Crear camara.
- Insertar keyframes.
- Renderizar imagen o animacion corta.

No incluye todavia IA generativa, ComfyUI ni agentes multiples.

## Fase 2

La Fase 2 convierte texto en `ShotSpec` usando reglas locales:

```text
Prompt
  -> generator.py
  -> generated/shots/*.json
  -> validator
  -> render_shot.py
```

Los presets iniciales soportados son:

- Escenas: cyberpunk street, procedural forest, interior room, desert stage, minimal stage.
- Camaras: orbit, dolly, push_in, static.
- Clima: rain, fog, snow.
- Sujetos: character, robot, vehicle, test subject.

Esta capa es deliberadamente simple. Su valor es establecer el contrato que despues debe cumplir un LLM.

## Render Jobs

Cada render se ejecuta dentro de una carpeta unica:

```text
renders/previews/<timestamp>_<scene_slug>_<shot_slug>/
  shot.json
  job.json
  manifest.json
  latest_preview.blend
  shot_0001-XXXX.mp4
  passes/
    beauty_frame_0001.png
    subject_mask_frame_0001.png
    depth_proxy_frame_0001.png
    normal_proxy_frame_0001.png
```

Esto evita pisar renders anteriores y permite comparar previews, repetir trabajos y auditar que spec produjo cada salida.

## Render Index

Los jobs tambien escriben eventos JSONL en:

```text
renders/index.jsonl
```

Eventos iniciales:

- `created`
- `dry_run`
- `started`
- `finished`

El indice es append-only para conservar historial aunque un job falle.

El comando `jobs` resume el ultimo evento conocido de cada job, y `show <job_id>` lee `job.json` y `manifest.json` para mostrar rutas de video, blend y passes.

## Control Passes

La primera version de passes genera imagenes estaticas del frame 1:

- `beauty`: render visual normal.
- `subject_mask`: mascara binaria aproximada del sujeto.
- `depth_proxy`: proxy de profundidad por distancia de objetos a camara.
- `normal_proxy`: proxy cromatico por posicion de objetos.

`depth_proxy` y `normal_proxy` son deliberadamente simples. Sirven para empezar a cablear ComfyUI y critic visual; mas adelante deben reemplazarse por pases tecnicos reales del compositor de Blender.
