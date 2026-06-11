# Guía de Escalado — El Noticiero de La Cotorra

Cómo crecer la producción del canal en cuatro ejes: guiones, producción,
distribución y monetización. Basado en lo construido hasta junio 2026 y en los
costos reales medidos en este pipeline.

---

## 1. Estado actual del sistema (qué ya escala)

| Pieza | Estado | Dónde |
|---|---|---|
| Elenco propio (licencia 100% nuestra) | La Cotorra (presentadora) + El Comandante Cerdo (portavoz) | `assets/characters/`, regenerables con `scripts/blender/export_*.py` |
| Episodio completo con 1 comando | gancho + 6 planos + voz + subtítulos + SFX | `auto-director` (ver `docs/commands.md`) |
| Lote nocturno | N episodios en secuencia, reanudable | `batch archivo.jsonl` |
| Voz en español ilimitada y gratis | piper-tts local | `assets/voices/` + `tts.py` |
| Gráficos generados que Blender usa | pantallas del estudio (logo, ÚLTIMA HORA, mapa) | `scripts/generate_screen_textures.py` |
| Formatos | vertical 9:16 (Shorts/TikTok/Reels) y 16:9 | flag `--vertical` |

Tiempos medidos en la laptop actual (3.7 GB RAM, CPU):
- Plano preview (3 s, 12 fps, 360x640): **~2-3 min**
- Episodio completo de 6 planos: **~20 min** → 1 episodio diario cómodo,
  lote de 7 episodios en una noche.

---

## 2. Eje 1 — Escalar guiones (el cuello de botella real)

El render ya es automático; escribir el chiste diario no. Plan:

### 2.1 Fuente automática de material
La prensa oficial cubana publica RSS (Granma, ACN, Cubadebate). Un script
diario que descargue los titulares entrega la materia prima sola — y la
realidad oficial ya viene escrita en tono de auto-sátira.

### 2.2 Director LLM (requiere `OPENROUTER_API_KEY` en `.env`)
El planner y el generator ya tienen el camino LLM implementado (se activa solo
con poner la key). Costo: centavos por guion con `google/gemini-2.0-flash-001`.
Convierte titular real → hook de 4-7 palabras + guion setup→escalada→punchline
+ plan de escenas específico. El humano queda como **editor que aprueba**, no
como escritor.

### 2.3 Objetivo de implementación
Comando `episodio-diario`: RSS → guion LLM → línea JSONL → se acumula en el
archivo de la semana → el `batch` nocturno lo produce. Revisión humana antes
de publicar (criterio editorial y control de calidad del chiste).

---

## 3. Eje 2 — Escalar producción (hardware)

### 3.1 Laptop actual (3.7 GB RAM, sin GPU) — lo que hay
- Sirve para: previews, episodios estándar, desarrollo, TTS.
- Límite: renders finales 1080x1920 arriesgados (RAM), nada de IA de imágenes.

### 3.2 i5 con 16 GB sin GPU — el siguiente paso natural
- Renders ~2x más rápidos y finales 1080p cómodos en lote nocturno.
- **Stable Diffusion en CPU se vuelve posible** (~1-3 min por imagen):
  fondos IA, carteles, miniaturas — generados de noche.
- Configuración recomendada de dos máquinas:
  - **i5 = nodo de render**: corre `batch` nocturno y finales.
  - **Laptop = dirección**: guiones, planes, revisión de previews.
- Migración: el proyecto es Git + scripts; en la máquina nueva hace falta
  Blender (tarball oficial 4.2 LTS), FFmpeg (apt), piper (pip) y la voz
  (curl desde HuggingFace). Los personajes se regeneran con sus scripts de
  export. (Pendiente: `setup.sh` que lo haga todo de una vez.)

### 3.3 GPU alquilada (~$0.56/hora, Vast.ai / RunPod) — el multiplicador barato
Costos reales estimados con una RTX 3090/4090 a ese precio:

| Tarea | Tiempo GPU | Costo |
|---|---|---|
| Render final 1080x1920 de un episodio | ~10-15 min | ~$0.10-0.15 |
| Estilización IA de un episodio (252 frames img2img + ControlNet depth) | ~5-10 min | ~$0.06-0.10 |
| **Lote semanal completo (7 episodios finales + estilización)** | ~2 h | **~$1.20** |
| Imágenes IA para texturas/miniaturas | segundos c/u | centavos |

