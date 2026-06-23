# Biblia de Personajes — *El Noticiero de La Cotorra*

> **Nota de enfoque.** Este documento define **caricaturas satíricas** para una serie de
> sátira política animada. Los antagonistas están inspirados en el **rol público
> documentado** de figuras de la televisión y el aparato comunicacional oficialista cubano
> (conductores, programas, canales y operaciones digitales señalados por medios
> independientes y organizaciones de DD.HH.). La sátira nace de la **exageración del
> personaje público** y del contraste entre el discurso oficial y la realidad — no de
> acusaciones privadas ni datos personales. Es la tradición de la caricatura editorial y el
> *claymation* satírico (marionetas, *Spitting Image*, etc.).

---

## 1. Premisa del universo

En la **República Popular de Plastilina**, una **cotorra** presenta el noticiero oficial.
Al inicio repite la propaganda obedientemente, pero **como es cotorra, repite también lo que
el régimen no quiere que se diga**. Cada episodio es una noticia absurda donde **"El Aparato"**
—la maquinaria de TV, podcasts, canales anónimos y tropas digitales— intenta corregirla,
censurarla o hundirla en ruido digital. El estudio, literal y figuradamente, **se cae a pedazos**.

El humor vive en el **contraste**: solemnidad oficial ↔ ruina cotidiana.

---

## 2. Ficha técnica común (para producción 3D)

Cada personaje es un **asset riggeado** en Blender, igual que `cotorra_v1`:

- **Armature** con hueso de **mandíbula** (`Beak` / `Jaw`) → lip-sync por audio (Rhubarb).
- Huesos de **ojos** para parpadeo procedural.
- Acciones NLA: **`Idle`**, **`Talk`**, **`Walk`** (+ opcional `React` para gags).
- Estilo **claymation**: materiales con subsurface + huellas (`materials.py`).
- Export **GLB** a `assets/characters/<id>/<id>.glb` + su `asset.json`.
- Alta en `planner.py` (`character_mappings`) para que el Director Agent lo invoque por nombre.
- **Voz** propia vía el backend TTS (`settings.tts_engine`).

---

## 3. Protagonistas

### 🦜 La Cotorra — *heroína involuntaria*
- **Rol:** presentadora del noticiero. La "voz oficial" que, por instinto de cotorra, **repite
  todo** — incluida la verdad que no debía decir.
- **Diseño:** perica verde caribeña, cabeza grande, pico articulado, cresta roja de tres llamitas,
  ojos grandes de botón, traje de presentadora mal entallado. Plastilina: cuerpo verde (`#2A8540`),
  vientre crema (`#D9C773`), pico naranja (`#F29E1F`).
- **Personalidad:** dócil en apariencia; la verdad se le escapa como un eructo. Inocente-letal.
- **Catchphrases:** *"…según fuentes 100% oficiales — digo, según lo que vi con mis ojos…"* ·
  *"¡Esto no lo iba a decir, pero ya que estamos…!"*
- **Voz (TTS):** femenina, noticiero impostado que se quiebra en sinceridad.
- **Estado:** ya existe (`cotorra_v1.glb`, con Idle/Talk/Walk + parpadeo).

### 🐷 El Comandante Cerdo — *jefe del Aparato*
- **Rol:** vocero máximo del régimen; da las "orientaciones".
- **Diseño:** cerdo bípedo en uniforme verde olivo con medallas, gorra militar, mandíbula
  articulada, **dedo acusador**. Plastilina rosada grisácea (`#C98B86`).
- **Catchphrases:** *"¡Eso es una campaña del imperio!"* · *"Compañeros, hay que resistir… ustedes."*
- **Voz (TTS):** grave, lenta, con eco de plaza.
- **Estado:** ya existe (`cerdo`).

---

## 4. El Aparato — Núcleo Principal (TV)

### 🐶 Humbrete, el Sabueso de Expediente
- **Caricaturiza a:** Humberto López ("Humbrete"/"Humbertico"), conductor de *Hacemos Cuba*
  (Canal Caribe / TV Cubana). Figura pública señalada por medios independientes y la FDHC como
  rostro de campañas de descrédito contra activistas, artistas y periodistas independientes.
