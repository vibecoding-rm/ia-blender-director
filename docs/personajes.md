# Biblia de Personajes — *El Noticiero de La Cotorra*

> **Nota de enfoque.** Este documento define **caricaturas satíricas** para una serie de
> sátira política animada. Los antagonistas están inspirados en el **rol público
> documentado** de figuras de la televisión oficialista cubana como voceros/propagandistas
> del régimen. La sátira nace de la **exageración del personaje público** y del contraste
> entre el discurso oficial y la realidad — no de acusaciones privadas ni datos personales.
> Es una larga tradición de la sátira política (marionetas, claymation, caricatura editorial).

---

## 1. Premisa del universo

En la **República Popular de Plastilina**, el régimen produce su propio noticiero oficial:
**"El Noticiero de La Cotorra"**. La presentadora repite el guion del Partido… hasta que
"se le escapa" la verdad. Cada vez que eso pasa, **El Aparato** (los voceros y el enjambre
de trolls) entra a "corregir", censurar y reportar. Todo ocurre en un estudio que literal y
figuradamente **se cae a pedazos**: apagones, fondo verde despegándose, micrófonos de
plastilina que se derriten.

El humor vive en el **contraste**: solemnidad oficial ↔ ruina cotidiana.

---

## 2. Ficha técnica común (para producción 3D)

Cada personaje es un **asset riggeado** en Blender, igual que `cotorra_v1`:

- **Armature** con hueso de **mandíbula** (`Beak` / `Jaw`) → lip-sync por audio (Rhubarb).
- Huesos de **ojos** para parpadeo procedural.
- Acciones NLA: **`Idle`**, **`Talk`**, **`Walk`** (y opcional `React` para gags).
- Estilo **claymation**: materiales con subsurface + huellas (ya en `materials.py`).
- Export **GLB** a `assets/characters/<id>/<id>.glb` + su `asset.json`.
- Alta en `planner.py` (`character_mappings`) para que el Director Agent lo invoque por nombre.
- **Voz** propia vía el backend TTS (`settings.tts_engine`).

---

## 3. Protagonistas

### 🦜 La Cotorra
- **Rol:** presentadora estrella del noticiero. La "voz oficial" que, por instinto de cotorra,
  **repite todo** — incluida la verdad que no debía decir.
- **Diseño:** perica verde caribeña, cabeza grande (ratio "cuteness"), pico articulado,
  cresta roja de tres llamitas, ojos grandes de botón. Traje de presentadora mal entallado.
  Plastilina: cuerpo verde (`#2A8540`), vientre crema (`#D9C773`), pico naranja (`#F29E1F`).
- **Personalidad:** dócil en apariencia, pero la verdad se le escapa como un eructo. Inocente-letal.
- **Catchphrases:** *"…y según fuentes 100% oficiales — digo, según lo que vi con mis ojos…"* ·
  *"¡Esto no lo iba a decir, pero ya que estamos…!"*
- **Gag firma:** abre el pico para leer el teleprónter y le sale la verdad; se tapa el pico con el ala.
- **Voz (TTS):** femenina, tono noticiero impostado que se quiebra en sinceridad. Piper es suficiente;
  ideal una voz clonada consistente.
- **Estado:** ya existe (`cotorra_v1.glb`, con acciones Idle/Talk/Walk y parpadeo).

### 🐷 El Comandante Cerdo
- **Rol:** vocero máximo del régimen. Da las "orientaciones".
- **Diseño:** cerdo bípedo en uniforme verde olivo cargado de medallas de plastilina, gorra militar,
  mandíbula articulada, **dedo acusador** prominente. Plastilina rosada grisácea (`#C98B86`).
- **Personalidad:** pomposo, amenazante, se ofende por todo. Confunde "pueblo" con "enemigo".
- **Catchphrases:** *"¡Eso es una campaña del imperio!"* · *"Compañeros, hay que resistir… ustedes."*
- **Gag firma:** cada vez que algo falla, culpa al "bloqueo"; el dedo acusador se le cae y lo recoge.
- **Voz (TTS):** grave, lenta, con eco de discurso de plaza.
- **Estado:** ya existe (`cerdo`).

---

## 4. El Aparato — antagonistas (nuevos)

### 🐶 Humbertico "El Bulterico"
- **Caricaturiza a:** Humberto López (*Hacemos Cuba* / NTV), apodado **"Humbertico"** por la gente;
  rostro de las campañas contra el MSI y el 27N, conocido por llamar **"mercenarios"** a activistas
  y por intentar quitarle el teléfono a una activista. (Rol público de "ariete" de la propaganda.)
- **Diseño 3D:** **bulldog/dóberman** de plastilina embutido en un traje gris barato que le aprieta.
  Papada temblorosa, ceño permanente, dientes grandes. Lleva una **"Carpeta de la Seguridad"** bajo
  el brazo (de la que saca "pruebas" absurdas). Plastilina marrón-tabaco (`#6B4A2B`), traje gris (`#5A5A60`).
  Silueta reconocible: perro cuadrado con maletín.
