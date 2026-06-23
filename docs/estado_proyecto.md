# Estado del Proyecto — *El Noticiero de La Cotorra*

> Snapshot del avance (junio 2026). Resume el reparto, las capacidades del pipeline,
> el entorno y las limitaciones conocidas. Complementa la [biblia de personajes](personajes.md)
> y la [visión](project_vision.md).

---

## 1. Reparto

### Modelados (GLB riggeado + `asset.json` + alta en el planner) ✅

| Personaje | `asset_id` | Forma | Rig (lip-sync) | Estado |
|---|---|---|---|---|
| La Cotorra | `cotorra_v1` | perica presentadora | pico `Beak` | ✅ |
| Comandante Cerdo | `comandante_cerdo_v1` | cerdo vocero | mandíbula | ✅ |
| Humbrete | `humbrete_v1` | bulldog fiscal | `Jaw` | ✅ |
| Ciberclarias | `ciberclarias_v1` | bagre (enjambre) | `Jaw` | ✅ (`swarm`) |
| Michelito Filo | `michelito_v1` | gallo navaja | `Beak` | ✅ |
| Gaby Filo | `gaby_v1` | lechuza de teleprompter | `Beak` | ✅ |
| Randy Redondo | `randy_v1` | tortuga de mesa | `Jaw` | ✅ |
| Guerrero de Lata | `guerrero_v1` | armadura anónima | visera `Jaw` | ✅ |
| El Guanajo Designado | `guanajo_v1` | pavo marioneta | pico `Beak` | ✅ |
| El Caimán General | `caiman_v1` | cocodrilo militar titiritero | `Jaw` | ✅ |

Cada uno tiene acciones NLA **Idle / Talk / Walk** y huesos de ojos para parpadeo. Los `export_*.py`
viven en `scripts/blender/` y los GLB fueron **construidos y verificados** en Blender 4.2.

### Documentados / banco de reserva (definidos, sin modelar) 📝

- **Aparato (TV/digital):** Arleen Chapea (jutía), Brigada Copy-Paste (clones),
  Lázaro Mediodía (hurón), Fantasma de la Pupila (retrato).
- **Cúpula y aliados:** Gerardo el Chivatón (jefe CDR), Marrero el Conserje 5★ (PM),
  Bruno Bloqueo (canciller),
  El Trovador del Picadillo de Soya (artistas oficialistas).

Todos con diseño 3D, gags, voz y `asset_id` sugerido en [`personajes.md`](personajes.md).

---

## 2. Capacidades del pipeline (implementadas y con tests)

| Capacidad | Dónde | Notas |
|---|---|---|
| **Lip-sync por audio** | `lipsync.py` + `scripts/blender/ai_director/lipsync.py` | Rhubarb → hueso `Jaw`/`Beak`; degrada elegante sin el binario |
| **Lip-sync end-to-end multi-shot** | `commands/pipeline.py` (`_prepare_lipsync`) | sintetiza voz antes del render, inyecta visemas por plano (`narration_offset`) |
| **Gráficos broadcast** | `broadcast.py` | lower-third, ticker desplazable, bug "ÚLTIMA HORA"; auto-activados en escenas de noticiero |
| **TTS pluggable** | `tts.py` + `config.py` | `piper` (default) / `xtts` / `command`; fallback a piper; voces por `asset_id` con `TTS_CHARACTER_VOICES` |
| **Director Agent (LLM)** | `planner.py` | JSON-mode robusto por defecto; Instructor **opt-in** (`director_use_instructor`) |
| **Multi-shot dirigido** | `auto-director --shots N` | default **4** planos (ritmo de retención) |
| **Calidad profesional** | `--profile final`, `generation.py` | 1080×1920, 128 samples, raytracing; vertical 9:16 |
| **Render EEVEE** | `scripts/blender/ai_director/` | AgX, GTAO, bloom, raytracing, motion blur, DOF, easing, claymation (subsurface+huellas) |
| **Encoding/audio** | `postproduction.py`, `sfx.py` | H.264 CRF 18, `+faststart`, audio `loudnorm` -14 LUFS |

Suite de tests: **110/110 verde**.

---

## 3. Entorno y dependencias

| Componente | Estado en esta máquina |
|---|---|
| Python | 3.14 |
| Blender | 4.2.3 LTS (`C:/Program Files/Blender Foundation/Blender 4.2`) |
| FFmpeg | disponible |
| piper-tts + voz es (`es_MX-claude-high.onnx`) | ✅ instalado (síntesis verificada) |
| Rhubarb 1.14.0 | ✅ en PATH (lip-sync verificado) |
| instructor | ✅ instalado (extra `director`) |
| Claves | `.env` local (gitignored): `OPENROUTER_API_KEY`, `VAST_API_KEY` — **rotar tras pruebas** |

**GPU en la nube:** `scripts/provision_gpu.sh` deja lista una caja Linux de Vast.ai
(Blender + ffmpeg + piper + rhubarb + paquete).

---

## 4. Cómo correr

```bash
# Preview rápido local (sin GPU; útil para iterar encuadre/voz/lip-sync hasta el render)
ai-blender-director auto-director "La Cotorra presenta noticia urgente del régimen" \
  --shots 4 --vertical --hook "ULTIMA HORA" \
  --narration "Buenas noches, soy La Cotorra..." --no-comfy

# Máxima calidad (en GPU): añade --profile final
... --profile final
```

---

## 5. Limitaciones conocidas

- **Render EEVEE necesita GPU/OpenGL.** En esta máquina (headless, sin GPU) Blender **crashea al
  renderizar** (`No OpenGL vendor detected`). El **modelado/export de GLB sí funciona** aquí.
  → Para el video final: usar la GPU de Vast.ai con `provision_gpu.sh`.
- **Instructor con gemini-2.5-flash** devuelve `shots` como strings → por eso es **opt-in**; el
  JSON-mode clásico es el default robusto.
- **Licencias TTS:** para uso comercial, evitar XTTS v2 / F5 (no comerciales); preferir
  OpenVoice v2 (MIT) o Fish Speech.
- **Lip-sync end-to-end** solo en el flujo multi-shot (`--shots>1`), no en single-shot.

---

## 6. Próximos pasos sugeridos

1. **Render real en GPU** (Vast.ai) para ver el reparto en movimiento — el mayor pendiente.
2. Modelar aliados restantes de la cúpula (Gerardo, Marrero, Bruno, Trovador) y/o secundarios (Arleen, Brigada Copy-Paste).
3. **Gags de escena** (Humbrete baja la luz / tapa cámara; Ciberclarias se hunden) como
   comportamiento de postproducción.
4. Presets de voz reales por personaje (grabar/descargar modelos `.onnx` y mapearlos en `.env`).
