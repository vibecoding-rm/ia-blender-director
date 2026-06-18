"""Lip-sync por audio con Rhubarb Lip Sync (local, sin servicios externos).

Rhubarb (https://github.com/DanielSWolf/rhubarb-lip-sync, MIT) analiza un WAV de
narración y devuelve una línea de tiempo de visemas (formas de boca). Para La
Cotorra —cuya "boca" es el pico articulado (hueso `Beak`)— traducimos cada
visema a una cantidad de apertura del pico (0..1) que el script de Blender aplica
como keyframes sobre la rotación del hueso.

Degradación elegante: si el binario `rhubarb` no está instalado, `generate_visemes`
devuelve None y el pipeline sigue usando la animación Talk embebida.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Visemas de Rhubarb (esquema Preston-Blair extendido) → apertura de boca 0..1.
# X = reposo/silencio (cerrado); A = cerrado labial (M/B/P); D = vocal abierta.
VISEME_OPENNESS: dict[str, float] = {
    "X": 0.0,   # silencio / reposo
    "A": 0.05,  # M, B, P — labios cerrados
    "B": 0.22,  # consonantes suaves, E breve
    "C": 0.45,  # E, vocales medias
    "D": 0.85,  # A, vocales abiertas
    "E": 0.50,  # O
    "F": 0.30,  # U, W, F
    "G": 0.28,  # F, V (dientes-labio)
    "H": 0.62,  # L
}


def rhubarb_available() -> bool:
    """True si el binario `rhubarb` está en el PATH."""
    return shutil.which("rhubarb") is not None


def generate_visemes(wav: Path, out_json: Path, *, recognizer: str = "phonetic") -> Path | None:
    """Ejecuta Rhubarb sobre `wav` y escribe la timeline de visemas en `out_json`.

    Devuelve la ruta del JSON si tuvo éxito, o None si falta el binario o falla.
    `recognizer="phonetic"` no depende del idioma (mejor para español).
    """
    if not rhubarb_available():
        logger.info("rhubarb no está instalado; se omite el lip-sync por audio.")
        return None
    if not wav.exists():
        logger.error("WAV de narración no encontrado para lip-sync: %s", wav)
        return None
    out_json.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["rhubarb", "-f", "json", "-r", recognizer, "-o", str(out_json), str(wav)],
        capture_output=True,
    )
    if result.returncode != 0:
        logger.error("rhubarb falló: %s", result.stderr.decode(errors="replace")[-300:])
        return None
    return out_json if out_json.exists() else None


def parse_visemes(json_path: Path) -> list[dict]:
    """Lee el JSON de Rhubarb y devuelve la lista de mouthCues [{start,end,value}]."""
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("mouthCues", [])


def cues_to_jaw_track(
    cues: list[dict], fps: int, *, max_open_rad: float, start_offset: float = 0.0
) -> list[tuple[int, float]]:
    """Convierte mouthCues a keyframes (frame, rotación_apertura_rad) para el pico.

    - `fps`: frames por segundo del shot.
    - `max_open_rad`: apertura máxima del pico en radianes (openness 1.0).
    - `start_offset`: segundos de la narración que ocurren antes de este shot
      (para mapear un WAV global a la línea de tiempo local del plano).
    """
    track: list[tuple[int, float]] = []
    for cue in cues:
        try:
            start = float(cue["start"]) - start_offset
            value = str(cue["value"]).upper()
        except (KeyError, ValueError, TypeError):
            continue
        if start < 0:
            continue
        openness = VISEME_OPENNESS.get(value, 0.0)
        frame = max(1, round(start * fps) + 1)
        track.append((frame, openness * max_open_rad))
    return track
