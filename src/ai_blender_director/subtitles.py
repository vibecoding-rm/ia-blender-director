"""Subtítulos quemados para Shorts: grandes, con borde, legibles sin sonido.

Genera un archivo .ass desde el texto de narración repartiendo el tiempo de
forma proporcional al número de caracteres de cada fragmento, y lo quema en el
video con ffmpeg. Sin dependencias de alineación: para clips de 30-45 s con voz
TTS de velocidad constante, el reparto proporcional queda bien sincronizado.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

MAX_WORDS_PER_CAPTION = 5


def chunk_narration(text: str, *, max_words: int = MAX_WORDS_PER_CAPTION) -> list[str]:
    """Divide la narración en fragmentos de pocas palabras, respetando frases.

    Corta primero por puntuación fuerte y luego cada frase en grupos de
    `max_words` palabras como máximo (los Shorts usan 4-7 palabras por caption).
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?:;])\s+", text.strip()) if s.strip()]
    chunks: list[str] = []
    for sentence in sentences:
        words = sentence.split()
        for i in range(0, len(words), max_words):
            chunks.append(" ".join(words[i:i + max_words]))
    return chunks


def caption_timings(
    chunks: list[str],
    *,
    audio_duration: float,
    start_offset: float = 0.0,
) -> list[tuple[float, float, str]]:
    """Asigna (inicio, fin, texto) proporcional a la longitud de cada fragmento."""
    total_chars = sum(len(c) for c in chunks) or 1
    timings: list[tuple[float, float, str]] = []
    cursor = start_offset
    for chunk in chunks:
        span = audio_duration * len(chunk) / total_chars
        timings.append((cursor, cursor + span, chunk))
        cursor += span
    return timings


def write_ass(
    timings: list[tuple[float, float, str]],
    output_path: Path,
    *,
    play_res: tuple[int, int] = (720, 1280),
) -> Path:
    """Escribe un .ass con estilo Shorts: tipografía gruesa, borde negro, parte baja."""
    width, height = play_res
    font_size = max(28, int(height * 0.045))
    margin_v = int(height * 0.18)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Shorts,DejaVu Sans,{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H7F000000,-1,0,0,0,100,100,0,0,1,4,1,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for start, end, text in timings:
        safe = text.replace("{", "(").replace("}", ")").upper()
        lines.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Shorts,,0,0,0,,{safe}\n")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(lines), encoding="utf-8")
    return output_path


def burn_subtitles(video: Path, ass_path: Path, output: Path) -> bool:
    """Quema el .ass en el video (re-encode H264)."""
    # libass interpreta ':' y '\' en el path del filtro — escapar mínimamente.
    filter_path = str(ass_path).replace("\\", "\\\\").replace(":", "\\:")
    result = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
         "-vf", f"ass={filter_path}", "-c:a", "copy", str(output)],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"error: ffmpeg subtitles falló: {result.stderr.decode(errors='replace')[-300:]}", file=sys.stderr)
        return False
    return output.exists()


def _ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"
