from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import bpy


def main() -> int:
    shot_path, output_dir = _parse_args(sys.argv)
    spec = _load_json(shot_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    random.seed(spec["seed"])
    _clear_scene()
    _configure_render(spec, output_dir)

    subject = _create_subject(spec)
    _create_lighting(spec)
    camera = _create_camera(spec, subject)
    _animate_subject(subject, spec)
    _animate_camera(camera, spec)

    if spec.get("weather") == "rain":
        _create_rain_proxy()

    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / "latest_preview.blend"))
    bpy.ops.render.render(animation=True)
    return 0


def _parse_args(argv: list[str]) -> tuple[Path, Path]:
    if "--" not in argv:
        raise SystemExit("Usage: blender --background --python render_shot.py -- shot.json output_dir")
    script_args = argv[argv.index("--") + 1 :]
    if len(script_args) != 2:
        raise SystemExit("Usage: blender --background --python render_shot.py -- shot.json output_dir")
    return Path(script_args[0]).resolve(), Path(script_args[1]).resolve()


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def _configure_render(spec: dict, output_dir: Path) -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = int(spec["duration_seconds"] * spec["fps"])
    scene.frame_set(1)
    scene.render.fps = int(spec["fps"])
    scene.render.resolution_x = int(spec["resolution"]["width"])
    scene.render.resolution_y = int(spec["resolution"]["height"])
    scene.render.filepath = str(output_dir / "shot_")
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.eevee.taa_render_samples = 64


def _create_subject(spec: dict) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 1))
    subject = bpy.context.object
    subject.name = f"subject_{_slug(spec['subject'])}"

    material = bpy.data.materials.new("subject_neon_material")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.1, 0.8, 1.0, 1.0)
    bsdf.inputs["Emission Color"].default_value = (0.0, 0.5, 1.0, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.5
    subject.data.materials.append(material)
    return subject


def _create_lighting(spec: dict) -> None:
    bpy.ops.object.light_add(type="AREA", location=(0, -4, 5))
    key = bpy.context.object
    key.name = "key_light"
    key.data.energy = 500
    key.data.size = 4

    bpy.ops.object.light_add(type="POINT", location=(-3, 2, 3))
    rim = bpy.context.object
    rim.name = "rim_light"
    rim.data.energy = 250
    rim.data.color = (1.0, 0.1, 0.2)


def _create_camera(spec: dict, subject: bpy.types.Object) -> bpy.types.Object:
    bpy.ops.object.camera_add(location=(5, -7, 4), rotation=(math.radians(60), 0, math.radians(37)))
    camera = bpy.context.object
    camera.name = "director_camera"
    camera.data.lens = int(spec["camera"].get("lens_mm", 35))
    bpy.context.scene.camera = camera
    _look_at(camera, subject.location)
    return camera


def _animate_subject(subject: bpy.types.Object, spec: dict) -> None:
    frame_end = int(spec["duration_seconds"] * spec["fps"])
    subject.location = (-1.5, 0, 1)
    subject.keyframe_insert(data_path="location", frame=1)
    subject.rotation_euler = (0, 0, 0)
    subject.keyframe_insert(data_path="rotation_euler", frame=1)

    subject.location = (1.5, 0, 1)
    subject.rotation_euler = (0, 0, math.radians(180))
    subject.keyframe_insert(data_path="location", frame=frame_end)
    subject.keyframe_insert(data_path="rotation_euler", frame=frame_end)


def _animate_camera(camera: bpy.types.Object, spec: dict) -> None:
    frame_end = int(spec["duration_seconds"] * spec["fps"])
    camera.location = (5, -7, 4)
    camera.keyframe_insert(data_path="location", frame=1)
    camera.location = (-5, -7, 4)
    camera.keyframe_insert(data_path="location", frame=frame_end)


def _create_rain_proxy() -> None:
    material = bpy.data.materials.new("rain_proxy_material")
    material.diffuse_color = (0.6, 0.8, 1.0, 0.35)
    for index in range(80):
        x = random.uniform(-6, 6)
        y = random.uniform(-6, 3)
        z = random.uniform(2, 7)
        bpy.ops.mesh.primitive_cube_add(size=0.025, location=(x, y, z))
        drop = bpy.context.object
        drop.name = f"rain_drop_{index:03d}"
        drop.scale.z = random.uniform(5, 12)
        drop.data.materials.append(material)


def _look_at(obj: bpy.types.Object, target) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")[:40]


if __name__ == "__main__":
    raise SystemExit(main())