- **Personalidad:** matón con micrófono; ladra más de lo que informa. Bravucón ante débiles, cobarde ante datos.
- **Catchphrases:** *"¡MEEERCENARIO!"* (ladrido) · *"Tengo aquí, en esta carpeta…"* · *"¡Dame ese teléfono!"*
- **Gag firma:** en cuanto alguien saca un teléfono, intenta **robárselo** y forcejea con el plano;
  abre la carpeta y vuelan papeles en blanco.
- **Voz (TTS):** masculina, agresiva, ladridos cortados; sube el volumen cuando no tiene argumentos.
- **Relaciones:** brazo ejecutor del Comandante Cerdo; desprecia a La Cotorra por "blanda".

### 🐓 Michelito "Con Filo"
- **Caricaturiza a:** Michel Torres Corona (programa *Con Filo*), presentador-guionista irónico;
  su mentor Iroel Sánchez lo apodó **"Huevonauta"**. (Rol público: difama con ironía a quien opina distinto.)
- **Diseño 3D:** **gallo fino (de pelea) joven**, cresta engominada hacia atrás, plumas brillantes,
  espolones, una **navajita ("filo")** atada a la pata. Camisa moderna ajustada. Plastilina:
  plumaje azul-petróleo (`#2E5A78`), cresta roja (`#C8202A`). Silueta: gallito chulo con cuchillito.
- **Personalidad:** sarcástico, soberbio, se cree el "joven símbolo" del régimen. Lee un guion que le
  sostiene un agente fuera de cuadro.
- **Catchphrases:** *"Hoy, Con Filo… y sin argumentos."* · *"Qué casualidad, ¿no?"* (insinuación marca de la casa) ·
  *"Esto me lo escribí yo solito."*
- **Gag firma:** "afila" un insulto contra el pueblo; cuando le responden con un dato, se esconde
  **dentro de un huevo gigante** (el "Huevonauta") y asoma solo los ojos.
- **Voz (TTS):** masculina joven, nasal, ritmo rápido y burlón.
- **Relaciones:** rivaliza con Humbertico por ser "el favorito"; subestima a Randy por viejo.

### 🐢 Randy "La Mesa Redonda Interminable"
- **Caricaturiza a:** Randy Alonso (*Mesa Redonda* / *Cubadebate*), rostro incansable de la propaganda
  desde los años 90. (Rol público: conductor del espacio insignia de propaganda estatal.)
- **Diseño 3D:** **tortuga vieja** de plastilina con gafas grandes y traje marrón anticuado, sentada
  eternamente a una **mesa redonda que gira sola**. Caparazón con el logo del canal medio despegado.
  Plastilina: caparazón verde-oliva (`#556B2F`), piel gris (`#8A8A7A`). Silueta: tortuga + mesa giratoria.
- **Personalidad:** habla horas sin decir nada; el invitado siempre asiente. Maestro del relleno.
- **Catchphrases:** *"Y para profundizar en este importante tema…"* · *"Llevamos cuatro horas, compañeros, y seguimos."*
- **Gag firma:** su programa **nunca termina** (contador en pantalla: "Mesa Redonda — Día 3"); cuando
  alguien menciona un **apagón**, "se va la señal" y vuelve sin que nadie se mueva.
- **Voz (TTS):** masculina, grave, monótona, somnífera; ritmo lentísimo.
- **Relaciones:** "decano" respetado a regañadientes; usa a los demás como "panelistas".

### 🦡 Lázaro "El Hurón del Mediodía"
- **Caricaturiza a:** Lázaro Manuel Alonso (noticiero del mediodía, NTV), criticado por atacar a la
  oposición; **cerró su Facebook** tras un destape de excolegas. (Rol público: conductor que ataca y borra.)
- **Diseño 3D:** **hurón/mangosta** escurridizo con corbata estrecha y sonrisa nerviosa, ojitos juntos.
  Siempre cerca de una **alcantarilla** por la que desaparece. Plastilina: pelaje crema-marrón (`#B89B72`),
  corbata roja (`#A21F2A`). Silueta: mustélido alargado con corbata.
- **Personalidad:** ataca al mediodía y de noche **borra las pruebas**. Valiente solo en diferido.
- **Catchphrases:** *"Como decíamos al mediodía…"* · *"Eso yo no lo dije"* (mientras lo repite el ticker).
- **Gag firma:** ante una pregunta incómoda, **"cierra su Facebook"** (un cartel de "cuenta desactivada"
  le cubre la cara) y se mete por la alcantarilla.
- **Voz (TTS):** masculina, suave y meliflua, que se acelera nerviosa al ser confrontado.
- **Relaciones:** evita a Humbertico (le tiene miedo), copia a Randy.