- **Diseño 3D:** **bulldog/sabueso** de plastilina con traje gris apretado, papada temblorosa,
  ceño permanente, dientes grandes. Lleva **carpeta secreta**, micrófono y un sello de **"MERCENARIO"**.
  Plastilina marrón-tabaco (`#6B4A2B`), traje gris (`#5A5A60`). Silueta: perro cuadrado con maletín.
- **Personalidad:** fiscal televisivo; entra gritando "pruebas" que son recortes absurdos,
  *screenshots* borrosos y sellos. Bravucón ante débiles, cobarde ante datos.
- **Catchphrases:** *"¡Tengo las PRUEBAS aquí!"* · *"¡MEEERCENARIO!"* (ladrido) · *"¡Apaguen esa cámara!"*
- **Gag firma:** al aparecer, **baja la luz del estudio** y arranca el "segmento de difamación".
  Si alguien enseña un dato real, intenta **tapar la cámara con la carpeta**.
- **Voz (TTS):** masculina, agresiva, ladridos cortados; sube el volumen cuando no tiene argumentos.
- **Relaciones:** brazo ejecutor del Comandante Cerdo; desprecia a La Cotorra por "blanda".

### 🐓 Michelito Filo, el Gallito Navaja
- **Caricaturiza a:** Michel Torres Corona, conductor/guionista de *Con Filo* (presentado por
  Cubadebate como militante y rostro del programa). La cara "joven" del agitprop pos-11J; asociado
  a Iroel Sánchez y Randy Alonso en la cocina editorial.
- **Diseño 3D:** **gallo fino joven**, cresta brillante engominada, espejuelos, espolones y una
  **navajita de cartón**. Camisa moderna ajustada. Plastilina: plumaje azul-petróleo (`#2E5A78`),
  cresta roja (`#C8202A`). Silueta: gallito *cool* con cuchillito.
- **Personalidad:** quiere parecer moderno e irónico, pero siempre lee el guion que le pasan
  fuera de cuadro.
- **Catchphrases:** *"Esto no es propaganda, es contexto."* · *"Hoy, Con Filo… y sin argumentos."* ·
  *"Qué casualidad, ¿no?"*
- **Gag firma:** cada vez que alguien le responde con un hecho, **pierde el filo y la navaja queda
  como cuchara**.
- **Voz (TTS):** masculina joven, nasal, rápida y burlona.
- **Relaciones:** rivaliza con Humbrete por el favor del régimen; "dúo" editorial con Gaby Filo.

### 🦉 Gaby Filo, la Lechuza de Teleprompter
- **Caricaturiza a:** Gabriela Fernández Álvarez, presentadora y guionista de *Con Filo*; en 2025
  medios independientes reportaron su gira propagandística por España y declaraciones negando la
  existencia de presos políticos.
- **Diseño 3D:** **lechuza** muy seria, ojos enormes, pestañas duras, toga/blazer académico.
  Plastilina: plumaje gris-beige (`#9A8C73`), ojos ámbar (`#E0A526`). Silueta: búho con teleprompter.
- **Personalidad:** no grita: **"explica"** la propaganda con tono de clase universitaria, como si
  fuera pedagogía.
- **Catchphrases:** *"Hagamos un análisis sereno…"* · *"No hay presos, hay… matices."*
- **Gag firma:** su **teleprompter gigante la aplasta**; cuando se rompe solo puede repetir
  *"matriz de opinión, matriz de opinión"*.
- **Voz (TTS):** femenina, calmada, condescendiente, ritmo de conferencia.
- **Relaciones:** "intelectual de la casa"; corrige a Michelito con suficiencia.

### 🐢 Randy Redondo, la Tortuga de Mesa
- **Caricaturiza a:** Randy Alonso Falcón, director general de *Mesa Redonda* y *Cubadebate*; una de
  las figuras más longevas del aparato comunicacional oficial.
