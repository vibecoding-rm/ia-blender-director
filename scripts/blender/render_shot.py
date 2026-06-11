from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
ASSETS_ROOT = ROOT / "assets"


def main() -> int:
    shot_path, output_dir, profile, preview_only = _parse_args(sys.argv)
    spec = _load_json(shot_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    asset_refs = _resolve_asset_refs(spec)

    random.seed(spec["seed"])
    _clear_scene()
    _configure_render(spec, output_dir, profile)

    _create_environment(spec, asset_refs)
    subject = _create_subject(spec, asset_refs)
    _create_lighting(spec)
    camera = _create_camera(spec, subject)
    _animate_subject(subject, spec, asset_refs)
    _animate_camera(camera, spec)

    weather = spec.get("weather")
    if weather == "rain":
        _create_rain_system()
    elif weather == "fog":
        _create_fog_volume()
    elif weather == "snow":
        _create_snow_system()

    if _is_claymation(spec):
        _apply_claymation_style()

    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / "latest_preview.blend"))

    if preview_only:
        preview_path = _render_preview_frame(spec, output_dir)
        _write_manifest(spec, shot_path, output_dir, profile, {"preview_frame": str(preview_path)}, asset_refs)
        return 0

    bpy.ops.render.render(animation=True)
    passes = _render_control_passes(output_dir, subject)
    _write_manifest(spec, shot_path, output_dir, profile, passes, asset_refs)
    return 0


def _parse_args(argv: list[str]) -> tuple[Path, Path, str, bool]:
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


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def _configure_render(spec: dict, output_dir: Path, profile: str) -> None:
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
    scene.eevee.taa_render_samples = 16 if profile == "preview" else 64
    scene.world = bpy.data.worlds.new("director_world") if scene.world is None else scene.world
    scene.world.color = (0.015, 0.015, 0.025)


def _create_environment(spec: dict, asset_refs: dict) -> None:
    environment = asset_refs.get("environment")
    if environment:
        print(f"Using environment asset: {environment['id']} ({environment['source']})")
        if environment.get("path"):
            imported = _import_glb(environment["path"], label="environment")
            if imported is not None:
                print(f"  Imported environment from: {environment['path']}")
                return
            print(f"  Import failed, falling back to procedural environment.")

    scene_name = spec["scene"].lower()
    if "studio" in scene_name or "news" in scene_name:
        _create_news_studio()
    elif "kitchen" in scene_name or "apartment" in scene_name:
        _create_kitchen()
    elif "rally" in scene_name or "plaza" in scene_name or "havana" in scene_name:
        _create_plaza_rally()
    elif "street" in scene_name or "cyberpunk" in scene_name:
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


def _create_news_studio() -> None:
    _add_floor("studio_floor", color=(0.88, 0.88, 0.90, 1.0))

    # Backdrop wall with deep-blue gradient feel
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 5, 2.2))
    backdrop = bpy.context.object
    backdrop.name = "news_backdrop"
    backdrop.dimensions = (14, 0.15, 5.0)
    backdrop.data.materials.append(_emission_material("backdrop_blue", (0.04, 0.10, 0.42, 1.0), 0.3))

    # News desk
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1.6, 0.52))
    desk = bpy.context.object
    desk.name = "news_desk"
    desk.dimensions = (2.8, 0.75, 1.04)
    desk.data.materials.append(_material("desk_dark", (0.10, 0.10, 0.16, 1.0)))

    # Glowing desk front panel
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1.22, 0.52))
    panel = bpy.context.object
    panel.name = "desk_panel"
    panel.dimensions = (2.75, 0.04, 1.00)
    panel.data.materials.append(_emission_material("panel_cyan", (0.0, 0.55, 1.0, 1.0), 1.8))

    # Three TV screens on backdrop. If branded textures exist (generated with
    # scripts/generate_screen_textures.py) they are used as emissive images;
    # otherwise fall back to flat colored screens.
    screens_dir = ASSETS_ROOT / "branding" / "screens"
    screen_images = ["screen_left.png", "screen_center.png", "screen_right.png"]
    for i, (sx, sz) in enumerate([(-3.2, 2.3), (0.0, 2.6), (3.2, 2.3)]):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(sx, 4.9, sz), rotation=(math.radians(90), 0, 0))
        screen = bpy.context.object
        screen.name = f"tv_screen_{i}"
        screen.scale = (1.7, 1.0, 1.0)
        image_path = screens_dir / screen_images[i]
        if image_path.exists():
            screen.data.materials.append(
                _image_emission_material(f"screen_{i}", str(image_path), 1.6)
            )
        else:
            color = (1.0, 0.18, 0.06, 1.0) if i != 1 else (0.08, 0.45, 1.0, 1.0)
            screen.data.materials.append(_emission_material(f"screen_{i}", color, 3.5))

    # Desk microphone (small prop that sells the "set" feeling on close-ups)
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.015, depth=0.35, location=(0.35, 1.45, 1.2))
    mic_stand = bpy.context.object
    mic_stand.name = "desk_mic_stand"
    mic_stand.rotation_euler = (math.radians(-18), 0, 0)
    mic_stand.data.materials.append(_material("mic_dark", (0.05, 0.05, 0.06, 1.0)))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8, radius=0.045, location=(0.35, 1.40, 1.38))
    mic_head = bpy.context.object
    mic_head.name = "desk_mic_head"
    mic_head.data.materials.append(_material("mic_foam", (0.65, 0.08, 0.10, 1.0)))

    # Side walls
    wall_mat = _material("studio_wall", (0.82, 0.84, 0.87, 1.0))
    for name, loc, dims in [
        ("studio_left",  (-6, 0, 2.2), (0.12, 12, 5.0)),
        ("studio_right", ( 6, 0, 2.2), (0.12, 12, 5.0)),
        ("studio_ceil",  ( 0, 0, 4.5), (12, 12, 0.12)),
    ]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        w = bpy.context.object
        w.name = name
        w.dimensions = dims
        w.data.materials.append(wall_mat)


