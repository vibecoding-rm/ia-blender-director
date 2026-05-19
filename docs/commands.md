# Comandos

## Tests

```bash
make test
```

## Generar un shot desde texto

```bash
make generate PROMPT="calle cyberpunk nocturna con lluvia y camara orbitando al personaje"
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

## Ver comando Blender sin ejecutar

```bash
PYTHONPATH=src python3 -m ai_blender_director.cli render examples/shots/smoke_test.json --dry-run
```