- **Diseño 3D:** **tortuga vieja** con gafas y traje marrón, atrapada en una **mesa circular que gira
  sin llegar a ningún lugar**. Caparazón con el logo del canal medio despegado. Plastilina:
  caparazón verde-oliva (`#556B2F`), piel gris (`#8A8A7A`). Silueta: tortuga + mesa giratoria.
- **Personalidad:** habla tan largo que **envejecen los invitados**. Maestro del relleno.
- **Catchphrases:** *"Para profundizar en este importante tema…"* · *"Vamos a hacer una pausa."*
- **Gag firma:** cada vez que dice "vamos a hacer una pausa", **ocurre un apagón**; contador en
  pantalla: *"Mesa Redonda — Día N"*.
- **Voz (TTS):** masculina, grave, monótona, somnífera.
- **Relaciones:** "decano" del Aparato; usa a todos como "panelistas".

### 🐀 Arleen Chapea, la Jutía Podadora
- **Caricaturiza a:** Arleen Rodríguez Derivet, coordinadora general de *Mesa Redonda*, autora en
  Cubadebate y conductora de *Chapeando Bajito* (podcast en Cubadebate / Radio Rebelde); descrita
  por medios críticos como operadora discursiva cercana al núcleo presidencial.
- **Diseño 3D:** **jutía** (roedor cubano) con **tijeras de jardín** y auriculares de podcast.
  Plastilina: pelaje marrón rojizo (`#7A4A2E`), auriculares negros. Silueta: jutía + tijeras.
- **Personalidad:** **"chapea" la realidad**: corta lo incómodo, deja solo lo conveniente.
- **Catchphrases:** *"Eso es fake news."* · *"Chapeando bajito, compañeros."*
- **Gag firma:** convierte **todo** en "fake news", incluso lo que la cámara muestra en vivo.
- **Voz (TTS):** femenina, podcast íntimo, falsa cercanía.
- **Relaciones:** dúo de "vieja maquinaria" con Randy Redondo.

---

## 5. El Aparato Digital

### 🥫 El Guerrero de Lata
- **Caricaturiza a:** "El Guerrero Cubano", canal anónimo/seudónimo citado por medios oficiales y
  criticado por independientes como herramienta de ataques y amenazas; Telemundo y Diario Las
  Américas reportaron denuncias/investigaciones sobre amenazas vinculadas al canal.
- **Diseño 3D:** **casco/armadura vacía** con voz distorsionada; nadie ve quién está dentro. Espada
  de **antena WiFi** y escudo de **"FUENTE ANÓNIMA"**. Plastilina: lata gris metálico (`#7F8389`).
  Silueta: caballero hueco.
- **Personalidad:** amenaza en voz grave, valentón anónimo.
- **Catchphrases:** *"Te tenemos identificado."* · *"Fuentes confiables confirman…"*
- **Gag firma:** cuando se le **cae el casco no hay cabeza**: solo cables y un teléfono con "saldo
  institucional".
- **Voz (TTS):** masculina muy procesada (modulador/robotizada), grave y reverberada.
- **Relaciones:** "operación sucia" junto a las Ciberclarias y la Brigada Copy-Paste.

### 🐟 Las Ciberclarias *(coro / enjambre)*
- **Caricaturiza a:** las **"ciberclarias"** — término popular para trolls oficialistas y cuentas
  coordinadas que atacan a críticos (documentadas por CiberCuba, Yucabyte y otros, incluidas
  operaciones tipo *De Zurda Team*). El *claria* es un pez de fango que **sobrevive enterrado y come
  de todo**.
- **Diseño 3D:** **banco de bagres** de fango con celulares, **ojos rojos** y camisetas iguales.
  Idénticos entre sí. Plastilina gris-fango (`#4A4438`), brillo húmedo. *(Un solo modelo instanciado
  en partículas/duplicados.)*
- **Gag firma:** aparecen de golpe repitiendo el mismo comentario — *"Viva"*, *"mercenario"*,
  *"bloqueo"*, *"fake"* — y cuando La Cotorra dice una verdad simple, **se traban como bots** y se hunden.