def _create_kitchen() -> None:
    _add_floor("kitchen_floor", color=(0.52, 0.42, 0.32, 1.0))

    wall_mat = _material("kitchen_wall", (0.75, 0.70, 0.62, 1.0))
    for name, loc, dims in [
        ("back_wall",  (0,  4.0, 2.0), (8.0, 0.12, 4.0)),
        ("left_wall",  (-4, 0.0, 2.0), (0.12, 8.0, 4.0)),
        ("right_wall", ( 4, 0.0, 2.0), (0.12, 8.0, 4.0)),
    ]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        w = bpy.context.object
        w.name = name
        w.dimensions = dims
        w.data.materials.append(wall_mat)

    # Kitchen counter along back wall
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 3.6, 0.45))
    counter = bpy.context.object
    counter.name = "kitchen_counter"
    counter.dimensions = (4.5, 0.65, 0.90)
    counter.data.materials.append(_material("counter_mat", (0.20, 0.20, 0.22, 1.0)))

    # Rickety wooden table
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.5, 0.38))
    table = bpy.context.object
    table.name = "kitchen_table"
    table.dimensions = (1.5, 0.9, 0.76)
    table.data.materials.append(_material("table_wood", (0.28, 0.18, 0.10, 1.0)))

    # Old CRT TV on counter
    bpy.ops.mesh.primitive_cube_add(size=1, location=(1.6, 3.3, 1.12))
    tv = bpy.context.object
    tv.name = "old_tv_casing"
    tv.dimensions = (0.48, 0.35, 0.42)
    tv.data.materials.append(_material("tv_casing", (0.16, 0.14, 0.11, 1.0)))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(1.6, 3.14, 1.12))
    screen = bpy.context.object
    screen.name = "old_tv_screen"
    screen.dimensions = (0.40, 0.04, 0.34)
    screen.data.materials.append(_emission_material("tv_glow", (0.18, 0.48, 0.90, 1.0), 2.5))

    # Flickering single bulb — represented by emissive sphere
    bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4, radius=0.08, location=(0, 2, 3.6))
    bulb = bpy.context.object
    bulb.name = "ceiling_bulb"
    bulb.data.materials.append(_emission_material("bulb_warm", (1.0, 0.92, 0.72, 1.0), 8.0))


def _create_plaza_rally() -> None:
    _add_floor("plaza_ground", color=(0.34, 0.30, 0.26, 1.0))

    # Government-style building facade
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 7, 4.5))
    building = bpy.context.object
    building.name = "gov_facade"
    building.dimensions = (14, 2.5, 10.0)
    building.data.materials.append(_material("facade_mat", (0.70, 0.65, 0.55, 1.0)))

    # Poster / banner on facade
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 5.85, 3.8))
    poster = bpy.context.object
    poster.name = "rubio_poster"
    poster.dimensions = (3.0, 0.06, 2.2)
    poster.data.materials.append(_emission_material("poster_red", (0.75, 0.06, 0.06, 1.0), 1.2))

    # Street lamps
    for x in (-4.5, 0.0, 4.5):
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.06, depth=5.0,
                                             location=(x, 4.0, 2.5))
        pole = bpy.context.object
        pole.name = f"lamp_pole_{int(x)}"
        pole.data.materials.append(_material("pole_dark", (0.10, 0.10, 0.10, 1.0)))

        bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4, radius=0.12,
                                              location=(x, 4.0, 5.1))
        head = bpy.context.object
        head.name = f"lamp_head_{int(x)}"
        head.data.materials.append(_emission_material("lamp_warm", (1.0, 0.88, 0.65, 1.0), 4.0))

    # Side buildings
    for bx, bz in ((-6, 5), (6, 4)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(bx, 4, bz / 2))
        sb = bpy.context.object
        sb.name = f"side_building_{bx}"
        sb.dimensions = (2.5, 4.0, float(bz))
        sb.data.materials.append(_material("side_facade", (0.55, 0.50, 0.42, 1.0)))


