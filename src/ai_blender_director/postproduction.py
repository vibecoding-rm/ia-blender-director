"""Post-producción de Shorts: gancho + concat + audio (voz/SFX) + subtítulos.

Convierte los clips renderizados por Blender en un Short listo para publicar
siguiendo las reglas de retención documentadas en docs/estrategia_contenido.md:
tarjeta de gancho con sting, whoosh en cada corte, narración TTS y subtítulos
quemados que funcionan sin sonido.
"""

from __future__ import annotations

import sys
from pathlib import Path
import ffmpeg

from .branding import make_hook_clip
from .commands.video import H264_OUTPUT_OPTIONS
from .sfx import mix_audio_track
from .subtitles import caption_timings, chunk_narration, write_ass
from .tts import media_duration, synthesize

HOOK_DURATION = 1.4

ZOOM_PRESETS = {
    'zoom_in': {
        'z': 'min(1.0+0.0015*on,1.5)',
        'x': 'iw/2-(iw/zoom/2)',
        'y': 'ih/2-(ih/zoom/2)'
    },
    'zoom_out': {
        'z': 'max(1.5-0.0015*on,1.0)',
        'x': 'iw/2-(iw/zoom/2)',
        'y': 'ih/2-(ih/zoom/2)'
    },
    'pan_left': {
        'z': '1.3',
        'x': '(iw-iw/zoom)*max(1.0-on/100,0.0)',
        'y': 'ih/2-(ih/zoom/2)'
    },
    'pan_right': {
        'z': '1.3',
        'x': '(iw-iw/zoom)*min(on/100,1.0)',
        'y': 'ih/2-(ih/zoom/2)'
    }
}


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
    narration_wav: Path | None = None,
    lower_third: tuple[str, str] | None = None,
    ticker_text: str | None = None,
    corner_bug: str | None = None,
) -> Path | None:
    """Ensambla el Short final. Devuelve la ruta del video terminado o None."""
    output_video.parent.mkdir(parents=True, exist_ok=True)
    work = output_video.parent
    stem = output_video.stem

    # ── 1. Gancho ────────────────────────────────────────────────────────────
    clips = list(shot_videos)
    durations = list(shot_durations)
    hook_duration = 0.0
    if hook_title:
        hook_clip = work / f"{stem}_hook.mp4"
        if make_hook_clip(hook_title, hook_clip, resolution=resolution, fps=fps, duration=HOOK_DURATION):
            clips.insert(0, hook_clip)
            durations.insert(0, HOOK_DURATION)
            hook_duration = HOOK_DURATION
            print(f"  gancho: {hook_clip.name}")
        else:
            print("warning: no se pudo crear la tarjeta de gancho", file=sys.stderr)

    # Load ShotSpecs to determine transitions and camera movements
    shot_specs = []
    for sv in shot_videos:
        spec_path = sv.parent / "shot.json"
        if not spec_path.exists():
            spec_path = sv.parent.parent / "shot.json"
        
        spec = None
        if spec_path.exists():
            try:
                from .io import load_shot_spec
                spec = load_shot_spec(spec_path)
            except Exception as e:
                print(f"warning: error loading shot spec from {spec_path}: {e}")
        shot_specs.append(spec)

    # ── 2. Video assembly filter graph construction ──────────────────────────
    video_streams = []
    for i, clip_path in enumerate(clips):
        input_node = ffmpeg.input(str(clip_path))
        v = input_node.video
        
        # Apply Ken Burns effect (zoompan) to static shots
        shot_idx = i - 1 if hook_title else i
        if shot_idx >= 0 and shot_idx < len(shot_specs):
            spec = shot_specs[shot_idx]
            if spec and spec.camera.movement.lower() == 'static':
                preset_keys = list(ZOOM_PRESETS.keys())
                preset_name = preset_keys[shot_idx % len(preset_keys)]
                preset = ZOOM_PRESETS[preset_name]
                v = v.filter(
                    'zoompan',
                    z=preset['z'],
                    x=preset['x'],
                    y=preset['y'],
                    d=1,
                    s=f"{resolution[0]}x{resolution[1]}",
                    fps=fps
                )
        
        # Standardize video characteristics
        v = v.filter('scale', w=resolution[0], h=resolution[1])
        v = v.filter('setsar', sar='1/1')
        v = v.filter('settb', tb='1/1000000')
        v = v.filter('setpts', 'PTS-STARTPTS')
        video_streams.append(v)

    # Determine transitions
    transitions = []
    if hook_title:
        transitions.append(('none', 0.0))
    for spec in shot_specs[:-1]:
        if spec and spec.transition:
            transitions.append((spec.transition.type, spec.transition.duration))
        else:
            transitions.append(('none', 0.0))

    # Cap transitions to 50% of min duration of the adjacent clips
    for i in range(len(clips) - 1):
        t_type, t_dur = transitions[i]
        if t_type == 'none':
            transitions[i] = ('none', 0.0)
        else:
            max_d = min(durations[i], durations[i+1]) * 0.5
            if t_dur > max_d:
                transitions[i] = (t_type, max_d)

    # Concatenate / Transition video streams
    current_v = video_streams[0]
    accumulated_duration = durations[0]
    cut_times = []

    for i in range(len(clips) - 1):
        t_type, t_dur = transitions[i]
        v_next = video_streams[i+1]
        
        if t_type == 'none' or t_dur <= 0:
            current_v = ffmpeg.concat(current_v, v_next, v=1, a=0)
            midpoint = accumulated_duration
            cut_times.append(round(midpoint, 3))
            accumulated_duration += durations[i+1]
        else:
            offset = accumulated_duration - t_dur
            current_v = ffmpeg.filter((current_v, v_next), 'xfade', transition=t_type, duration=t_dur, offset=offset)
            midpoint = accumulated_duration - t_dur / 2.0
            cut_times.append(round(midpoint, 3))
            accumulated_duration = accumulated_duration + durations[i+1] - t_dur

    video_duration = accumulated_duration

    # ── 3. Narración ─────────────────────────────────────────────────────────
    # Si se pasa un WAV ya sintetizado (p.ej. el usado para el lip-sync), se
    # reutiliza para no sintetizar dos veces; los subtítulos siguen usando
    # narration_text.
    narration_duration = 0.0
    if narration_wav is not None and narration_wav.exists():
        narration_duration = media_duration(narration_wav) or 0.0
    elif narration_text:
        narration_wav = work / f"{stem}_narracion.wav"
        if synthesize(narration_text, narration_wav, voice=voice):
            narration_duration = media_duration(narration_wav) or 0.0
        else:
            narration_wav = None
            print("warning: falló la síntesis de voz", file=sys.stderr)
    elif voice and voice.exists() and voice.suffix == '.wav':
        narration_wav = voice
        narration_duration = media_duration(voice) or 0.0

    # Apply padding if narration extends beyond video
    narration_end = hook_duration + narration_duration
    if narration_wav and narration_end > video_duration + 0.05:
        pad = narration_end - video_duration + 0.3
        current_v = current_v.filter('tpad', stop_mode='clone', stop_duration=pad)
        video_duration += pad

    # ── 4. Subtítulos quemados ───────────────────────────────────────────────
    if subtitles and narration_text and narration_duration > 0:
        chunks = chunk_narration(narration_text)
        timings = caption_timings(chunks, audio_duration=narration_duration, start_offset=hook_duration)
        ass_path = work / f"{stem}_subs.ass"
        write_ass(timings, ass_path, play_res=resolution)
        escaped_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
        current_v = current_v.filter('ass', filename=escaped_ass)

    # ── 4b. Gráficos de broadcast (lower-third, ticker, bug) ──────────────────
    if lower_third or ticker_text or corner_bug:
        from .broadcast import apply_overlays
        current_v = apply_overlays(
            current_v, work, stem,
            resolution=resolution, fps=fps, video_duration=video_duration,
            lower_third=lower_third, ticker_text=ticker_text, corner_bug=corner_bug,
        )

    # Compile and run the video assembly graph
    base = work / f"{stem}_base.mp4"
    stream = ffmpeg.output(current_v, str(base), an=None, **H264_OUTPUT_OPTIONS).overwrite_output()
    try:
        ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        print(f"error: video assembly falló: {e.stderr.decode(errors='replace')[-300:]}", file=sys.stderr)
        return None

    # ── 5. Mezcla de audio (voz + sting + whooshes) ──────────────────────────
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

    # ── 6. Renombrar al destino final ────────────────────────────────────────
    if current != output_video:
        if output_video.exists():
            output_video.unlink()
        current.replace(output_video)
    return output_video