- **Voz (TTS):** coro de voces con *pitch* variado, solapadas (efecto bot).

### ⌨️ La Brigada Copy-Paste *(minions digitales)*
- **Caricaturiza a:** perfiles/colectivos tipo *De Zurda Team*, "Karlito Marx Jeune", "La Mala
  Palabra", "Cuba No Es Miami" — **no individualizados**, sino como tropa.
- **Diseño 3D:** muñequitos idénticos con teclados, saliendo en cadena de una **"fábrica de
  comentarios"**. Plastilina uniforme roja (`#A21F2A`). Silueta: clones con teclado.
- **Gag firma:** **reportan hasta el pronóstico del tiempo** por "contrarrevolucionario".
- **Voz (TTS):** coro mecánico, copy-paste.

---

## 6. Personajes secundarios

### 🦡 Lázaro Mediodía, el Hurón de Última Hora
- **Caricaturiza a:** Lázaro Manuel Alonso, periodista del NTV; junto a Humberto López fue premiado
  por la UPEC y señalado por medios independientes como parte de campañas de descrédito.
- **Diseño 3D:** **hurón** escurridizo con corbata estrecha y sonrisa nerviosa, junto a una
  **alcantarilla**. Plastilina crema-marrón (`#B89B72`), corbata roja (`#A21F2A`).
- **Gag firma:** aparece rápido, **suelta una acusación y se esconde** (cartel "cuenta desactivada"
  + alcantarilla).
- **Voz (TTS):** masculina, meliflua, que se acelera nerviosa al ser confrontado.

### 👻 El Fantasma de la Pupila *(no antagonista activo)*
- **Inspirado en:** Iroel Sánchez (figura ya fallecida, vinculada a *La Pupila Insomne* y al
  ecosistema que alimentó *Con Filo*). Se usa como **fantasma ideológico**, no como villano activo,
  por respeto y por función narrativa.
- **Diseño 3D:** **retrato en la pared** del estudio que cobra vida y **dicta frases viejas** a los
  presentadores. Plastilina sepia, marco dorado.
- **Gag firma:** sopla consignas anticuadas; Michelito y Gaby las repiten sin entenderlas.
- **Voz (TTS):** masculina, eco/ultratumba, citas de manual.

---

## 7. Estructura de episodio (Short 9:16, 30–60 s)

1. **Titular oficial absurdo** (gancho 1.4 s + sting). *(branding.py — ya existe.)*
2. **La Cotorra lo lee obediente.**
3. **Se cuela una verdad.**
4. **Entra un antagonista:** Humbrete, Michelito Filo, Gaby Filo, Randy Redondo, Arleen Chapea o las
   Ciberclarias.
5. **La escenografía se cae** y revela la realidad (apagón, fondo verde despegándose).
6. **Remate corto** con **ticker satírico**. *(lower-third + ticker — ya existen.)*

**Ritmo:** un cambio de plano cada 3–5 s (multi-shot, ya por defecto en `--shots 4`).

---

## 8. El reparto, por función

| Función | Personaje(s) |
|---|---|
| Heroína involuntaria | **La Cotorra** |
| Jefe del Aparato | **Comandante Cerdo** |
| Fiscal televisivo | **Humbrete** |
| Juventud propagandística | **Michelito Filo** + **Gaby Filo** |
| Vieja maquinaria | **Randy Redondo** + **Arleen Chapea** |
| Operación sucia digital | **Guerrero de Lata** + **Ciberclarias** + **Brigada Copy-Paste** |
| Secundarios | **Lázaro Mediodía**, **El Fantasma de la Pupila** |

---

## 9. Prioridad de modelado e integración

Orden recomendado (impacto cómico + reutilización):