def _add_floor(name: str, *, color: tuple[float, float, float, float]) -> None:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -0.05))
    floor = bpy.context.object
    floor.name = name
    floor.dimensions = (14, 14, 0.1)
    floor.data.materials.append(_material(f"{name}_material", color))


def _create_subject(spec: dict, asset_refs: dict) -> bpy.types.Object:
    character = asset_refs.get("character")
    if character:
        print(f"Using character asset: {character['id']} ({character['source']})")
        if character.get("path"):
            imported = _import_glb(character["path"], label="character")
            if imported is not None:
                imported.name = f"subject_{_slug(spec['subject'])}"
                imported.location = (0, 0, 0)
                _normalize_subject(imported)
                print(f"  Imported character from: {character['path']}")
                return imported
            print(f"  Import failed, falling back to procedural character.")

    subject_name = spec["subject"].lower()
    if character or "character" in subject_name or "hero" in subject_name or "humano" in subject_name:
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
    bright = any(w in lighting for w in ("bright", "studio", "broadcast", "daylight"))

    bpy.ops.object.light_add(type="AREA", location=(0, -4, 5))
    key = bpy.context.object
    key.name = "key_light"
    if bright:
        key.data.energy = 1600
    elif "neon" in lighting:
        key.data.energy = 750
    else:
        key.data.energy = 500
    key.data.size = 4
    if "sunset" in lighting:
        key.data.color = (1.0, 0.65, 0.35)
    elif "moonlight" in lighting:
        key.data.color = (0.55, 0.65, 1.0)

    bpy.ops.object.light_add(type="POINT", location=(-3, 2, 3))
    rim = bpy.context.object
    rim.name = "rim_light"
    rim.data.energy = 250
    rim.data.color = (1.0, 1.0, 1.0) if bright else (1.0, 0.1, 0.2)

    if bright:
        # Soft fill from the opposite side so studio scenes read flat and clean
        bpy.ops.object.light_add(type="AREA", location=(3, -3, 4))
        fill = bpy.context.object
        fill.name = "fill_light"
        fill.data.energy = 700
        fill.data.size = 5


def _create_camera(spec: dict, subject: bpy.types.Object) -> bpy.types.Object:
    lens_mm = int(spec["camera"].get("lens_mm", 35))
    height = _subject_height(subject)

    # Frame size by lens role: 85mm close-up (upper body), 24mm wide establishing,
    # 35-50mm medium shot. Distance derives from the vertical field of view.
    if lens_mm >= 70:
        frame_height = 0.7 * height
        target_z = 0.78 * height
    elif lens_mm <= 28:
        frame_height = 3.5 * height
        target_z = 0.5 * height
    else:
        frame_height = 1.6 * height
        target_z = 0.55 * height

    bpy.ops.object.camera_add(location=(0, -5, target_z))
    camera = bpy.context.object
    camera.name = "director_camera"
    camera.data.lens = lens_mm
    bpy.context.scene.camera = camera

    sensor_height = camera.data.sensor_width * (
        bpy.context.scene.render.resolution_y / bpy.context.scene.render.resolution_x
    )
    fov_v = 2 * math.atan(sensor_height / (2 * lens_mm))
    distance = frame_height / (2 * math.tan(fov_v / 2))

    target = bpy.data.objects.new("camera_target", None)
    bpy.context.scene.collection.objects.link(target)
    target.location = (subject.location.x, subject.location.y, target_z)
    # Parent keeping the world transform: imported GLB roots often carry a
    # Y-up→Z-up rotation/scale that would otherwise displace the target.
    bpy.context.view_layer.update()
    target.parent = subject
    target.matrix_parent_inverse = subject.matrix_world.inverted()

    camera["frame_distance"] = distance
    camera["target_z"] = target_z
    camera.location = (0, -distance, target_z + 0.15 * distance)

    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    constraint.target = target
    return camera


