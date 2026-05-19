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

    _create_environment(spec)
    subject = _create_subject(spec)
    _create_lighting(spec)
    camera = _create_camera(spec, subject)
    _animate_subject(subject, spec)
    _animate_camera(camera, spec)

    if spec.get("weather") == "rain":
        _create_rain_proxy()
    if spec.get("weather") in {"fog", "snow"}:
        _create_atmosphere_proxy(spec)

    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / "latest_preview.blend"))
    bpy.ops.render.render(animation=True)
    _write_manifest(spec, shot_path, output_dir)
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
    scene.world = bpy.data.worlds.new("director_world") if scene.world is None else scene.world
    scene.world.color = (0.015, 0.015, 0.025)


def _create_environment(spec: dict) -> None:
    scene_name = spec["scene"].lower()
    if "street" in scene_name or "cyberpunk" in scene_name:
        _create_cyberpunk_street()
    elif "forest" in scene_name:
        _create_forest()
    elif "room" in scene_name or "interior" in scene_name:
        _create_room()
    elif "desert" in scene_name:
        _create_desert()
    else:
        _create_stage()


def _create_stage() -> None:
    _add_floor("stage_floor", color=(0.06, 0.06, 0.07, 1.0))


def _create_cyberpunk_street() -> None:
    _add_floor("wet_asphalt", color=(0.015, 0.015, 0.02, 1.0))
    for index, x in enumerate([-5, -3, 3, 5]):
        height = random.uniform(3.5, 7.0)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, random.uniform(2.5, 5.0), height / 2))
        building = bpy.context.object
        building.name = f"background_building_{index}"
        building.dimensions = (1.2, 1.2, height)
        building.data.materials.append(_material("building_dark", (0.02, 0.025, 0.035, 1.0)))

        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 1.8, random.uniform(1.4, 3.2)))
        sign = bpy.context.object
        sign.name = f"neon_sign_{index}"
        sign.dimensions = (1.0, 0.05, 0.25)
        color = (1.0, 0.05, 0.15, 1.0) if index % 2 == 0 else (0.0, 0.7, 1.0, 1.0)
        sign.data.materials.append(_emission_material(f"neon_{index}", color, 2.5))


def _create_forest() -> None:
    _add_floor("forest_ground", color=(0.025, 0.08, 0.035, 1.0))
    bark = _material("tree_bark", (0.18, 0.09, 0.035, 1.0))
    leaves = _material("tree_canopy", (0.02, 0.20, 0.06, 1.0))
    for index in range(18):
        x = random.uniform(-6, 6)
        y = random.uniform(-1, 7)
        if abs(x) < 1.2 and y < 2.5:
            continue
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.12, depth=random.uniform(2.0, 4.0), location=(x, y, 1.2))
        trunk = bpy.context.object
        trunk.name = f"tree_trunk_{index}"
        trunk.data.materials.append(bark)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.5, 0.9), location=(x, y, random.uniform(2.4, 4.2)))
        canopy = bpy.context.object
        canopy.name = f"tree_canopy_{index}"
        canopy.data.materials.append(leaves)


def _create_room() -> None:
    _add_floor("room_floor", color=(0.12, 0.11, 0.10, 1.0))
    wall_material = _material("warm_wall", (0.22, 0.20, 0.18, 1.0))
    for name, location, scale in [
        ("back_wall", (0, 4, 2), (8, 0.12, 4)),
        ("left_wall", (-4, 0, 2), (0.12, 8, 4)),
        ("right_wall", (4, 0, 2), (0.12, 8, 4)),
    ]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        wall = bpy.context.object
        wall.name = name
        wall.dimensions = scale
        wall.data.materials.append(wall_material)


def _create_desert() -> None:
    _add_floor("desert_sand", color=(0.55, 0.40, 0.19, 1.0))
    rock_material = _material("desert_rock", (0.24, 0.18, 0.12, 1.0))
    for index in range(8):
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=1,
            radius=random.uniform(0.25, 0.8),
            location=(random.uniform(-5, 5), random.uniform(1, 6), random.uniform(0.15, 0.45)),
        )
        rock = bpy.context.object
        rock.name = f"desert_rock_{index}"
        rock.scale.z = random.uniform(0.3, 0.7)
        rock.data.materials.append(rock_material)


def _add_floor(name: str, *, color: tuple[float, float, float, float]) -> None:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -0.05))
    floor = bpy.context.object
    floor.name = name
    floor.dimensions = (14, 14, 0.1)
    floor.data.materials.append(_material(f"{name}_material", color))


def _create_subject(spec: dict) -> bpy.types.Object:
    subject_name = spec["subject"].lower()
    if "character" in subject_name or "hero" in subject_name or "humano" in subject_name:
        subject = _create_humanoid_proxy(spec)
    elif "vehicle" in subject_name:
        subject = _create_vehicle_proxy(spec)
    else:
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 1))
        subject = bpy.context.object
    subject.name = f"subject_{_slug(spec['subject'])}"

    if not subject.data.materials:
        subject.data.materials.append(_emission_material("subject_neon_material", (0.1, 0.8, 1.0, 1.0), 0.5))
    return subject