| # | Personaje | `asset_id` | Animal/forma | Por qué primero |
|---|---|---|---|---|
| 1 | **Humbrete** | `humbrete_v1` | bulldog | El más reconocible; gags físicos fuertes |
| 2 | **Ciberclarias** | `ciberclarias_v1` | enjambre de bagres | Sirven para cualquier episodio |
| 3 | **Michelito Filo** | `michelito_v1` | gallo fino | Conecta directo con *Con Filo* |
| 4 | **Randy Redondo** | `randy_v1` | tortuga | Capítulos de apagones/bloqueo/economía |
| 5 | **Guerrero de Lata** | `guerrero_v1` | armadura hueca | Gran personaje de redes/amenazas |
| 6 | **Gaby Filo** | `gaby_v1` | lechuza | Dúo con Michelito |
| 7 | **Arleen Chapea** | `arleen_v1` | jutía | Dúo con Randy |
| 8 | **Brigada Copy-Paste** | `brigada_v1` | clones con teclado | Minions (instanciados) |
| 9 | **Lázaro Mediodía** | `lazaro_v1` | hurón | Secundario rápido |
| 10 | **Fantasma de la Pupila** | `pupila_v1` | retrato | Recurso de fondo |

**Pasos por personaje:**
1. `scripts/blender/export_<id>.py` (patrón de `export_cotorra.py`): armadura con mandíbula + ojos,
   mallas de plastilina, acciones `Idle/Talk/Walk`, export GLB.
2. `assets/characters/<id>/asset.json`.
3. Alta en `planner.py` → `character_mappings` (palabras clave → `<id>`).
4. Voz por personaje en el backend TTS.

---

## 10. La Cúpula del poder y aliados (banco de reserva)

> Estado de modelado: todos los personajes de esta sección ya tienen GLB riggeado.

> Reparto **investigado y definido por si se necesita**. Mismas reglas: caricaturas
> satíricas de figuras públicas por su rol político/público documentado.

### 🐊 El Caimán General — *el poder real tras el trono*
- **Caricaturiza a:** Raúl Castro, General de Ejército que conserva enorme influencia pese a su edad;
  avaló el paquete de "reforma" y sigue como figura tutelar del régimen. (Cuba misma tiene forma de
  caimán: "el caimán" es la isla.)
- **Diseño:** cocodrilo viejísimo de plastilina en uniforme verde olivo, gafas oscuras, mueve los
  **hilos** de una marioneta. Plastilina verde-musgo (`#3B4A2A`).
- **Personalidad:** habla poco, decide todo; sonrisa de reptil.
- **Catchphrase:** *"Tranquilo, muchacho, yo te puse ahí."*
- **Gag firma:** desde la sombra **maneja los hilos** del Guanajo Designado; cuando algo sale mal,
  "ya está retirado".
- **Voz (TTS):** masculina, anciana, rasposa, lentísima.

### 🦃 El Guanajo Designado — *el presidente puppet*
- **Caricaturiza a:** Miguel Díaz-Canel, Primer Secretario del PCC y presidente "designado" por Raúl.
  El pueblo lo corea **"Singao"** desde el 11J (de un rap de Aldo el Aldeano y Silvito el Libre;
  hasta la RAE comentó la grafía). *(En cubano, "guanajo" = pavo, sinónimo de bobo/torpe.)*
- **Diseño:** **guanajo (pavo)** desgarbado en traje grande que le queda mal, con **hilos de marioneta**
  saliéndole de la espalda hacia el Caimán. Moco rojo caído. Plastilina parda (`#6E5A3A`).
- **Personalidad:** torpe, repite consignas, se enreda; valentón solo en discurso.
- **Catchphrases:** *"¡Ordeno y mando… lo que me ordenen!"* · *"Eso lo resolvemos con una tarea."*
- **Gag firma:** cada vez que aparece, **una multitud fuera de cuadro corea "¡Siiingao!"** y él finge
  que aplauden; tropieza con los propios hilos.
- **Voz (TTS):** masculina, monótona, lee de tarjetas, se traba.

### 🐐 Gerardo el Chivatón — *jefe de los CDR*
- **Caricaturiza a:** Gerardo Hernández Nordelo, uno de los "Cinco Héroes", hoy **Coordinador Nacional
  de los CDR** (los comités de vigilancia de barrio). *(Pun: "chivo" → "chivato" = soplón.)*