def _animate_subject(subject: bpy.types.Object, spec: dict, asset_refs: dict) -> None:
    frame_end = int(spec["duration_seconds"] * spec["fps"])
    action = spec["action"].lower()
    animation_ref = asset_refs.get("animation", {})
    animation_id = animation_ref.get("id")

    # If the imported object already carries NLA tracks (e.g. GLB with embedded actions), reuse them.
    if (subject.animation_data and subject.animation_data.nla_tracks
            and any(t.strips for t in subject.animation_data.nla_tracks)):
        print("  Subject already has NLA tracks — reusing embedded animation.")
        action_name = animation_ref.get("metadata", {}).get("action_name")
        if action_name and _select_nla_animation(subject, action_name, frame_end):
            print(f"  Selected NLA animation: {action_name}")
            return
        # Fallback: unmute every track (a failed selection leaves them muted)
        # and extend all strip frame ends so the embedded animation still plays.
        for track in subject.animation_data.nla_tracks:
            track.mute = False
            for strip in track.strips:
                strip.frame_end = frame_end
        return

    # If a real animation .glb is provided, try to apply it via NLA
    if animation_ref.get("path"):
        applied = _apply_nla_animation(subject, animation_ref["path"], frame_end)
        if applied:
            print(f"  Applied NLA animation from: {animation_ref['path']}")
            return
        print("  NLA animation apply failed, falling back to keyframe animation.")

    # Fallback: simple keyframe-based movement
    start_x = -2.0 if "runs" in action or animation_id == "run_v1" else -1.5
    end_x = 2.0 if "runs" in action or animation_id == "run_v1" else 1.5
    if "stands" in action or animation_id == "idle_v1":
        start_x = end_x = 0

    base_z = subject.location.z
    subject.location = (start_x, 0, base_z)
    subject.keyframe_insert(data_path="location", frame=1)
    subject.rotation_euler = (0, 0, 0)
    subject.keyframe_insert(data_path="rotation_euler", frame=1)

    subject.location = (end_x, 0, base_z)
    subject.rotation_euler = (0, 0, math.radians(180))
    subject.keyframe_insert(data_path="location", frame=frame_end)
    subject.keyframe_insert(data_path="rotation_euler", frame=frame_end)


def _animate_camera(camera: bpy.types.Object, spec: dict) -> None:
    frame_end = int(spec["duration_seconds"] * spec["fps"])
    movement = spec["camera"].get("movement", "orbit").lower()
    distance = float(camera.get("frame_distance", 7.0))
    cam_z = float(camera.get("target_z", 1.0)) + 0.15 * distance

    if movement == "static":
        camera.keyframe_insert(data_path="location", frame=1)
        camera.keyframe_insert(data_path="location", frame=frame_end)
        return
    if movement == "push_in":
        camera.location = (0, -1.5 * distance, cam_z + 0.1 * distance)
        camera.keyframe_insert(data_path="location", frame=1)
        camera.location = (0, -0.85 * distance, cam_z)
        camera.keyframe_insert(data_path="location", frame=frame_end)
        return
    if movement == "dolly":
        camera.location = (-0.6 * distance, -distance, cam_z)
        camera.keyframe_insert(data_path="location", frame=1)
        camera.location = (0.6 * distance, -distance, cam_z)
        camera.keyframe_insert(data_path="location", frame=frame_end)
        return

    # Orbit: smooth arc at constant radius around the subject (-50° → +50°)
    steps = 5
    for i in range(steps):
        t = i / (steps - 1)
        angle = math.radians(-90 - 50 + 100 * t)  # around -Y axis front
        frame = 1 + round(t * (frame_end - 1))
        camera.location = (distance * math.cos(angle), distance * math.sin(angle), cam_z)
        camera.keyframe_insert(data_path="location", frame=frame)


def _select_nla_animation(subject: bpy.types.Object, action_name: str, frame_end: int) -> bool:
    """Mute all NLA tracks except the one whose action matches action_name; loop it to frame_end."""
    if not (subject.animation_data and subject.animation_data.nla_tracks):
        return False
    target = action_name.lower()

    def _matches(strip: bpy.types.NlaStrip) -> bool:
        # GLB exporters decorate action names (e.g. "Walk" → "Walk_Track" or
        # "Walk_Track_Protagonista_Armature"), so match by substring.
        return bool(strip.action) and target in strip.action.name.lower()

    matched_tracks = [t for t in subject.animation_data.nla_tracks if any(_matches(s) for s in t.strips)]
    if not matched_tracks:
        return False
    for track in subject.animation_data.nla_tracks:
        track.mute = track not in matched_tracks
    for track in matched_tracks:
        for strip in track.strips:
            if _matches(strip):
                # Reposicionar al frame 1: los exportadores colocan las strips en
                # offsets arbitrarios (p.ej. Talk en el frame 80) y fuera del rango
                # del render la animación nunca se reproduce.
                cycle = strip.action_frame_end - strip.action_frame_start
                strip.frame_start = 1
                strip.frame_end = frame_end
                if cycle > 0:
                    strip.repeat = math.ceil(frame_end / cycle)
    return True


def _subject_bounds(subject: bpy.types.Object) -> tuple[float, float]:
    """Return (min_z, height) of the subject's world-space mesh bounding box."""
    meshes = [o for o in [subject, *subject.children_recursive] if o.type == "MESH"]
    if not meshes:
        return subject.location.z, 1.7
    zs = [
        (obj.matrix_world @ Vector(corner)).z
        for obj in meshes
        for corner in obj.bound_box
    ]
    return min(zs), max(zs) - min(zs)