### 🐟 Las Ciberclarias *(coro / enjambre recurrente)*
- **Caricaturiza a:** las **"ciberclarias"** — cuentas-troll del régimen que ocultan su identidad,
  repiten consignas, atacan a críticos y **reportan en masa** cuentas de activistas para cerrarlas.
  El nombre viene del *claria*, pez introducido en los 90 que **sobrevive enterrado en el fango y come
  de todo**. (Fenómeno público documentado, incluso por un estudio de Oxford sobre "cibertropas".)
- **Diseño 3D:** **banco de bagres (clarias)** de plastilina cubiertos de fango, bigotes largos, cada
  uno con un **teléfono**, saliendo en masa de alcantarillas y charcos. Idénticos entre sí
  (son un enjambre). Plastilina: gris-fango (`#4A4438`), brillo húmedo. Silueta: pez-bigote + teléfono.
- **Rol:** el **coro**. Inundan la pantalla con el mismo comentario copy-paste, presionan el botón
  **"REPORTAR"**, y se **entierran en el fango** cuando aparece un dato real.
- **Catchphrases (en bloque):** *"¡VIVA!"* · *"¡Mercenario pagado!"* · *"REPORTADO ✅"*.
- **Gag firma:** aparecen como enjambre repitiendo la consigna del día; al primer hecho verificable,
  **se hunden** todos a la vez con un *"glup"*.
- **Voz (TTS):** coro de voces procesadas/pitch variado, solapadas (efecto "bot").
- **Producción:** se puede hacer **un solo modelo** instanciado en partículas/duplicados (barato y
  con gran efecto cómico de masa).

---

## 5. Estructura de episodio (Short 9:16, 30–60 s)

1. **Gancho (1.4 s):** tarjeta "ÚLTIMA HORA" con titular absurdo + sting. *(branding.py — ya existe.)*
2. **Estudio:** La Cotorra presenta la "noticia oficial".
3. **Fuga de verdad:** se le escapa el dato real → reacción.
4. **Entra El Aparato:** Humbertico ladra "mercenario", o las Ciberclarias inundan la pantalla,
   o corte a la Mesa Redonda de Randy.
5. **Colapso cómico:** apagón / fondo verde despegándose / micrófono que se derrite.
6. **Cierre:** remate + ticker satírico ("Noticias 100% oficiales*"). *(lower-third + ticker — ya existen.)*

**Ritmo:** un cambio de plano cada 3–5 s (multi-shot, ya por defecto en `--shots 4`).

---

## 6. Segmentos recurrentes y *running gags*

- **"Con Filo… y sin argumentos"** — el editorial de Michelito.
- **"Mesa Redonda — Día N"** — el programa de Randy que nunca acaba.
- **"El Reporte de las Ciberclarias"** — barrido de comentarios-bot.
- **El apagón** — siempre se va la luz en el peor momento (chiste estructural).
- **La carpeta de Humbertico** — siempre saca "pruebas" que son papeles en blanco.
- **El fondo verde** — el croma se despega y revela el estudio en ruinas.

## 7. Ideas de episodio piloto

1. **"ÚLTIMA HORA: el café ahora es opcional (como la electricidad)"** — La Cotorra anuncia el "logro";
   Humbertico llama mercenario al que pregunta por el café; apagón.
2. **"El régimen decreta el Sombrero de Fiesta obligatorio en días hábiles"** — Michelito defiende el
   decreto Con Filo; las Ciberclarias celebran; el sombrero es de plastilina y se derrite.
3. **"Mesa Redonda especial: ¿Por qué somos tan felices? (Día 4)"** — Randy entrevista a Lázaro, que
   ataca y luego cierra su Facebook en vivo; La Cotorra suelta la cifra real de la felicidad.

---

## 8. Integración con el pipeline (próximos pasos técnicos)

Para cada personaje nuevo, en orden de impacto cómico (**Humbertico** y **Ciberclarias** primero):

1. **Script de export** `scripts/blender/export_<id>.py` (patrón de `export_cotorra.py`): armadura con
   hueso de mandíbula + ojos, mallas de plastilina, acciones `Idle/Talk/Walk`, export GLB.
2. **Registro de asset** `assets/characters/<id>/asset.json`.
3. **Alta en el planner** (`planner.py` → `character_mappings`): palabras clave → `<id>`.
4. **Voz** en el backend TTS (tono por personaje).

Mapa de IDs sugerido:

| Personaje | `asset_id` | Animal | Prioridad |
|---|---|---|---|
| Humbertico "El Bulterico" | `humbertico_v1` | bulldog | 🔴 Alta |
| Las Ciberclarias | `ciberclarias_v1` | enjambre de bagres | 🔴 Alta |
| Michelito "Con Filo" | `michelito_v1` | gallo fino | 🟡 Media |
| Randy (Mesa Redonda) | `randy_v1` | tortuga | 🟡 Media |
| Lázaro "El Hurón" | `lazaro_v1` | hurón | 🟢 Baja |