def _create_lighting(spec: dict) -> None:
    lighting = spec["lighting"].lower()
    bpy.ops.object.light_add(type="AREA", location=(0, -4, 5))
    key = bpy.context.object
    key.name = "key_light"
    key.data.energy = 750 if "neon" in lighting else 500
    key.data.size = 4
    if "sunset" in lighting:
        key.data.color = (1.0, 0.65, 0.35)
    elif "moonlight" in lighting:
        key.data.color = (0.55, 0.65, 1.0)

    bpy.ops.object.light_add(type="POINT", location=(-3, 2, 3))
    rim = bpy.context.object
    rim.name = "rim_light"
    rim.data.energy = 250
    rim.data.color = (1.0, 0.1, 0.2)


def _create_camera(spec: dict, subject: bpy.types.Object) -> bpy.types.Object:
    movement = spec["camera"].get("movement", "orbit").lower()
    location = (0, -7, 3.2) if movement == "push_in" else (5, -7, 4)
    if movement == "static":
        location = (3.5, -6, 3.2)
    bpy.ops.object.camera_add(location=location, rotation=(math.radians(60), 0, math.radians(37)))
    camera = bpy.context.object
    camera.name = "director_camera"
    camera.data.lens = int(spec["camera"].get("lens_mm", 35))
    bpy.context.scene.camera = camera
    _look_at(camera, subject.location)
    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    constraint.target = subject
    return camera


def _animate_subject(subject: bpy.types.Object, spec: dict) -> None:
    frame_end = int(spec["duration_seconds"] * spec["fps"])
    action = spec["action"].lower()
    start_x = -2.0 if "runs" in action else -1.5
    end_x = 2.0 if "runs" in action else 1.5
    if "stands" in action:
        start_x = end_x = 0

    subject.location = (start_x, 0, 1)
    subject.keyframe_insert(data_path="location", frame=1)
    subject.rotation_euler = (0, 0, 0)
    subject.keyframe_insert(data_path="rotation_euler", frame=1)

    subject.location = (end_x, 0, 1)
    subject.rotation_euler = (0, 0, math.radians(180))
    subject.keyframe_insert(data_path="location", frame=frame_end)
    subject.keyframe_insert(data_path="rotation_euler", frame=frame_end)


def _animate_camera(camera: bpy.types.Object, spec: dict) -> None:
    frame_end = int(spec["duration_seconds"] * spec["fps"])
    movement = spec["camera"].get("movement", "orbit").lower()
    if movement == "static":
        camera.keyframe_insert(data_path="location", frame=1)
        camera.keyframe_insert(data_path="location", frame=frame_end)
        return
    if movement == "push_in":
        camera.location = (0, -8, 3.2)
        camera.keyframe_insert(data_path="location", frame=1)
        camera.location = (0, -4.2, 2.4)
        camera.keyframe_insert(data_path="location", frame=frame_end)
        return
    if movement == "dolly":
        camera.location = (-4, -6, 3.2)
        camera.keyframe_insert(data_path="location", frame=1)
        camera.location = (4, -6, 3.2)
        camera.keyframe_insert(data_path="location", frame=frame_end)
        return

    camera.location = (5, -7, 4)
    camera.keyframe_insert(data_path="location", frame=1)
    camera.location = (-5, -7, 4)
    camera.keyframe_insert(data_path="location", frame=frame_end)


def _create_humanoid_proxy(spec: dict) -> bpy.types.Object:
    body_material = _emission_material("hero_body_material", (0.1, 0.8, 1.0, 1.0), 0.35)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.0))
    body = bpy.context.object
    body.name = "humanoid_body"
    body.dimensions = (0.7, 0.35, 1.35)
    body.data.materials.append(body_material)

    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.32, location=(0, 0, 1.85))
    head = bpy.context.object
    head.name = "humanoid_head"
    head.data.materials.append(body_material)
    head.parent = body
    return body


def _create_vehicle_proxy(spec: dict) -> bpy.types.Object:
    material = _material("vehicle_material", (0.05, 0.08, 0.10, 1.0))
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.45))
    vehicle = bpy.context.object
    vehicle.name = "vehicle_body"
    vehicle.dimensions = (2.3, 1.1, 0.55)
    vehicle.data.materials.append(material)
    return vehicle


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


def _create_atmosphere_proxy(spec: dict) -> None:
    weather = spec.get("weather")
    color = (0.75, 0.82, 0.95, 0.18) if weather == "fog" else (0.9, 0.95, 1.0, 0.45)
    material = _material(f"{weather}_proxy_material", color)
    for index in range(36):
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=12,
            ring_count=6,
            radius=random.uniform(0.03, 0.08) if weather == "snow" else random.uniform(0.35, 0.9),
            location=(random.uniform(-6, 6), random.uniform(-3, 5), random.uniform(0.8, 4.8)),
        )
        particle = bpy.context.object
        particle.name = f"{weather}_proxy_{index:03d}"
        particle.data.materials.append(material)


def _material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    return material


def _emission_material(name: str, color: tuple[float, float, float, float], strength: float) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Emission Color"].default_value = color
    bsdf.inputs["Emission Strength"].default_value = strength
    return material


def _write_manifest(spec: dict, shot_path: Path, output_dir: Path) -> None:
    manifest = {
        "shot": str(shot_path),
        "scene": spec["scene"],
        "duration_seconds": spec["duration_seconds"],
        "fps": spec["fps"],
        "frame_count": int(spec["duration_seconds"] * spec["fps"]),
        "resolution": spec["resolution"],
        "output_prefix": str(output_dir / "shot_"),
    }
    with (output_dir / "manifest.json").open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)
        file.write("\n")


def _look_at(obj: bpy.types.Object, target) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")[:40]


if __name__ == "__main__":
    raise SystemExit(main())
