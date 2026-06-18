"""
End-to-end video generation test.
Uses 3 solid-color dummy clips (no Blender needed) to test the full
postproduction pipeline: Ken Burns zoom + xfade transitions + audio mix.
"""
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, "src")

import ffmpeg
from ai_blender_director.postproduction import produce_short

# ── 1. Create 3 dummy video clips ─────────────────────────────────────────────
print("Creando clips de prueba...")
tmp = Path(tempfile.mkdtemp())
clips = []
colors = [("red", "static"), ("green", "orbit"), ("blue", "static")]
durations = [4.0, 3.0, 5.0]

for i, (color, movement) in enumerate(colors, 1):
    clip_dir = tmp / f"shot_{i}"
    clip_dir.mkdir()
    clip_path = clip_dir / "video.mp4"

    # Generate solid-color video
    (
        ffmpeg
        .input(f"color=c={color}:s=1280x720:d={durations[i-1]}", f="lavfi")
        .output(str(clip_path), r=25, vcodec="libx264", pix_fmt="yuv420p")
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )

    # Write shot.json with transition metadata
    shot_spec = {
        "scene": f"{color} scene",
        "style": "cinematic",
        "duration_seconds": int(durations[i-1]),
        "fps": 25,
        "resolution": {"width": 1280, "height": 720},
        "camera": {"movement": movement, "lens_mm": 35},
        "lighting": "soft light",
        "subject": "test subject",
        "action": "stands still",
        "seed": i * 100,
        "transition": {"type": "fade" if i < 3 else "none", "duration": 0.8},
    }
    (clip_dir / "shot.json").write_text(json.dumps(shot_spec), encoding="utf-8")
    clips.append(clip_path)
    print(f"  [OK] Clip {i}: {color} ({movement}) {durations[i-1]}s")

# -- 2. Run the full postproduction pipeline -----------------------------------
print("\nEnsamblando video con transiciones y Ken Burns...")
output = tmp / "final_output.mp4"

result = produce_short(
    shot_videos=clips,
    shot_durations=durations,
    output_video=output,
    resolution=(1280, 720),
    fps=25,
    hook_title="CYBERPUNK NEWS",
    narration_text=None,
    voice=None,
    subtitles=False,
    sfx=False,
)

# -- 3. Verify -----------------------------------------------------------------
if result and result.exists():
    probe = ffmpeg.probe(str(result))
    duration = float(probe["format"]["duration"])
    size_mb = result.stat().st_size / 1024 / 1024
    print("\n[SUCCESS] VIDEO GENERADO EXITOSAMENTE")
    print(f"   Archivo : {result}")
    print(f"   Duracion: {duration:.2f}s")
    print(f"   Tamano  : {size_mb:.2f} MB")
    print(f"\n   Copia el video para verlo:")
    print(f"   {result}")
else:
    print("\n[ERROR] No se genero el video")
    sys.exit(1)