def _normalize_subject(subject: bpy.types.Object, *, target_height: float = 1.7) -> None:
    """Scale an imported character to a plausible human height and rest it on the floor."""
    min_z, height = _subject_bounds(subject)
    if height > 0 and not (1.2 <= height <= 2.5):
        factor = target_height / height
        subject.scale = tuple(s * factor for s in subject.scale)
        bpy.context.view_layer.update()
        min_z, height = _subject_bounds(subject)
        print(f"  Normalized subject scale by {factor:.3f} (height {height:.2f}m)")
    if abs(min_z) > 1e-4:
        subject.location.z -= min_z
        bpy.context.view_layer.update()
        print(f"  Grounded subject (was floating at z={min_z:.3f})")


def _subject_height(subject: bpy.types.Object) -> float:
    _, height = _subject_bounds(subject)
    return height if height > 0 else 1.7


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


def _resolve_asset_refs(spec: dict) -> dict:
    refs = {}
    for key, asset_type in [
        ("character", "characters"),
        ("environment", "environments"),
        ("animation", "animations"),
    ]:
        asset_id = spec.get(key)
        if not asset_id:
            continue
        refs[key] = _load_asset_ref(asset_id, asset_type)
    return refs


def _load_asset_ref(asset_id: str, asset_type: str) -> dict:
    manifest_path = ASSETS_ROOT / asset_type / asset_id / "asset.json"
    if not manifest_path.exists():
        return {
            "id": asset_id,
            "type": asset_type.rstrip("s"),
            "source": "missing",
            "manifest": str(manifest_path),
            "resolved": False,
        }
    with manifest_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    raw_path = data.get("path")
    resolved_path: str | None = None
    if raw_path:
        candidate = (manifest_path.parent / raw_path).resolve()
        resolved_path = str(candidate) if candidate.exists() else None
        if not candidate.exists():
            print(f"  WARNING: asset '{asset_id}' path not found: {candidate}")
    return {
        "id": data.get("id", asset_id),
        "type": data.get("type", asset_type.rstrip("s")),
        "name": data.get("name", asset_id),
        "source": data.get("source", "unknown"),
        "path": resolved_path,
        "manifest": str(manifest_path.resolve()),
        "resolved": True,
        "metadata": data.get("metadata", {}),
    }


def _import_glb(path: str, *, label: str = "asset") -> bpy.types.Object | None:
    """Import a .glb file and return its root Empty or first mesh object.

    Returns None if the import fails or produces no objects.
    All imported objects are grouped under a new Empty named after the label.
    """
    before = set(bpy.context.scene.objects)
    try:
        bpy.ops.import_scene.gltf(filepath=path)
    except Exception as exc:  # noqa: BLE001
        print(f"  ERROR importing {label} from '{path}': {exc}")
        return None

    new_objects = [obj for obj in bpy.context.scene.objects if obj not in before]
    if not new_objects:
        print(f"  WARNING: import of {label} produced no objects.")
        return None

    root = _find_root_object(new_objects)
    print(f"  Imported {len(new_objects)} object(s) for {label}, root: {root.name}")
    return root


def _find_root_object(objects: list[bpy.types.Object]) -> bpy.types.Object:
    """Return the topmost object with no parent among the given list."""
    roots = [obj for obj in objects if obj.parent is None or obj.parent not in objects]
    # Prefer armatures as root (for rigged characters)
    armatures = [obj for obj in roots if obj.type == "ARMATURE"]
    if armatures:
        return armatures[0]
    return roots[0] if roots else objects[0]


def _apply_nla_animation(
    subject: bpy.types.Object,
    animation_path: str,
    frame_end: int,
) -> bool:
    """Import a .glb animation and push its actions into the subject via NLA.

    Returns True if at least one action was successfully applied.
    """
    before_actions = set(bpy.data.actions)
    try:
        bpy.ops.import_scene.gltf(filepath=animation_path)
    except Exception as exc:  # noqa: BLE001
        print(f"  ERROR importing animation from '{animation_path}': {exc}")
        return False

    new_actions = [a for a in bpy.data.actions if a not in before_actions]
    if not new_actions:
        print("  No new actions found in animation .glb.")
        return False

    # Remove the imported objects (we only want the actions)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in list(bpy.context.scene.objects):
        if obj.animation_data and obj.animation_data.action in new_actions:
            obj.select_set(True)
    bpy.ops.object.delete()

    # Apply the first new action to the subject via NLA track
    action = new_actions[0]
    anim_data = subject.animation_data_create()
    track = anim_data.nla_tracks.new()
    track.name = f"director_{action.name}"
    strip = track.strips.new(action.name, start=1, action=action)
    strip.action_frame_start = action.frame_range[0]
    strip.action_frame_end = min(action.frame_range[1], frame_end)
    strip.frame_end = frame_end
    return True