- **Diseño:** **chivo (cabra)** con binoculares, medalla de "Héroe", libreta de anotaciones y un
  ojo pegado a una **persiana**. Boina. Plastilina blanco-sucio (`#C8C2B0`).
- **Personalidad:** vigila al vecino, anota todo, delata por deporte.
- **Catchphrases:** *"Compañero, lo estoy anotando."* · *"¿Y esa visita de quién es?"*
- **Gag firma:** espía por la persiana y **reporta hasta quién cocina con gas**; toca a las puertas
  "para el CDR".
- **Voz (TTS):** masculina, chismosa, susurrante.

### 🦚 Marrero, el Conserje de Cinco Estrellas — *Primer Ministro*
- **Caricaturiza a:** Manuel Marrero Cruz, Primer Ministro surgido del sector turismo/hoteles.
- **Diseño:** **pavo real** en uniforme de conserje de hotel de lujo, llaves doradas, mientras detrás
  hay apagón. Plastilina azul-pavo (`#1F6F8B`).
- **Personalidad:** inaugura hoteles vacíos mientras el país está a oscuras.
- **Catchphrase:** *"¡Bienvenidos a un nuevo hotel cinco estrellas!"* (se va la luz).
- **Gag firma:** despliega la cola de pavo real = folletos de hoteles; nadie tiene para entrar.
- **Voz (TTS):** masculina, servil, de recepcionista.

### 🐍 Bruno Bloqueo, el Majá Canciller — *Relaciones Exteriores*
- **Caricaturiza a:** Bruno Rodríguez Parrilla, Ministro de Relaciones Exteriores; voz del "bloqueo"
  en foros internacionales.
- **Diseño:** **majá** (serpiente cubana) en traje diplomático, enrollado en un micrófono de la ONU.
  Plastilina verde-gris (`#5A6B4A`).
- **Personalidad:** todo lo explica con una sola palabra: *"bloqueo"*.
- **Catchphrase:** *"Esto es culpa del bloqueo."* (lo dice ante cualquier pregunta).
- **Gag firma:** saca un cartel de "BLOQUEO" para tapar cualquier dato incómodo.
- **Voz (TTS):** masculina, suave, diplomática, siseante.

### 🎸 El Trovador del Picadillo de Soya — *artistas oficialistas*
- **Caricaturiza a:** Raúl Torres y el coro de la canción oficialista *"Patria o Muerte por la Vida"*
  (Annie Garcés, Dayana Divo, etc.), respuesta del régimen a *Patria y Vida*.
- **Diseño:** **sinsonte/canario** en guayabera con guitarra, cantándole a **retratos de líderes
  muertos**; detrás, un coro de pajaritos idénticos. Plastilina pardo-amarillo (`#C2A23A`).
- **Personalidad:** compone odas por encargo; cambia la letra según la orientación del día.
- **Catchphrases:** *"¡Patria o muerte… por la vida… del régimen!"* · *"Esta se la dedico al Comandante."*
- **Gag firma:** su canción acumula *dislikes* en pantalla en tiempo real; el coro desafina.
- **Voz (TTS):** masculina, trovador meloso; coro de relleno.

| Personaje | `asset_id` sugerido | Animal/forma | Uso |
|---|---|---|---|
| El Caimán General | `caiman_v1` | cocodrilo militar | Titiritero del poder |
| El Guanajo Designado | `guanajo_v1` | pavo marioneta | "Presidente" puppet |
| **Gerardo el Chivatón** | `chivaton_v1` | chivo vigilante | Jefe de los CDR |
| **Marrero (Conserje 5★)** | `marrero_v1` | pavo real | Hoteles vs. apagones |
| **Bruno Bloqueo** | `bruno_v1` | majá diplomático | Todo es "el bloqueo" |
| **Trovador del Picadillo** | `trovador_v1` | sinsonte + coro | Artistas oficialistas |
