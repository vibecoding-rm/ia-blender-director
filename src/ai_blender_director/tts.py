"""Narración local con piper-tts (CPU, sin servicios externos)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VOICE = ROOT / "assets" / "voices" / "es_MX-claude-high.onnx"


def synthesize(text: str, output_wav: Path, *, voice: Path | None = None) -> bool:
    """Sintetiza `text` a un WAV usando piper. Devuelve True si se generó el archivo."""
    voice = voice or DEFAULT_VOICE
    if not voice.exists():
        print(f"error: voz piper no encontrada: {voice}", file=sys.stderr)
        return False
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, "-m", "piper", "-m", str(voice), "-f", str(output_wav)],
        input=text.encode("utf-8"),
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"error: piper falló: {result.stderr.decode(errors='replace')[-300:]}", file=sys.stderr)
        return False
    return output_wav.exists()


def mux_narration(video: Path, narration_wav: Path, output: Path) -> bool:
    """Mezcla la narración sobre el video. Si el audio es más largo, congela el
    último frame del video hasta que termine la voz."""
    video_dur = _duration(video)
    audio_dur = _duration(narration_wav)
    if video_dur is None or audio_dur is None:
        return False

    command = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(narration_wav)]
    if audio_dur > video_dur + 0.05:
        pad = audio_dur - video_dur
        command += ["-vf", f"tpad=stop_mode=clone:stop_duration={pad:.3f}"]
    else:
        command += ["-c:v", "copy"]
    command += ["-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", "-shortest", str(output)]

    result = subprocess.run(command, capture_output=True)
    if result.returncode != 0:
        print(f"error: ffmpeg mux falló: {result.stderr.decode(errors='replace')[-300:]}", file=sys.stderr)
        return False
    return output.exists()


def _duration(path: Path) -> float | None:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
    )
    try:
        return float(result.stdout.decode().strip())
    except ValueError:
        print(f"error: no se pudo medir la duración de {path}", file=sys.stderr)
        return None