def _create_rain_system() -> None:
    """Particle-system rain: emitter plane overhead, elongated streak instances falling."""
    # Instance object: thin vertical streak (hidden from direct view, shown via particles)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(100, 100, 100))
    streak = bpy.context.object
    streak.name = "rain_streak_instance"
    streak.dimensions = (0.015, 0.015, 0.35)
    mat = bpy.data.materials.new("rain_streak_material")
    mat.diffuse_color = (0.55, 0.75, 1.0, 0.6)
    streak.data.materials.append(mat)

    # Emitter plane above scene, hidden from render
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 9))
    emitter = bpy.context.object
    emitter.name = "rain_emitter"
    emitter.hide_render = True

    ps = emitter.modifiers.new("rain_ps", type="PARTICLE_SYSTEM")
    s = ps.particle_system.settings
    s.name = "rain_settings"
    s.type = "EMITTER"
    s.count = 400
    s.frame_start = 1
    s.frame_end = 500
    s.lifetime = 25
    s.lifetime_random = 0.3
    s.emit_from = "FACE"
    s.use_emit_random = True
    s.normal_factor = 0.0
    s.factor_random = 0.4
    s.object_align_factor[2] = -8.0
    s.render_type = "OBJECT"
    s.instance_object = streak
    s.particle_size = 0.8
    s.use_rotation_instance = True


def _create_fog_volume() -> None:
    """Volume scatter cube for atmospheric fog (Eevee volumetrics)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1, 3))
    vol = bpy.context.object
    vol.name = "fog_volume"
    vol.dimensions = (14, 12, 8)

    mat = bpy.data.materials.new("fog_volume_material")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (300, 0)
    scatter = nodes.new("ShaderNodeVolumeScatter")
    scatter.location = (0, 0)
    scatter.inputs["Density"].default_value = 0.08
    scatter.inputs["Color"].default_value = (0.75, 0.82, 0.95, 1.0)
    links.new(scatter.outputs["Volume"], output.inputs["Volume"])
    vol.data.materials.append(mat)

    bpy.context.scene.eevee.use_volumetric_shadows = True


def _create_snow_system() -> None:
    """Particle-system snow: emitter plane overhead, ico-sphere flake instances drifting down."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.04, location=(100, 100, 100))
    flake = bpy.context.object
    flake.name = "snow_flake_instance"
    mat = bpy.data.materials.new("snow_flake_material")
    mat.diffuse_color = (0.95, 0.97, 1.0, 0.9)
    flake.data.materials.append(mat)

    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 7))
    emitter = bpy.context.object
    emitter.name = "snow_emitter"
    emitter.hide_render = True

    ps = emitter.modifiers.new("snow_ps", type="PARTICLE_SYSTEM")
    s = ps.particle_system.settings
    s.name = "snow_settings"
    s.type = "EMITTER"
    s.count = 250
    s.frame_start = 1
    s.frame_end = 500
    s.lifetime = 60
    s.lifetime_random = 0.4
    s.emit_from = "FACE"
    s.use_emit_random = True
    s.normal_factor = 0.0
    s.factor_random = 0.8
    s.object_align_factor[2] = -1.5
    s.render_type = "OBJECT"
    s.instance_object = flake
    s.particle_size = 1.0


def _render_preview_frame(spec: dict, output_dir: Path) -> Path:
    """Render a single mid-shot frame at 25% resolution for quick critic evaluation."""
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

    # Blender appends a zero-padded frame number; rename to a stable path
    numbered = output_dir / f"preview_frame{mid_frame:04d}.png"
    if numbered.exists() and not preview_path.exists():
        numbered.rename(preview_path)
    return preview_path


def _render_control_passes(output_dir: Path, subject: bpy.types.Object) -> dict[str, str]:
    """Render beauty, depth, normal and subject-mask passes via the Blender compositor.

    Uses real view-layer passes (Z, Normal, IndexOB) so a single render call
    produces all four images instead of the previous four material-override renders.
    Pass keys are kept identical to the old proxy implementation so manifests
    and any downstream tooling remain compatible.
    """
    passes_dir = output_dir / "passes"
    passes_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.frame_set(1)
    frame = scene.frame_current

    # Tag subject objects with pass_index = 1 for the IndexOB / ID Mask node
    _mark_subject_for_passes(subject, pass_index=1)

    # Enable real view-layer passes (Z depth, Surface Normal, Object Index)
    _enable_view_layer_passes(scene)

    # Force the depsgraph to propagate pass-enable changes so the compositor
    # Render Layers node exposes the IndexOB socket immediately.
    bpy.context.evaluated_depsgraph_get()

    # Build compositor node tree: Render Layers → one File Output per pass
    _setup_compositor_pass_nodes(scene, passes_dir)

    # One render call — compositor writes all pass files automatically
    original_filepath = scene.render.filepath
    original_format = scene.render.image_settings.file_format
    try:
        scene.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(write_still=False)
    finally:
        scene.render.filepath = original_filepath
        scene.render.image_settings.file_format = original_format
        _clear_compositor(scene)
        _reset_subject_pass_index(subject)

    # Compositor File Output appends the zero-padded frame number
    frame_str = f"{frame:04d}"
    result: dict[str, str] = {
        "beauty":      str(_resolve_pass_file(passes_dir / f"beauty_frame_{frame_str}.png")),
        "depth_proxy": str(_resolve_pass_file(passes_dir / f"depth_proxy_frame_{frame_str}.png")),
        "normal_proxy": str(_resolve_pass_file(passes_dir / f"normal_proxy_frame_{frame_str}.png")),
    }
    mask_candidate = passes_dir / f"subject_mask_frame_{frame_str}.png"
    if mask_candidate.exists():
        result["subject_mask"] = str(mask_candidate)
    return result