A ese precio, una GPU usada de $250 tarda 2+ años en amortizarse: **alquilar
gana mientras el canal no facture**.

#### Flujo de trabajo con GPU alquilada (el pipeline YA lo soporta)
El cliente ComfyUI se conecta por HTTP usando `COMFY_URL` (`.env`):

1. Alquilar instancia con plantilla ComfyUI de un clic (arranca en ~2 min).
2. Túnel SSH hacia la instancia (no exponer el puerto público):
   `ssh -L 8188:localhost:8188 usuario@instancia`
3. En `.env`: `COMFY_URL=http://127.0.0.1:8188`
4. Ejecutar `auto-director`/`batch` SIN `--no-comfy`.
5. Blender local renderiza → frames + depth pass van a la GPU → vuelven
   estilizados → se ensamblan. Cero cambios de código.
6. **APAGAR LA INSTANCIA AL TERMINAR** (el único costo malo es olvidarla).

Pendiente para ese día: ajustar el workflow `stylization_v1` con prompt
claymation (hoy usa SD 1.5 con prompt genérico) y validar de punta a punta.

#### Estrategia mixta recomendada
- **Diario (gratis, local)**: episodios estándar — ya son publicables.
- **Semanal (~$1-2)**: sesión GPU de 2 h para finales + estilización.
- **Cuando el canal facture**: GPU propia (y entonces Unreal Engine se vuelve
  opción para el salto cinematográfico; con menos de eso, Blender es
  imbatible en control por código + gratis + local).

### 3.4 Optimizaciones locales pendientes (costo cero)
- **Cache de sets**: estudio/plaza se reconstruyen en cada render; guardar el
  `.blend` del set y solo re-posar cámara/personaje ahorraría ~40% del tiempo.
- Renderizar planos de un lote en paralelo cuando haya 2 máquinas.

---

## 4. Eje 3 — Escalar distribución

- **El mismo archivo vertical sirve sin cambios** para: YouTube Shorts,
  TikTok, Instagram Reels y Facebook Reels.
- **Facebook es prioritario**: es donde más cubanos (de a pie y diáspora)
  consumen video.
- **Consistencia**: publicar a hora fija; misma mascota, muletilla de cierre
  ("Y así están las cosas: totalmente normales"), misma estética claymation.
- **A/B de ganchos**: generar 2 tarjetas `--hook` distintas del mismo episodio
  cuesta casi nada; publicar variantes en plataformas distintas y aprender qué
  titular detiene más el scroll.
- Los subtítulos van quemados: el video funciona en silencio en cualquier
  plataforma sin configurar nada.

---

## 5. Eje 4 — Escalar monetización

1. **Fase embudo (ahora)**: Shorts para crecer. Requisito del programa de
   YouTube: 1.000 subs + 10M vistas de Shorts en 90 días — es la meta, no el
   ingreso inicial.
2. **Apoyo directo desde el video #1**: la diáspora cubana apoya contenido
   crítico — membresías, Patreon, donaciones. Mencionarlo en la muletilla de
   cierre de vez en cuando.
3. **Videos largos 16:9** (mejor RPM que Shorts): compilación semanal
   "Lo mejor del Noticiero" (3-5 min) — el pipeline ya hace 16:9 quitando
   `--vertical`; concatenar los episodios de la semana es un comando ffmpeg.
4. **La marca**: La Cotorra y El Comandante Cerdo son personajes originales
   del canal (modelados por script, licencia propia) — registrables,
   merchandizables, sin riesgo de copyright.

---

## 6. Roadmap de escalado (orden recomendado)

1. [x] Cola nocturna `batch` (producción)
2. [ ] `setup.sh` de instalación para la máquina i5 (producción)
3. [ ] `OPENROUTER_API_KEY` + comando `episodio-diario` con RSS (guiones)
4. [ ] Compilación semanal 16:9 automática (monetización)
5. [ ] Workflow ComfyUI claymation + prueba con GPU alquilada (calidad)
6. [ ] Sincronía pico-voz por amplitud del WAV (calidad)
7. [ ] Set de entrevista (dos personajes en plano) → formato "entrevista imposible"
8. [ ] Cache de sets en `.blend` (velocidad)
9. [ ] GPU propia / Unreal (solo cuando haya ingresos que lo justifiquen)
