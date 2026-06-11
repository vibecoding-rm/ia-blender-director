"""Post-producción de Shorts: gancho + concat + audio (voz/SFX) + subtítulos.

Convierte los clips renderizados por Blender en un Short listo para publicar
siguiendo las reglas de retención documentadas en docs/estrategia_contenido.md:
tarjeta de gancho con sting, whoosh en cada corte, narración TTS y subtítulos
quemados que funcionan sin sonido.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .branding import make_hook_clip
from .sfx import mix_audio_track
from .subtitles import burn_subtitles, caption_timings, chunk_narration, write_ass
from .tts import media_duration, synthesize

HOOK_DURATION = 1.4


def produce_short(
    shot_videos: list[Path],
    shot_durations: list[float],
    output_video: Path,
    *,
    resolution: tuple[int, int],
    fps: int,
    hook_title: str | None = None,
    narration_text: str | None = None,
    voice: Path | None = None,
    subtitles: bool = True,
    sfx: bool = True,
) -> Path | None:
    """Ensambla el Short final. Devuelve la ruta del video terminado o None."""
    output_video.parent.mkdir(parents=True, exist_ok=True)
    work = output_video.parent
    stem = output_video.stem

    # ── 1. Gancho ────────────────────────────────────────────────────────────
    clips = list(shot_videos)
    hook_duration = 0.0
    if hook_title:
        hook_clip = work / f"{stem}_hook.mp4"
        if make_hook_clip(hook_title, hook_clip, resolution=resolution, fps=fps, duration=HOOK_DURATION):
            clips.insert(0, hook_clip)
            hook_duration = HOOK_DURATION
            print(f"  gancho: {hook_clip.name}")
        else:
            print("warning: no se pudo crear la tarjeta de gancho", file=sys.stderr)

    # ── 2. Concat de video (re-encode: el gancho y Blender traen params H264
    # distintos y el concat con -c copy puede corromper la salida) ───────────
    base = work / f"{stem}_base.mp4"
    if not _concat_reencode(clips, base, fps=fps):
        print("error: falló la concatenación de planos", file=sys.stderr)
        return None

    # Momentos de corte (para los whoosh): gancho→plano1 y entre planos
    cut_times: list[float] = []
    cursor = hook_duration
    if hook_duration:
        cut_times.append(round(cursor, 3))
    for duration in shot_durations[:-1]:
        cursor += duration
        cut_times.append(round(cursor, 3))

    # ── 3. Narración ─────────────────────────────────────────────────────────
    narration_wav: Path | None = None
    narration_duration = 0.0
    if narration_text:
        narration_wav = work / f"{stem}_narracion.wav"
        if synthesize(narration_text, narration_wav, voice=voice):
            narration_duration = media_duration(narration_wav) or 0.0
        else:
            narration_wav = None
            print("warning: falló la síntesis de voz", file=sys.stderr)

    # Si la voz se extiende más allá del video, congelar el último frame
    video_duration = media_duration(base) or (hook_duration + sum(shot_durations))
    narration_end = hook_duration + narration_duration
    if narration_wav and narration_end > video_duration + 0.05:
        padded = work / f"{stem}_padded.mp4"
        pad = narration_end - video_duration + 0.3
        result = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(base),
             "-vf", f"tpad=stop_mode=clone:stop_duration={pad:.3f}",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(padded)],
            capture_output=True,
        )
        if result.returncode == 0:
            base = padded
        else:
            print("warning: no se pudo extender el último frame", file=sys.stderr)

    # ── 4. Mezcla de audio (voz + sting + whooshes) ──────────────────────────
    current = base
    if sfx or narration_wav:
        mixed = work / f"{stem}_audio.mp4"
        ok = mix_audio_track(
            current, mixed,
            narration_wav=narration_wav,
            narration_delay=hook_duration,
            cut_times=cut_times if sfx else [],
            with_sting=sfx and hook_duration > 0,
        )
        if ok:
            current = mixed
        else:
            print("warning: el video queda sin pista de audio", file=sys.stderr)

    # ── 5. Subtítulos quemados ───────────────────────────────────────────────
    if subtitles and narration_text and narration_duration > 0:
        chunks = chunk_narration(narration_text)
        timings = caption_timings(chunks, audio_duration=narration_duration, start_offset=hook_duration)
        ass_path = work / f"{stem}_subs.ass"
        write_ass(timings, ass_path, play_res=resolution)
        subtitled = work / f"{stem}_final.mp4"
        if burn_subtitles(current, ass_path, subtitled):
            current = subtitled
        else:
            print("warning: no se pudieron quemar los subtítulos", file=sys.stderr)

    # ── 6. Renombrar al destino final ────────────────────────────────────────
    if current != output_video:
        current.replace(output_video)
    return output_video


def _concat_reencode(clips: list[Path], output: Path, *, fps: int) -> bool:
    list_file = output.with_suffix(".txt")
    list_file.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
    result = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(list_file), "-r", str(fps),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(output)],
        capture_output=True,
    )
    list_file.unlink(missing_ok=True)
    if result.returncode != 0:
        print(f"error: concat falló: {result.stderr.decode(errors='replace')[-300:]}", file=sys.stderr)
        return False
    return output.exists()