def _mark_subject_for_passes(subject: bpy.types.Object, *, pass_index: int) -> None:
    """Assign pass_index to the subject and every mesh skinned to it."""
    subject.pass_index = pass_index
    for child in subject.children_recursive:
        child.pass_index = pass_index
    # Also tag meshes that use this object as an Armature modifier target
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            for mod in obj.modifiers:
                if mod.type == "ARMATURE" and mod.object == subject:
                    obj.pass_index = pass_index
                    break


def _reset_subject_pass_index(subject: bpy.types.Object) -> None:
    """Reset pass_index back to 0 after passes render."""
    subject.pass_index = 0
    for child in subject.children_recursive:
        child.pass_index = 0
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.pass_index != 0:
            obj.pass_index = 0


def _enable_view_layer_passes(scene: bpy.types.Scene) -> None:
    """Enable the Z-depth, Surface Normal and Object Index view layer passes."""
    vl = scene.view_layers[0]
    vl.use_pass_z = True              # real Z depth buffer
    vl.use_pass_normal = True         # surface normal vectors
    vl.use_pass_object_index = True   # IndexOB — used for subject mask
    vl.use_pass_combined = True       # beauty (always on, but explicit)


def _setup_compositor_pass_nodes(scene: bpy.types.Scene, passes_dir: Path) -> None:
    """Build a compositor node tree that writes each pass to a separate PNG file.

    Node layout:
        Render Layers
            Image   → File Output  (beauty_frame_)
            Depth   → Normalize → File Output  (depth_proxy_frame_)
            Normal  → File Output  (normal_proxy_frame_)
            IndexOB → ID Mask (index=1) → File Output  (subject_mask_frame_)

    Blender appends the zero-padded frame number automatically, so slot path
    "beauty_frame_" + frame 1 → "beauty_frame_0001.png".
    """
    scene.use_nodes = True
    tree = scene.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    # ── Source ───────────────────────────────────────────────────────────────
    rl = nodes.new("CompositorNodeRLayers")
    rl.location = (-300, 0)
    # Blender defers pass output registration; removing and re-adding the node
    # forces the node to expose all currently-enabled view-layer pass sockets.
    nodes.remove(rl)
    rl = nodes.new("CompositorNodeRLayers")
    rl.location = (-300, 0)

    # ── Beauty pass ──────────────────────────────────────────────────────────
    beauty_out = _file_output_node(nodes, passes_dir, "beauty_frame_", x=200, y=300)
    links.new(rl.outputs["Image"], beauty_out.inputs[0])

    # ── Composite output (required so Blender doesn't warn about missing viewer)
    composite = nodes.new("CompositorNodeComposite")
    composite.location = (200, 150)
    links.new(rl.outputs["Image"], composite.inputs["Image"])

    # ── Depth pass: normalize raw Z to [0, 1] ────────────────────────────────
    normalize = nodes.new("CompositorNodeNormalize")
    normalize.location = (-50, 0)
    links.new(rl.outputs["Depth"], normalize.inputs[0])
    depth_out = _file_output_node(nodes, passes_dir, "depth_proxy_frame_", x=200, y=0)
    links.new(normalize.outputs[0], depth_out.inputs[0])

    # ── Normal pass ──────────────────────────────────────────────────────────
    normal_out = _file_output_node(nodes, passes_dir, "normal_proxy_frame_", x=200, y=-200)
    links.new(rl.outputs["Normal"], normal_out.inputs[0])

    # ── Subject mask: IndexOB == 1 via ID Mask ────────────────────────────────
    id_mask = nodes.new("CompositorNodeIDMask")
    id_mask.location = (-50, -300)
    id_mask.index = 1
    id_mask.use_antialiasing = True
    mask_out = _file_output_node(nodes, passes_dir, "subject_mask_frame_", x=200, y=-400)
    if "IndexOB" in rl.outputs:
        links.new(rl.outputs["IndexOB"], id_mask.inputs[0])
        links.new(id_mask.outputs[0], mask_out.inputs[0])
    else:
        # Fallback: flat white RGBA image (full frame treated as subject)
        # CompositorNodeRGB broadcasts a constant colour as a frame-sized image.
        rgb_white = nodes.new("CompositorNodeRGB")
        rgb_white.outputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
        rgb_white.location = (-50, -500)
        links.new(rgb_white.outputs[0], mask_out.inputs[0])


