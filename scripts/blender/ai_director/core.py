from __future__ import annotations
import json
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[3]
ASSETS_ROOT = ROOT / "assets"

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)

def write_manifest(
    spec: dict,
    shot_path: Path,
    output_dir: Path,
    profile: str,
    passes: dict[str, str],
    asset_refs: dict,
) -> None:
    frame_start = 1
    frame_end = int(spec["duration_seconds"] * spec["fps"])
    scene = bpy.context.scene
    manifest = {
        "job_id": output_dir.name,
        "profile": profile,
        "shot": str(shot_path),
        "scene": spec["scene"],
        "duration_seconds": spec["duration_seconds"],
        "fps": spec["fps"],
        "frame_start": frame_start,
        "frame_end": frame_end,
        "frame_count": frame_end,
        "resolution": spec["resolution"],
        "render_resolution": {
            "width": scene.render.resolution_x,
            "height": scene.render.resolution_y,
        },
        "output_prefix": str(output_dir / "shot_"),
        "video": str(output_dir / f"shot_{frame_start:04d}-{frame_end:04d}.mp4"),
        "blend_file": str(output_dir / "latest_preview.blend"),
        "passes": passes,
        "assets": asset_refs,
        "spec": spec,
    }
    with (output_dir / "manifest.json").open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)
        file.write("\n")

def look_at(obj: bpy.types.Object, target) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")[:40]

def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
