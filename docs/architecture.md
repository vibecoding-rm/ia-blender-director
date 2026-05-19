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
