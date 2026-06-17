"""Narración local con piper-tts (CPU, sin servicios externos)."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VOICE = ROOT / "assets" / "voices" / "es_MX-claude-high.onnx"


def synthesize(text: str, output_wav: Path, *, voice: Path | None = None) -> bool:
    """Sintetiza `text` a un WAV usando piper. Devuelve True si se generó el archivo."""
    voice = voice or DEFAULT_VOICE
    if not voice.exists():
        logger.error("Voz piper no encontrada: %s", voice)
        return False
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["piper", "-m", str(voice), "-f", str(output_wav)],
        input=text.encode("utf-8"),
        capture_output=True,
    )
    if result.returncode != 0:
        logger.error("piper falló: %s", result.stderr.decode(errors='replace')[-300:])
        return False
    return output_wav.exists()

def media_duration(path: Path) -> float | None:
    """Duración en segundos de un archivo de audio/video (ffprobe)."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True,
    )
    try:
        return float(result.stdout.decode().strip())
    except ValueError:
        logger.error("No se pudo medir la duración de %s", path)
        return None
