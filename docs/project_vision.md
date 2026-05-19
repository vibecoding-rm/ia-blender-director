# Vision del Proyecto

## Idea Base

El proyecto busca crear un sistema local donde una persona pueda escribir una idea de video y una IA convierta esa idea en una produccion controlada dentro de Blender.

La meta no es generar un video como una caja negra. La meta es que la IA actue como director tecnico: interpreta la idea, la divide en planos, elige camara, luces, personaje, escenario, accion, animacion y estilo, genera una especificacion validada, controla Blender mediante scripts, revisa previews y mejora el resultado hasta producir un video final.

Flujo ideal:

```text
Idea del usuario
  -> IA Director
  -> guion tecnico / lista de planos
  -> ShotSpec validado
  -> seleccion de assets
  -> control de Blender
  -> preview
  -> critic visual
  -> correcciones
  -> render final
  -> ensamblaje de video
```

## Problema Que Resuelve

Crear videos 3D consistentes suele requerir muchas habilidades separadas:

- escribir la idea visual;
- modelar o importar assets;
- animar personajes;
- configurar camaras;
- iluminar escenas;
- renderizar;
- corregir errores visuales;
- editar el resultado final.

La idea del proyecto es automatizar esa cadena sin perder control. En vez de depender de una IA que genera un video cerrado e impredecible, usamos Blender como motor central porque permite reproducibilidad, versionado, control de camara, control de assets y renders auditables.

## Objetivo Principal

Construir una plataforma local de generacion de video con IA y Blender donde el usuario pueda dar una idea en lenguaje natural y el sistema produzca videos editables, reproducibles y escalables.

El objetivo final es:

```text
"Quiero un personaje caminando en una calle cyberpunk con lluvia,
camara orbitando, estilo cinematografico y luces neon"
```

y que el sistema pueda convertirlo en:

- uno o varios `shot.json`;
- una escena Blender;
- personajes y entornos seleccionados;
- animaciones aplicadas;
- camaras y luces configuradas;
- previews rapidos;
- passes de control;
- render final;
- manifiestos para auditar y repetir el resultado.

## Principios Del Proyecto

1. **Blender es la fuente de verdad.** La geometria, camara, luces, animacion y render se controlan en Blender.
2. **La IA propone, el sistema valida.** La IA no debe ejecutar codigo arbitrario ni romper el entorno. Debe producir especificaciones controladas.
3. **Todo debe ser reproducible.** Cada render debe poder repetirse con el mismo JSON, seed, assets y version del pipeline.
4. **Los assets deben ser versionados.** Personajes, escenarios, animaciones y materiales deben tener identificadores estables.
5. **Preview antes que render final.** El sistema debe iterar rapido antes de gastar tiempo en renders pesados.
6. **Escalar por modulos.** Director, generador, Blender worker, critic visual, assets, render farm y editor deben crecer como piezas separadas.
7. **Local primero.** El proyecto debe funcionar sin depender obligatoriamente de servicios pagos. APIs externas pueden sumarse despues, pero no deben ser el nucleo.

## Estado Actual

El proyecto ya tiene una base ejecutable:

- repo Git local;
- CLI `ai_blender_director`;
- validacion de `ShotSpec`;
- generador local de shots desde prompts simples;
- render jobs aislados;
- index de renders;
- previews con Blender;
- archivo `.blend` por job;
- video MP4 por job;
- passes de control iniciales;
- registro de assets para personajes, entornos y animaciones;
- placeholders procedurales para probar el contrato;
- tests automaticos.

Esto significa que el proyecto ya no es solo una idea: existe un pipeline minimo que convierte texto en especificacion y puede ejecutar Blender para generar previews.

## Arquitectura Deseada

El sistema completo se puede dividir en capas:

```text
Usuario
  -> Interfaz CLI o Web
  -> Director Agent
  -> Planner de escenas
  -> ShotSpec / SceneSpec
  -> Asset Registry
  -> Blender Render Worker
  -> Control Passes
  -> Vision Critic
  -> Editor / Ensamblador
  -> Video final
```

