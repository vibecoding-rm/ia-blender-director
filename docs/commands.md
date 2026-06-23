# Comandos

## Tests

```bash
make test
```

## Generar un shot desde texto

```bash
make generate PROMPT="calle cyberpunk nocturna con lluvia y camara orbitando al personaje"
```

## Generar y renderizar

```bash
make create PROMPT="bosque con niebla y camara fija con personaje mirando a camara"
```

Sin render:

```bash
PYTHONPATH=src python3 -m ai_blender_director.cli create "bosque con niebla"
```

El generador local puede rellenar assets placeholder:

```json
"character": "protagonista_v1",
"environment": "forest_v1",
"animation": "idle_v1"
```

Listar assets registrados:

```bash
PYTHONPATH=src python3 -m ai_blender_director.cli assets
PYTHONPATH=src python3 -m ai_blender_director.cli assets --type character
```

Validar el catalogo de assets:

```bash
make validate-assets
PYTHONPATH=src python3 -m ai_blender_director.cli validate-assets --type character
PYTHONPATH=src python3 -m ai_blender_director.cli validate-assets --blender
```

## Validar un shot

```bash
make validate SHOT=examples/shots/cyberpunk_orbit.json
```

## Renderizar

```bash
make render SHOT=examples/shots/smoke_test.json
```

El render crea una carpeta unica dentro de `renders/previews/`.
Tambien registra eventos en `renders/index.jsonl`.

## Listar jobs

```bash
make jobs
```

Mostrar un job especifico:

```bash
PYTHONPATH=src python3 -m ai_blender_director.cli show 20260519T154510Z
```

Render final:

```bash
make render SHOT=examples/shots/cyberpunk_orbit.json PROFILE=final
```

## Ver comando Blender sin ejecutar

```bash
PYTHONPATH=src python3 -m ai_blender_director.cli render examples/shots/smoke_test.json --profile preview --dry-run
```

## Producir un episodio del Noticiero (Short completo)

Pipeline completo: Director Agent → renders Blender → critic → postproducción
(gancho con sting, narración TTS, whoosh en cortes, subtítulos quemados).

```bash
PYTHONPATH=src python3 -m ai_blender_director.cli auto-director \
  "la cotorra presenta las noticias de cuba estilo claymation" \
  --shots 6 --duration 3 --fps 12 --vertical --no-comfy \
  --hook "TITULAR ABSURDO EN 4-7 PALABRAS" \
  --narration "Guion satírico con estructura setup → escalada → punchline." \
  --output-video renders/episodio_XXX.mp4
```

Flags de postproducción:

- `--hook "TEXTO"`: tarjeta de apertura de 1.4s con titular gigante y sting.
- `--narration "TEXTO"`: voz en español (piper-tts) + subtítulos quemados.
- `--voice ruta.onnx`: otra voz piper (default: assets/voices/es_MX-claude-high.onnx).
- `--voice-character cotorra_v1`: usa la voz configurada para ese `asset_id`
  en `TTS_CHARACTER_VOICES` si no se pasa `--voice`.
- `--vertical`: 720x1280 (Shorts/TikTok/Reels).
- `--no-subtitles` / `--no-sfx` / `--no-comfy`: desactivar pasos.
- Música de fondo: colocar `assets/audio/music_bed.mp3` (se mezcla a volumen bajo automáticamente).

Con `--shots 6` o más y un prompt de noticiero, el plan alterna estudio/plaza
con ángulos distintos por plano (un corte cada `--duration` segundos).

La guía editorial completa está en `docs/estrategia_contenido.md`.

## Lote nocturno de episodios

Producir una semana completa mientras duermes:

```bash
PYTHONPATH=src python3 -m ai_blender_director.cli batch examples/episodios/semana_ejemplo.jsonl
```

- El archivo es JSONL: una línea JSON por episodio con `id`, `prompt`, `hook`,
  `narration`, `voice_character` (defaults: 6 planos de 3s, 12 fps, vertical).
- Reanudable: los episodios cuyo MP4 ya existe se saltan (`--force` para repetir).
- Un episodio fallido no detiene el lote; al final imprime resumen con tiempos.
- `--dry-run` valida el archivo y lista lo que produciría sin renderizar.
- Salida: `renders/episodios/<id>.mp4`.

## Regenerar personajes y gráficos

```bash
blender --background --python scripts/blender/export_cotorra.py   # La Cotorra
blender --background --python scripts/blender/export_cerdo.py     # El Comandante Cerdo
python3 scripts/generate_screen_textures.py                       # pantallas del estudio
```
