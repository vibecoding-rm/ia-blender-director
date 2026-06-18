from __future__ import annotations
import sys
import random
import bpy
from pathlib import Path
from .core import load_json, clear_scene, write_manifest
from .assets import resolve_asset_refs
from .environment import create_environment, create_rain_system, create_fog_volume, create_snow_system
from .subject import create_subject
from .lighting import create_lighting
from .camera import create_camera
from .animation import animate_subject, animate_camera
from .materials import is_claymation, apply_claymation_style
from .passes import render_control_passes
from .lipsync import apply_jaw_track, load_jaw_track_from_json

def main() -> int:
    shot_path, output_dir, profile, preview_only = parse_args(sys.argv)
    spec = load_json(shot_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    asset_refs = resolve_asset_refs(spec)

    random.seed(spec["seed"])
    clear_scene()
    configure_render(spec, output_dir, profile)

    create_environment(spec, asset_refs)
    subject = create_subject(spec, asset_refs)
    create_lighting(spec)
    camera = create_camera(spec, subject)
    animate_subject(subject, spec, asset_refs)
    animate_camera(camera, spec)

    # Lip-sync por audio: si el spec trae un JSON de visemas (Rhubarb), conduce
    # el pico desde la narración en vez de la animación Talk genérica.
    visemes_path = spec.get("visemes_path")
    if visemes_path:
        frame_end = int(spec["duration_seconds"] * spec["fps"])
        jaw_track = load_jaw_track_from_json(
            visemes_path, int(spec["fps"]), start_offset=float(spec.get("narration_offset", 0.0))
        )
        if apply_jaw_track(subject, jaw_track, frame_end=frame_end):
            print(f"  lip-sync aplicado desde {visemes_path}")

    weather = spec.get("weather")
    if weather == "rain":
        create_rain_system()
    elif weather == "fog":
        create_fog_volume()
    elif weather == "snow":
        create_snow_system()

    if is_claymation(spec):
        apply_claymation_style()

    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / "latest_preview.blend"))

    if preview_only:
        preview_path = render_preview_frame(spec, output_dir)
        write_manifest(spec, shot_path, output_dir, profile, {"preview_frame": str(preview_path)}, asset_refs)
        return 0

    bpy.ops.render.render(animation=True)
    passes = render_control_passes(output_dir, subject)
    write_manifest(spec, shot_path, output_dir, profile, passes, asset_refs)
    return 0

def parse_args(argv: list[str]) -> tuple[Path, Path, str, bool]:
    if "--" not in argv:
        raise SystemExit("Usage: blender --background --python render_shot.py -- shot.json output_dir [preview|final] [--preview-only]")
    script_args = argv[argv.index("--") + 1:]
    preview_only = "--preview-only" in script_args
    positional = [a for a in script_args if not a.startswith("--")]
    if len(positional) not in {2, 3}:
        raise SystemExit("Usage: blender --background --python render_shot.py -- shot.json output_dir [preview|final] [--preview-only]")
    profile = positional[2] if len(positional) == 3 else "preview"
    if profile not in {"preview", "final"}:
        raise SystemExit("profile must be 'preview' or 'final'")
    return Path(positional[0]).resolve(), Path(positional[1]).resolve(), profile, preview_only

def configure_render(spec: dict, output_dir: Path, profile: str) -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = int(spec["duration_seconds"] * spec["fps"])
    scene.frame_set(1)
    scene.render.fps = int(spec["fps"])
    resolution_scale = 0.5 if profile == "preview" else 1.0
    scene.render.resolution_x = max(320, int(spec["resolution"]["width"] * resolution_scale))
    scene.render.resolution_y = max(240, int(spec["resolution"]["height"] * resolution_scale))
    scene.render.filepath = str(output_dir / "shot_")
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD" if profile == "preview" else "BEST"
    scene.render.ffmpeg.constant_rate_factor = "HIGH" if profile == "preview" else "PERC_LOSSLESS"
    scene.eevee.taa_render_samples = 16 if profile == "preview" else 64
    if profile == "final":
        scene.eevee.taa_render_samples = 128
    configure_view_transform(scene)
    configure_eevee(scene, profile)
    scene.world = bpy.data.worlds.new("director_world") if scene.world is None else scene.world
    scene.world.color = (0.045, 0.05, 0.07)

def configure_view_transform(scene: bpy.types.Scene) -> None:
    if "AgX" in {item.name for item in scene.view_settings.bl_rna.properties["view_transform"].enum_items}:
        scene.view_settings.view_transform = "AgX"
    available_looks = {item.name for item in scene.view_settings.bl_rna.properties["look"].enum_items}
    if "AgX - Medium High Contrast" in available_looks:
        scene.view_settings.look = "AgX - Medium High Contrast"
    elif "Medium High Contrast" in available_looks:
        scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1

def configure_eevee(scene: bpy.types.Scene, profile: str) -> None:
    eevee = scene.eevee
    _set_if_present(eevee, "use_gtao", True)
    _set_if_present(eevee, "gtao_distance", 4)
    _set_if_present(eevee, "gtao_factor", 1.25)
    _set_if_present(eevee, "use_bloom", True)
    _set_if_present(eevee, "bloom_threshold", 0.8)
    _set_if_present(eevee, "bloom_intensity", 0.07 if profile == "preview" else 0.11)
    _set_if_present(eevee, "use_raytracing", True)
    _set_if_present(eevee, "use_motion_blur", True)
    _set_if_present(eevee, "motion_blur_shutter", 0.35)

def _set_if_present(obj: object, attr: str, value: object) -> None:
    if hasattr(obj, attr):
        try:
            setattr(obj, attr, value)
        except TypeError:
            pass

def render_preview_frame(spec: dict, output_dir: Path) -> Path:
    scene = bpy.context.scene
    frame_end = int(spec["duration_seconds"] * spec["fps"])
    mid_frame = max(1, frame_end // 2)
    scene.frame_set(mid_frame)

    orig_percentage = scene.render.resolution_percentage
    orig_format = scene.render.image_settings.file_format
    orig_filepath = scene.render.filepath

    preview_path = output_dir / "preview_frame.png"
    try:
        scene.render.resolution_percentage = 25
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = str(output_dir / "preview_frame")
        bpy.ops.render.render(write_still=True)
    finally:
        scene.render.resolution_percentage = orig_percentage
        scene.render.image_settings.file_format = orig_format
        scene.render.filepath = orig_filepath

    numbered = output_dir / f"preview_frame{mid_frame:04d}.png"
    if numbered.exists() and not preview_path.exists():
        numbered.rename(preview_path)
    return preview_path
