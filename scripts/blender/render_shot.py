from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
ASSETS_ROOT = ROOT / "assets"


def main() -> int:
    shot_path, output_dir, profile = _parse_args(sys.argv)
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

    if spec.get("weather") == "rain":
        _create_rain_proxy()
    if spec.get("weather") in {"fog", "snow"}:
        _create_atmosphere_proxy(spec)

    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / "latest_preview.blend"))
    bpy.ops.render.render(animation=True)
    passes = _render_control_passes(output_dir, subject)
    _write_manifest(spec, shot_path, output_dir, profile, passes, asset_refs)
    return 0


def _parse_args(argv: list[str]) -> tuple[Path, Path, str]:
    if "--" not in argv:
        raise SystemExit("Usage: blender --background --python render_shot.py -- shot.json output_dir [preview|final]")
    script_args = argv[argv.index("--") + 1 :]
    if len(script_args) not in {2, 3}:
        raise SystemExit("Usage: blender --background --python render_shot.py -- shot.json output_dir [preview|final]")
    profile = script_args[2] if len(script_args) == 3 else "preview"
    if profile not in {"preview", "final"}:
        raise SystemExit("profile must be 'preview' or 'final'")
    return Path(script_args[0]).resolve(), Path(script_args[1]).resolve(), profile


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


def _create_subject(spec: dict, asset_refs: dict) -> bpy.types.Object:
    character = asset_refs.get("character")
    if character:
        print(f"Using character asset: {character['id']} ({character['source']})")
        if character.get("path"):
            imported = _import_glb(character["path"], label="character")
            if imported is not None:
                imported.name = f"subject_{_slug(spec['subject'])}"
                imported.location = (0, 0, 0)
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


def _animate_subject(subject: bpy.types.Object, spec: dict, asset_refs: dict) -> None:
    frame_end = int(spec["duration_seconds"] * spec["fps"])
    action = spec["action"].lower()
    animation_ref = asset_refs.get("animation", {})
    animation_id = animation_ref.get("id")

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
    return {
        "beauty":       str(_resolve_pass_file(passes_dir / f"beauty_frame_{frame_str}.png")),
        "subject_mask": str(_resolve_pass_file(passes_dir / f"subject_mask_frame_{frame_str}.png")),
        "depth_proxy":  str(_resolve_pass_file(passes_dir / f"depth_proxy_frame_{frame_str}.png")),
        "normal_proxy": str(_resolve_pass_file(passes_dir / f"normal_proxy_frame_{frame_str}.png")),
    }


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
    links.new(rl.outputs["IndexOB"], id_mask.inputs[0])
    mask_out = _file_output_node(nodes, passes_dir, "subject_mask_frame_", x=200, y=-400)
    links.new(id_mask.outputs[0], mask_out.inputs[0])


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
