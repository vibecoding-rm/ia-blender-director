# Guía de Contribución

¡Gracias por tu interés en contribuir a **IA Blender Director**! Este documento explica cómo colaborar de forma efectiva.

## Código de Conducta

Este proyecto adopta un ambiente respetuoso y colaborativo. Se espera que todos los participantes mantengan un trato profesional y constructivo.

## ¿Cómo Contribuir?

### Reportar Bugs

1. Verifica que el bug no haya sido reportado ya en [Issues](../../issues).
2. Abre un nuevo issue usando la plantilla **Bug Report**.
3. Incluye:
   - Descripción clara del problema.
   - Pasos para reproducirlo.
   - Comportamiento esperado vs. actual.
   - Versión de Python, Blender y sistema operativo.
   - Logs relevantes (sin credenciales).

### Proponer Nuevas Funcionalidades

1. Abre un issue usando la plantilla **Feature Request**.
2. Describe el caso de uso y por qué encaja con la visión del proyecto.
3. Espera feedback antes de empezar a implementar.

### Enviar Pull Requests

1. **Fork** el repositorio y crea una rama descriptiva:
   ```bash
   git checkout -b feat/director-agent-llm
   ```
2. Sigue el estilo de código del proyecto (PEP 8, type hints, docstrings).
3. Añade o actualiza tests si tu cambio afecta lógica existente.
4. Asegúrate de que todos los tests pasan:
   ```bash
   make test
   ```
5. Abre un Pull Request con:
   - Título claro y conciso.
   - Descripción del cambio y motivación.
   - Referencia al issue relacionado (`Closes #N`).

## Convenciones de Commits

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

```
feat:     nueva funcionalidad
fix:      corrección de bug
docs:     cambios en documentación
refactor: refactorización sin cambio de comportamiento
test:     añadir o corregir tests
chore:    mantenimiento (deps, CI, configuración)
```

Ejemplos:
```
feat: add LLM-based Director Agent for multi-shot planning
fix: handle missing blender executable gracefully
docs: update architecture diagram with Phase 4
```

## Estructura del Proyecto

```text
src/ai_blender_director/   Lógica principal (CLI, modelos, validación)
scripts/blender/           Scripts ejecutados dentro de Blender
assets/                    Assets versionados (personajes, entornos, animaciones)
examples/shots/            ShotSpecs de ejemplo
docs/                      Documentación técnica y de arquitectura
tests/                     Suite de tests
```

## Entorno de Desarrollo

```bash
# Clonar y configurar entorno virtual
git clone https://github.com/TU_USUARIO/ia-blender-director.git
cd ia-blender-director
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Copiar variables de entorno
cp .env.example .env
# Editar .env con tus claves

# Correr tests
make test
```

## Áreas Donde Se Necesita Ayuda

- 🤖 **Director Agent** — integración con LLMs para generar `ShotSpec` desde prompts complejos.
- 🎭 **Assets reales** — personajes riggeados `.blend`/`.glb` con licencia libre.
- 🎬 **Multi-shot** — pipeline para secuencias de planos y ensamblaje con FFmpeg.
- 🔍 **Vision Critic** — análisis automático de previews con modelos de visión.
- 🌐 **Web UI** — mejoras al servidor FastAPI y la interfaz web.
- 📚 **Documentación** — tutoriales, ejemplos y traducciones.

## Preguntas

Abre un [Discussion](../../discussions) o un issue con el label `question`.