### Director Agent

Interpreta la idea del usuario y toma decisiones de direccion:

- tema del video;
- duracion aproximada;
- estilo visual;
- cantidad de planos;
- orden narrativo;
- tono;
- camaras;
- acciones;
- assets necesarios.

Su salida no debe ser codigo Python. Su salida debe ser datos estructurados que el sistema pueda validar.

### ShotSpec

Representa un plano individual. Define:

- escena;
- estilo;
- duracion;
- FPS;
- resolucion;
- camara;
- luz;
- sujeto;
- accion;
- clima;
- seed;
- personaje;
- entorno;
- animacion.

Este contrato es la pieza mas importante porque permite que cualquier IA o generador futuro controle Blender sin tocar directamente codigo peligroso.

### Asset Registry

El registro de assets permite trabajar con nombres estables:

```text
protagonista_v1
cyberpunk_street_v1
forest_v1
walk_v1
run_v1
idle_v1
```

Hoy esos assets son placeholders. Mas adelante cada asset puede apuntar a:

- `.blend`;
- `.glb`;
- `.fbx`;
- `.bvh`;
- texturas;
- materiales;
- rigs;
- colecciones Blender.

### Blender Render Worker

Es la capa que ejecuta Blender. Recibe un `shot.json`, crea la escena, aplica assets, configura camara y luces, anima, renderiza y escribe un manifiesto.

Debe seguir siendo determinista y auditable. Si un render falla, debe quedar registro del error, el spec usado y el job asociado.

### Vision Critic

En una fase posterior, un critic visual analizara previews y passes:

- sujeto fuera de cuadro;
- camara demasiado lejos;
- escena muy oscura;
- personaje oculto;
- composicion debil;
- animacion incorrecta;
- falta de consistencia entre planos.

El critic no reemplaza al usuario. Ayuda a iterar antes del render final.

### Editor / Ensamblador

Cuando el sistema pueda generar varios planos, necesitara unirlos:

- ordenar clips;
- agregar transiciones;
- musica;
- voz;
- subtitulos;
- efectos;
- color final;
- exportacion.

## Metas Por Fase

### Fase 1: Base Ejecutable

Meta: demostrar que Python puede controlar Blender de forma segura.

Incluye:

- validar JSON;
- crear escenas simples;
- mover camara;
- renderizar video corto;
- guardar outputs.

Estado: completado como MVP.

### Fase 2: Generador Local

Meta: convertir prompts simples en `shot.json` validos.

Incluye:

- presets de escenas;
- deteccion de camara;
- deteccion de clima;
- deteccion de personaje;
- deteccion de animacion;
- previews rapidos.

Estado: iniciado y funcional.

### Fase 3: Assets Reales

Meta: reemplazar placeholders por archivos reales.

Incluye:

- importar personajes riggeados;
- cargar escenarios `.blend` o `.glb`;
- aplicar animaciones `.fbx` o `.bvh`;
- normalizar escalas;
- versionar assets;
- validar que los archivos existan.

Esta fase es clave para mantener personajes consistentes entre videos.

### Fase 4: Director Agent

Meta: usar una IA para producir specs complejos, no solo reglas locales.

Incluye:

- prompt a guion tecnico;
- guion tecnico a lista de planos;
- lista de planos a `ShotSpec`;
- validacion estricta;
- reintentos si el JSON no es valido;
- memoria de estilo y personajes.

### Fase 5: Critic Visual

Meta: que el sistema pueda revisar su propio preview.

Incluye:

- generar passes de control;
- analizar frame inicial o varios frames;
- detectar problemas visuales;
- proponer cambios;
- regenerar el shot;
- comparar versiones.

### Fase 6: Videos Multi-Shot

Meta: pasar de un plano aislado a una secuencia completa.

Incluye:

- `SceneSpec`;
- continuidad de personaje;
- continuidad de escenario;
- continuidad de camara;
- renders por plano;
- ensamblaje con FFmpeg;
- manifiesto del video completo.