def _file_output_node(
    nodes: bpy.types.NodeTree,
    base_dir: Path,
    slot_prefix: str,
    *,
    x: float,
    y: float,
) -> bpy.types.CompositorNodeOutputFile:
    """Create a compositor File Output node with a single PNG slot."""
    node = nodes.new("CompositorNodeOutputFile")
    node.location = (x, y)
    node.base_path = str(base_dir)
    node.format.file_format = "PNG"
    node.format.color_mode = "RGB"
    node.format.color_depth = "8"
    node.file_slots[0].path = slot_prefix
    return node


def _clear_compositor(scene: bpy.types.Scene) -> None:
    """Remove compositor nodes and disable use_nodes to avoid affecting other renders."""
    if scene.use_nodes and scene.node_tree:
        scene.node_tree.nodes.clear()
    scene.use_nodes = False


def _resolve_pass_file(path: Path) -> Path:
    """Return the path if it exists; otherwise fall back to the path without extension."""
    return path if path.exists() else path.with_suffix("")




def _is_claymation(spec: dict) -> bool:
    style = spec.get("style", "").lower()
    return any(word in style for word in ("clay", "plastilina", "claymation", "stop motion", "stop-motion"))


def _apply_claymation_style() -> None:
    """Re-shade every mesh with a clay look: matte rough surface with a
    fingerprint-like noise bump, preserving each material's base color.
    Animation cadence is left to the spec (use fps 12 for stop-motion feel)."""
    print("  Applying claymation style override.")
    image_color_cache: dict[str, tuple[float, float, float, float] | None] = {}
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        # Las pantallas conservan su gráfico emisivo (un TV no es de arcilla)
        if obj.name.startswith("tv_screen"):
            continue
        for slot_index in range(max(1, len(obj.material_slots))):
            base_color = (0.8, 0.5, 0.35, 1.0)
            old = obj.material_slots[slot_index].material if obj.material_slots else None
            if old is not None:
                if old.use_nodes:
                    bsdf = old.node_tree.nodes.get("Principled BSDF")
                    if bsdf is not None:
                        base_input = bsdf.inputs["Base Color"]
                        # Textured materials keep their color in the image, not
                        # the socket default — use the texture's average color.
                        sampled = _texture_average_color(base_input, image_color_cache)
                        base_color = sampled if sampled else tuple(base_input.default_value)
                else:
                    base_color = tuple(old.diffuse_color)
            clay = _clay_material(f"clay_{obj.name}_{slot_index}", base_color)
            if obj.material_slots:
                obj.material_slots[slot_index].material = clay
            else:
                obj.data.materials.append(clay)


def _texture_average_color(
    base_input: bpy.types.NodeSocket,
    cache: dict[str, tuple[float, float, float, float] | None],
) -> tuple[float, float, float, float] | None:
    """If the Base Color socket is fed (directly or through mix/factor nodes)
    by an image texture, return the image's alpha-weighted average color
    (subsampled for speed)."""
    # Breadth-first walk upstream: glTF importers wrap the base texture in
    # Mix/Multiply nodes, so the image is rarely linked directly.
    queue = [link.from_node for link in base_input.links]
    seen: set[str] = set()
    image = None
    while queue:
        node = queue.pop(0)
        if node.name in seen or len(seen) > 20:
            continue
        seen.add(node.name)
        if node.type == "TEX_IMAGE" and node.image is not None:
            image = node.image
            break
        for socket in node.inputs:
            queue.extend(link.from_node for link in socket.links)
    if image is not None:
        if image.name in cache:
            return cache[image.name]
        pixel_count = len(image.pixels) // 4
        if pixel_count == 0:
            cache[image.name] = None
            return None
        pixels = image.pixels[:]
        stride = max(1, pixel_count // 4096)
        r = g = b = weight = 0.0
        for i in range(0, pixel_count, stride):
            j = i * 4
            alpha = pixels[j + 3]
            if alpha < 0.1:
                continue
            r += pixels[j] * alpha
            g += pixels[j + 1] * alpha
            b += pixels[j + 2] * alpha
            weight += alpha
        color = (r / weight, g / weight, b / weight, 1.0) if weight > 0 else None
        cache[image.name] = color
        return color
    return None


def _clay_material(name: str, color: tuple[float, ...]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = 0.85
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.2

    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 35.0
    noise.inputs["Detail"].default_value = 4.0
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return material


def _material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    return material


def _image_emission_material(name: str, image_path: str, strength: float) -> bpy.types.Material:
    """Material emisivo con textura de imagen (pantallas del estudio)."""
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(image_path)
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = strength
    bsdf.inputs["Roughness"].default_value = 0.4
    return material


def _emission_material(name: str, color: tuple[float, float, float, float], strength: float) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Emission Color"].default_value = color
    bsdf.inputs["Emission Strength"].default_value = strength
    return material


def _write_manifest(
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


def _look_at(obj: bpy.types.Object, target) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")[:40]


if __name__ == "__main__":
    raise SystemExit(main())
