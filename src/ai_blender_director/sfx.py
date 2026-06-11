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

ROOT = Path(__file__).resolve().parents[2]
SFX_DIR = ROOT / "assets" / "audio" / "sfx"
MUSIC_BED = ROOT / "assets" / "audio" / "music_bed.mp3"

# name -> ffmpeg lavfi recipe (mono 44.1k, short)
_RECIPES: dict[str, list[str]] = {
    # Sting de noticiero: dos tonos urgentes descendentes con eco corto
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
    # Whoosh: ruido blanco con barrido de paso-banda y fade rápido
    "whoosh": [
        "-f", "lavfi",
        "-i", "anoisesrc=color=white:duration=0.35:amplitude=0.7",
        "-af",
        "bandpass=frequency=900:width_type=h:width=600,afade=t=in:st=0:d=0.08,afade=t=out:st=0.18:d=0.17,volume=0.5",
    ],
    # Ding: campanita para el dato clave / punchline
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
    inputs: list[str] = ["-i", str(video)]
    labels: list[str] = []
    filters: list[str] = []
    index = 1

    def _add(path: Path, delay_s: float, volume: float = 1.0) -> None:
        nonlocal index
        inputs.extend(["-i", str(path)])
        delay_ms = max(0, int(delay_s * 1000))
        filters.append(f"[{index}:a]volume={volume},adelay={delay_ms}|{delay_ms}[a{index}]")
        labels.append(f"[a{index}]")
        index += 1

    if narration_wav is not None and narration_wav.exists():
        _add(narration_wav, narration_delay, 1.0)
    if with_sting and "sting" in sfx:
        _add(sfx["sting"], 0.0, 0.9)
    if "whoosh" in sfx:
        for t in cut_times:
            _add(sfx["whoosh"], t, 0.6)
    if MUSIC_BED.exists():
        _add(MUSIC_BED, 0.0, 0.12)

    if not labels:
        print("warning: nada que mezclar (sin narración ni SFX)", file=sys.stderr)
        return False

    filter_complex = ";".join(filters) + f";{''.join(labels)}amix=inputs={len(labels)}:normalize=0[aout]"
    result = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *inputs,
         "-filter_complex", filter_complex,
         "-map", "0:v:0", "-map", "[aout]",
         "-c:v", "copy", "-c:a", "aac", "-shortest", str(output)],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"error: mezcla de audio falló: {result.stderr.decode(errors='replace')[-300:]}", file=sys.stderr)
        return False
    return output.exists()