### Fase 7: Interfaz Web

Meta: operar el sistema sin depender solo de terminal.

Incluye:

- crear proyecto;
- escribir idea;
- revisar lista de planos;
- lanzar preview;
- comparar renders;
- aprobar render final;
- administrar assets.

### Fase 8: Escalabilidad

Meta: soportar mas volumen, mejor calidad y trabajos largos.

Incluye:

- cola de render jobs;
- workers separados;
- cache de assets;
- perfiles `preview`, `draft`, `final`;
- ejecucion por GPU si esta disponible;
- reintentos automaticos;
- historial consultable;
- empaquetado por proyecto.

## Escalabilidad Tecnica

El proyecto debe poder crecer sin reescribir todo. Para eso conviene mantener estos limites claros:

- `src/ai_blender_director/`: logica de CLI, validacion, jobs, indices y generacion.
- `scripts/blender/`: codigo que solo corre dentro de Blender.
- `assets/`: inventario versionado de recursos.
- `generated/`: specs generados por IA o reglas.
- `renders/`: outputs locales ignorados por Git.
- `docs/`: decisiones, arquitectura y roadmap.

Cuando el proyecto crezca, se pueden agregar modulos nuevos:

- `planner`: convierte una idea en escenas y planos;
- `critic`: analiza previews;
- `comfy`: conecta workflows de ComfyUI;
- `editor`: ensambla clips;
- `server`: API local;
- `ui`: interfaz web.

## Escalabilidad Creativa

Para crear videos mas desarrollados, el sistema debe aprender a mantener consistencia:

- mismo personaje entre planos;
- mismo vestuario;
- misma escala;
- mismo entorno;
- misma iluminacion;
- misma paleta visual;
- continuidad de accion;
- continuidad temporal.

La forma correcta de lograrlo es no depender solo del prompt. Debemos usar IDs de assets, seeds, manifests y specs versionados.

## Escalabilidad Operativa

Renderizar video puede ser costoso. El proyecto debe separar:

- preview rapido para iterar;
- render final para calidad;
- cache de escenas;
- cache de assets importados;
- jobs reanudables;
- logs claros;
- outputs por carpeta;
- manifests para auditoria.

Esto evita perder trabajo y permite comparar versiones.

## Riesgos Principales

1. **Demasiada libertad para la IA.** Si la IA controla Blender sin contrato, puede generar errores o resultados imposibles de reproducir.
2. **Assets sin normalizar.** Personajes y escenarios de distintas fuentes pueden tener escalas, rigs o materiales incompatibles.
3. **Render lento.** Sin perfiles de preview, la iteracion se vuelve demasiado pesada.
4. **Inconsistencia visual.** Sin asset IDs y manifests, cada video puede cambiar de personaje o estilo.
5. **Falta de evaluacion.** Sin critic visual, el sistema puede producir renders tecnicamente validos pero visualmente malos.

## Definicion De Exito

El proyecto sera exitoso cuando pueda hacer esto de forma repetible:

1. El usuario escribe una idea.
2. La IA propone una lista de planos.
3. El sistema valida cada plano.
4. Blender genera previews.
5. El sistema detecta problemas basicos.
6. Se corrigen specs.
7. Se renderiza la version final.
8. Se ensambla el video.
9. Todo queda guardado con manifests, assets y seeds.

## Siguiente Objetivo Recomendado

El siguiente paso mas importante es cargar assets reales desde el `Asset Registry`.

Orden recomendado:

1. agregar un personaje real o placeholder riggeado en `.blend` o `.glb`;
2. hacer que `render_shot.py` importe ese asset cuando `character` tenga `path`;
3. agregar un entorno real;
4. agregar una animacion real;
5. mantener fallback procedural si el asset no existe;
6. probar con un prompt que use personaje, entorno y animacion.

Despues de eso, conviene crear el primer `Director Agent` que genere varios planos desde una sola idea.
