# Estrategia de Contenido — El Noticiero de La Cotorra

Canal de sátira de las noticias de Cuba en claymation. Este documento recoge la
investigación (junio 2026) sobre qué funciona en Shorts animados y cómo se
traduce a este pipeline. Es la guía editorial y técnica del canal.

## 1. El diagnóstico

Un render técnicamente correcto NO es un video entretenido. Los tres errores
que matan la retención y que este pipeline debe evitar por defecto:

1. Planos largos y estáticos (el espectador hace swipe en 1-2 segundos).
2. Todo el chiste en el audio (la mayoría ve Shorts sin sonido).
3. Sin gancho: abrir con un plano general en vez de con el titular absurdo.

## 2. Reglas de retención (basadas en datos públicos de la industria)

| Regla | Valor | Por qué |
|---|---|---|
| Gancho | 0-2 segundos | Si el primer frame no detiene el scroll, el video no existe. Texto grande (4-7 palabras), visual impactante, movimiento inmediato. |
| Cortes | cada 2-4 segundos | Los Shorts de alto rendimiento promedian un "pattern interrupt" (corte, zoom, SFX) cada 2-4 s. |
| Subtítulos quemados | siempre | +15-25% de retención. El video debe funcionar EN SILENCIO. |
| Duración | 30-45 segundos | Suficiente para un sketch, corto para sostener retención. |
| Loop | el final conecta con el inicio | El replay involuntario cuenta como retención extra. |
| SFX | en cortes y datos clave | Whoosh en cortes, ding en el dato, sting de noticiero al abrir. |

La retención es la métrica dominante del algoritmo: un Short con 90% de
retención y pocos likes supera a uno con miles de likes y 30% de retención.

## 3. Estructura de guion: el sketch de 3 actos

```text
ACTO 1 — SETUP (0-5s):    el titular oficial REAL (la realidad ya es absurda;
                          el titular es el gancho — no hay que inventarlo).
ACTO 2 — ESCALADA (5-30s): 2-3 "golpes" sobre el mismo chiste, cada uno más
                          ridículo que el anterior. El orden importa:
                          de menor a mayor absurdo.
ACTO 3 — PUNCHLINE (30-40s): el remate más grande VA AL FINAL. Y se corta ahí.
                          Regla de oro: "no digas tres palabras más después
                          del punchline".
CIERRE — MULETILLA:       frase de marca recurrente que además cierra el loop:
                          "Y así están las cosas... totalmente normales."
```

## 4. Formatos del canal (de más fácil a más ambicioso)

1. **El Noticiero de La Cotorra** (serie ancla, diaria/semanal).
   Titular oficial real en pantalla → La Cotorra lo "traduce al cubano de a pie".
   Estructura: tarjeta de titular → cotorra en estudio → reportaje en escena
   (plaza/cocina/calle) → primer plano para el punchline.

2. **El Traductor**. Formato rapidísimo: frase oficial (texto en pantalla) →
   corte → la realidad actuada en la escena. Tres pares por video, escalando.

3. **Falso documental** ("El funcionario en su hábitat natural").
   Voz solemne de documental de naturaleza mientras la cámara "observa" al
   personaje. Formato probado en el humor cubano (parodia de NatGeo/Discovery).

4. **La entrevista imposible**. La Cotorra entrevista a un personaje que solo
   responde consignas. Requiere un segundo personaje (pendiente: asset).

5. **El choteo como identidad**: humor cubano de burla cotidiana, personajes
   icónicos recurrentes y muletillas — eso construye marca y fidelidad.

## 5. Por qué claymation es la ventaja competitiva

En la era de video IA genérico, lo artesanal se percibe como calidad y destaca
en el feed: textura táctil, imperfecciones visibles, calidez que lo digital no
replica, y nostalgia (la exposición infantil al stop-motion crea asociación
emocional con comodidad). Mantener SIEMPRE visible la textura de arcilla y la
cadencia de 12 fps ("on twos").

