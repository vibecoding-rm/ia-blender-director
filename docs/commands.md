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
