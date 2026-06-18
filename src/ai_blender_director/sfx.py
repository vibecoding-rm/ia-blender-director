"""Efectos de sonido y mezcla de audio para los Shorts.

Los SFX se sintetizan localmente con los generadores de ffmpeg (sine/anoisesrc),
así que son 100% libres de derechos. Se generan una sola vez en
assets/audio/sfx/ y se reutilizan.

Mezcla final = narración (con retardo tras el gancho) + sting de apertura +
whoosh en cada corte de plano.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import ffmpeg

ROOT = Path(__file__).resolve().parents[2]
SFX_DIR = ROOT / "assets" / "audio" / "sfx"
MUSIC_BED = ROOT / "assets" / "audio" / "music_bed.mp3"

# name -> ffmpeg lavfi recipe (mono 44.1k, short)
_RECIPES: dict[str, list[str]] = {
    "sting": [
        "-f", "lavfi",
        "-i", "sine=frequency=880:duration=0.18,asetrate=44100",
        "-f", "lavfi",
        "-i", "sine=frequency=659:duration=0.22",
        "-f", "lavfi",
        "-i", "sine=frequency=523:duration=0.45",
        "-filter_complex",
        "[0][1][2]concat=n=3:v=0:a=1,aecho=0.7:0.6:60:0.35,afade=t=out:st=0.7:d=0.15,volume=0.85",
    ],
    "whoosh": [
        "-f", "lavfi",
        "-i", "anoisesrc=color=white:duration=0.35:amplitude=0.7",
        "-af",
        "bandpass=frequency=900:width_type=h:width=600,afade=t=in:st=0:d=0.08,afade=t=out:st=0.18:d=0.17,volume=0.5",
    ],
    "ding": [
        "-f", "lavfi",
        "-i", "sine=frequency=1318:duration=0.5",
        "-af", "aecho=0.6:0.4:90:0.3,afade=t=out:st=0.1:d=0.4,volume=0.6",
    ],
}


def ensure_sfx() -> dict[str, Path]:
    """Genera los SFX si no existen. Devuelve {nombre: ruta}."""
    SFX_DIR.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, recipe in _RECIPES.items():
        path = SFX_DIR / f"{name}.wav"
        if not path.exists():
            result = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", *recipe, str(path)],
                capture_output=True,
            )
            if result.returncode != 0:
                print(f"warning: no se pudo sintetizar SFX '{name}': "
                      f"{result.stderr.decode(errors='replace')[-200:]}", file=sys.stderr)
                continue
        paths[name] = path
    return paths


def mix_audio_track(
    video: Path,
    output: Path,
    *,
    narration_wav: Path | None,
    narration_delay: float,
    cut_times: list[float],
    with_sting: bool,
) -> bool:
    """Mezcla narración + sting + whooshes sobre el video (video copiado tal cual).

    - narration_delay: segundos antes de que entre la voz (duración del gancho).
    - cut_times: momentos (s) de cambio de plano donde suena un whoosh.
    - El sting suena en t=0 (sobre la tarjeta de gancho).
    """
    sfx = ensure_sfx()
    
    video_input = ffmpeg.input(str(video))
    audio_streams = []
    voice_ctrl = None
    
    if narration_wav is not None and narration_wav.exists():
        narration_input = ffmpeg.input(str(narration_wav)).audio
        delay_ms = max(0, int(narration_delay * 1000))
        delayed_voice = narration_input.filter('volume', 1.0).filter('adelay', f"{delay_ms}|{delay_ms}")
        if MUSIC_BED.exists():
            split_node = delayed_voice.filter('asplit').node
            voice_mix = split_node[0]
            voice_ctrl = split_node[1]
            audio_streams.append(voice_mix)
        else:
            audio_streams.append(delayed_voice)
            voice_ctrl = None
            
    if with_sting and "sting" in sfx:
        sting_stream = ffmpeg.input(str(sfx["sting"])).audio.filter('volume', 0.9)
        audio_streams.append(sting_stream)
        
    if "whoosh" in sfx:
        for t in cut_times:
            delay_ms = max(0, int(t * 1000))
            whoosh_stream = ffmpeg.input(str(sfx["whoosh"])).audio.filter('volume', 0.6).filter('adelay', f"{delay_ms}|{delay_ms}")
            audio_streams.append(whoosh_stream)
            
    if MUSIC_BED.exists():
        bgm_stream = ffmpeg.input(str(MUSIC_BED)).audio
        if voice_ctrl:
            bgm_raw = bgm_stream.filter('volume', 0.25)
            bgm_ducked = ffmpeg.filter((bgm_raw, voice_ctrl), 'sidechaincompress', threshold=0.05, ratio=4, attack=50, release=300)
            audio_streams.append(bgm_ducked)
        else:
            bgm_simple = bgm_stream.filter('volume', 0.1)
            audio_streams.append(bgm_simple)
            
    if not audio_streams:
        print("warning: nada que mezclar (sin narración ni SFX)", file=sys.stderr)
        return False
        
    aout = (
        ffmpeg
        .filter(audio_streams, 'amix', inputs=len(audio_streams), normalize=0)
        .filter('loudnorm', I=-14, TP=-1.5, LRA=11)
        .filter('apad')
    )
    stream = ffmpeg.output(
        video_input.video,
        aout,
        str(output),
        vcodec='copy',
        acodec='aac',
        audio_bitrate='192k',
        movflags='+faststart',
    ).global_args('-shortest').overwrite_output()
    
    cmd = ffmpeg.compile(stream)
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"error: mezcla de audio falló: {result.stderr.decode(errors='replace')[-300:]}", file=sys.stderr)
        return False
    return output.exists()