## 6. Mapeo a este pipeline

| Elemento editorial | Implementación en el repo |
|---|---|
| Gancho de titular | Tarjeta de apertura (`--hook "TITULAR"`) con sting de noticiero y zoom |
| Cortes cada 2-4s | Plan de noticiero con 6+ planos cortos y ángulos/escenas variados |
| Subtítulos quemados | Generados desde `--narration`, estilo grande con borde (`subtitles.py`) |
| SFX | Whoosh en cada corte + sting de apertura, sintetizados localmente (`sfx.py`) |
| Voz | piper-tts local en español (`tts.py`) |
| Vertical 9:16 | `--vertical` en plan/auto-director |
| Look plastilina | `style` con "claymation" → override de materiales arcilla |
| Historia en escenas | Plan noticiero: estudio → reportaje en plaza → primer plano |

Comando de producción de un episodio:

```bash
PYTHONPATH=src python3 -m ai_blender_director.cli auto-director \
  "la cotorra presenta las noticias de cuba estilo claymation" \
  --shots 6 --duration 2 --fps 12 --vertical --no-comfy \
  --hook "NO HAY APAGONES, HAY ROMANCE" \
  --narration "<guion satírico con estructura setup-escalada-punchline>" \
  --output-video renders/episodio_001.mp4
```

## 7. Flujo de trabajo editorial (por episodio)

1. Elegir UN titular oficial del día (Granma, mesa redonda, etc.). Uno solo.
2. Escribir el guion: titular → 2-3 golpes escalando → punchline → muletilla.
   40-60 palabras máximo (≈ 25-35 s de narración).
3. Elegir el texto del gancho: 4-7 palabras, el ángulo más absurdo del titular.
4. Ejecutar el comando de producción.
5. Revisar el preview; si funciona, re-render con `--profile final`.

## 8. Roadmap de mejoras del canal

- [x] Mascota original (La Cotorra) con pico articulado
- [x] TTS local en español
- [x] Vertical 9:16
- [x] Historia multi-escena (estudio → plaza → estudio)
- [x] Subtítulos quemados automáticos
- [x] Tarjeta de gancho + sting
- [x] SFX en cortes
- [ ] Música de fondo (colocar archivo en `assets/audio/music_bed.mp3` — usar música libre de derechos)
- [ ] Parpadeo/cejas de la cotorra (expresividad, cotorra_v2)
- [ ] Segundo personaje ("el de las consignas") para entrevistas
- [ ] Sincronía pico-voz (análisis de amplitud del WAV → keyframes del pico)
- [ ] Director LLM con OPENROUTER_API_KEY para guiones por noticia real
- [ ] Perfil final 1080x1920 para publicación

## 9. Fuentes

- GhostShorts — algoritmo de YouTube Shorts 2026: https://ghostshorts.com/es/blog/como-funciona-el-algoritmo-de-youtube-shorts-2026
- Crescitaly — ganchos y curiosity loops: https://blog.crescitaly.com/estrategia-crecimiento-youtube-shorts-hooks-curiosity-loops/
- Schedulala — duración ideal de Shorts: https://schedulala.com/es/blog/duracion-youtube-shorts
- OpusClip — formato y retención (data-backed): https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention
- AIR Media-Tech — edición para retención: https://air.io/en/youtube-hacks/advanced-retention-editing-cutting-patterns-that-keep-viewers-past-minute-8
- Speechify — subtítulos animados y engagement: https://speechify.com/blog/animated-subtitles/
- Celtx — cómo escribir un sketch: https://blog.celtx.com/how-to-write-a-skit/
- Final Draft — 10 consejos de los maestros del sketch: https://www.finaldraft.com/blog/10-sketch-writing-tips-on-writing-from-sketch-masters
- Morph Studio — claymation y nostalgia: https://www.morphstudio.com/article/claymation-a-journey-through-time-and-nostalgia
- Feedspot — 45 canales de sátira 2026: https://videos.feedspot.com/satire_youtube_channels/
