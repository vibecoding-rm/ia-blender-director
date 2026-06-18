"""Narración local con backend de TTS intercambiable.

Por defecto usa piper-tts (CPU, sin servicios externos). Se puede cambiar el
motor con `settings.tts_engine`:

- "piper"   → piper (rápido, local, voz fija). Por defecto.
- "xtts"    → CLI de Coqui TTS con XTTS v2 (clonación de voz, español). Requiere
              `pip install TTS` y una muestra de referencia (settings.tts_speaker_wav).
- "command" → plantilla libre en settings.tts_command con placeholders
              {text} {out} {ref} (para OpenVoice/Fish Speech u otro motor propio).

Cualquier fallo de un motor avanzado cae con elegancia a piper, así el pipeline
nunca se queda sin narración por un problema de dependencias.
"""

from __future__ import annotations

import logging
import shlex
import subprocess
from pathlib import Path

from .config import settings

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VOICE = ROOT / "assets" / "voices" / "es_MX-claude-high.onnx"


def synthesize(
    text: str, output_wav: Path, *, voice: Path | None = None, engine: str | None = None
) -> bool:
    """Sintetiza `text` a un WAV. Devuelve True si se generó el archivo.

    `engine` sobreescribe settings.tts_engine para esta llamada.
    """
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    engine = (engine or settings.tts_engine or "piper").lower()

    if engine == "piper":
        return _synthesize_piper(text, output_wav, voice=voice)

    ok = False
    if engine == "xtts":
        ok = _synthesize_xtts(text, output_wav)
    elif engine == "command":
        ok = _synthesize_command(text, output_wav)
    else:
        logger.warning("Motor TTS desconocido '%s'; usando piper.", engine)

    if ok and output_wav.exists():
        return True
    logger.warning("Motor TTS '%s' no produjo audio; fallback a piper.", engine)
    return _synthesize_piper(text, output_wav, voice=voice)


def _synthesize_piper(text: str, output_wav: Path, *, voice: Path | None = None) -> bool:
    voice = voice or DEFAULT_VOICE
    if not voice.exists():
        logger.error("Voz piper no encontrada: %s", voice)
        return False
    result = subprocess.run(
        ["piper", "-m", str(voice), "-f", str(output_wav)],
        input=text.encode("utf-8"),
        capture_output=True,
    )
    if result.returncode != 0:
        logger.error("piper falló: %s", result.stderr.decode(errors="replace")[-300:])
        return False
    return output_wav.exists()


def _synthesize_xtts(text: str, output_wav: Path) -> bool:
    """XTTS v2 vía el CLI de Coqui TTS (clonación de voz multilingüe)."""
    speaker = settings.tts_speaker_wav
    if not speaker or not Path(speaker).exists():
        logger.error("xtts requiere settings.tts_speaker_wav (muestra de referencia).")
        return False
    cmd = [
        "tts",
        "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
        "--text", text,
        "--speaker_wav", str(speaker),
        "--language_idx", settings.tts_language,
        "--out_path", str(output_wav),
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        logger.error("xtts (Coqui TTS) falló: %s", result.stderr.decode(errors="replace")[-300:])
        return False
    return output_wav.exists()


def _synthesize_command(text: str, output_wav: Path) -> bool:
    """Motor genérico: ejecuta settings.tts_command con {text} {out} {ref}."""
    template = settings.tts_command
    if not template:
        logger.error("tts_engine='command' requiere settings.tts_command.")
        return False
    ref = settings.tts_speaker_wav or ""
    cmd = shlex.split(template.format(text=text, out=str(output_wav), ref=ref))
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        logger.error("comando TTS falló: %s", result.stderr.decode(errors="replace")[-300:])
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
