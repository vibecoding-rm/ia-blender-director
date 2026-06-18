from __future__ import annotations
import bpy
import math

def animate_subject(subject: bpy.types.Object, spec: dict, asset_refs: dict) -> None:
    frame_end = int(spec["duration_seconds"] * spec["fps"])
    action = spec["action"].lower()
    animation_ref = asset_refs.get("animation", {})
    animation_id = animation_ref.get("id")

    if (subject.animation_data and subject.animation_data.nla_tracks
            and any(t.strips for t in subject.animation_data.nla_tracks)):
        print("  Subject already has NLA tracks — reusing embedded animation.")
        action_name = animation_ref.get("metadata", {}).get("action_name")
        if action_name and select_nla_animation(subject, action_name, frame_end):
            print(f"  Selected NLA animation: {action_name}")
            return
        for track in subject.animation_data.nla_tracks:
            track.mute = False
            for strip in track.strips:
                strip.frame_end = frame_end
        return

    if animation_ref.get("path"):
        applied = apply_nla_animation(subject, animation_ref["path"], frame_end)
        if applied:
            print(f"  Applied NLA animation from: {animation_ref['path']}")
            return
        print("  NLA animation apply failed, falling back to keyframe animation.")

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
    apply_easing(subject)

def animate_camera(camera: bpy.types.Object, spec: dict) -> None:
    frame_end = int(spec["duration_seconds"] * spec["fps"])
    movement = spec["camera"].get("movement", "orbit").lower()
    distance = float(camera.get("frame_distance", 7.0))
    cam_z = float(camera.get("target_z", 1.0)) + 0.15 * distance

    if movement == "static":
        camera.keyframe_insert(data_path="location", frame=1)
        camera.keyframe_insert(data_path="location", frame=frame_end)
        apply_easing(camera)
        return
    if movement == "push_in":
        camera.location = (0, -1.5 * distance, cam_z + 0.1 * distance)
        camera.keyframe_insert(data_path="location", frame=1)
        camera.location = (0, -0.85 * distance, cam_z)
        camera.keyframe_insert(data_path="location", frame=frame_end)
        apply_easing(camera)
        return
    if movement == "dolly":
        camera.location = (-0.6 * distance, -distance, cam_z)
        camera.keyframe_insert(data_path="location", frame=1)
        camera.location = (0.6 * distance, -distance, cam_z)
        camera.keyframe_insert(data_path="location", frame=frame_end)
        apply_easing(camera)
        return

    steps = 5
    for i in range(steps):
        t = i / (steps - 1)
        angle = math.radians(-90 - 50 + 100 * t)
        frame = 1 + round(t * (frame_end - 1))
        camera.location = (distance * math.cos(angle), distance * math.sin(angle), cam_z)
        camera.keyframe_insert(data_path="location", frame=frame)
    apply_easing(camera)

def select_nla_animation(subject: bpy.types.Object, action_name: str, frame_end: int) -> bool:
    if not (subject.animation_data and subject.animation_data.nla_tracks):
        return False
    target = action_name.lower()

    def matches(strip: bpy.types.NlaStrip) -> bool:
        return bool(strip.action) and target in strip.action.name.lower()

    matched_tracks = [t for t in subject.animation_data.nla_tracks if any(matches(s) for s in t.strips)]
    if not matched_tracks:
        return False
    for track in subject.animation_data.nla_tracks:
        track.mute = track not in matched_tracks
    for track in matched_tracks:
        for strip in track.strips:
            if matches(strip):
                cycle = strip.action_frame_end - strip.action_frame_start
                strip.frame_start = 1
                strip.frame_end = frame_end
                if cycle > 0:
                    strip.repeat = math.ceil(frame_end / cycle)
    return True

def apply_nla_animation(
    subject: bpy.types.Object,
    animation_path: str,
    frame_end: int,
) -> bool:
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

    bpy.ops.object.select_all(action="DESELECT")
    for obj in list(bpy.context.scene.objects):
        if obj.animation_data and obj.animation_data.action in new_actions:
            obj.select_set(True)
    bpy.ops.object.delete()

    action = new_actions[0]
    anim_data = subject.animation_data_create()
    track = anim_data.nla_tracks.new()
    track.name = f"director_{action.name}"
    strip = track.strips.new(action.name, start=1, action=action)
    strip.action_frame_start = action.frame_range[0]
    strip.action_frame_end = min(action.frame_range[1], frame_end)
    strip.frame_end = frame_end
    return True

def apply_easing(obj: bpy.types.Object) -> None:
    if not obj.animation_data or not obj.animation_data.action:
        return
    for fcurve in obj.animation_data.action.fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = "BEZIER"
            keyframe.handle_left_type = "AUTO_CLAMPED"
            keyframe.handle_right_type = "AUTO_CLAMPED"
