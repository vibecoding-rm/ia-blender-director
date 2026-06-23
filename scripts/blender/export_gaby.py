"""
Blender headless script - builds "Gaby Filo, la Lechuza de Teleprompter":
an owl pundit with huge amber eyes, academic blazer, hard eyelashes and a
teleprompter gag. Rigged GLB with Idle, Talk and Walk NLA.

The lower beak is the `Beak` bone for lip-sync.

Usage:
    blender --background --python scripts/blender/export_gaby.py

Output:
    assets/characters/gaby_v1/gaby_v1.glb
"""

import math
from pathlib import Path

import bpy
import mathutils

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "assets" / "characters" / "gaby_v1" / "gaby_v1.glb"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

_BONES: list[tuple[str, tuple, tuple, str | None]] = [
    ("Root", (0, 0, 0), (0, 0, 0.1), None),
    ("Body", (0, 0, 0.34), (0, 0, 0.88), "Root"),
    ("Head", (0, 0, 0.90), (0, 0, 1.24), "Body"),
    ("Beak", (0, -0.14, 1.02), (0, -0.30, 0.99), "Head"),
    ("Wing.L", (-0.28, 0, 0.74), (-0.50, -0.02, 0.52), "Body"),
    ("Wing.R", (0.28, 0, 0.74), (0.50, -0.02, 0.52), "Body"),
    ("Tail", (0, 0.20, 0.48), (0, 0.40, 0.28), "Body"),
    ("Leg.L", (-0.10, 0, 0.34), (-0.10, -0.02, 0.04), "Root"),
    ("Leg.R", (0.10, 0, 0.34), (0.10, -0.02, 0.04), "Root"),
    ("Eye.L", (-0.10, -0.14, 1.07), (-0.10, -0.14, 1.14), "Head"),
    ("Eye.R", (0.10, -0.14, 1.07), (0.10, -0.14, 1.14), "Head"),
]


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.actions, bpy.data.armatures, bpy.data.meshes, bpy.data.materials):
        for block in list(collection):
            collection.remove(block)


def _solid_mat(name: str, rgba: tuple) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.82
    return mat


def build_armature() -> bpy.types.Object:
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm_obj = bpy.context.object
    arm_obj.name = "Gaby_Armature"
    arm_obj.data.name = "Gaby_Rig"

    edit_bones = arm_obj.data.edit_bones
    for bone in list(edit_bones):
        edit_bones.remove(bone)

    created: dict[str, bpy.types.EditBone] = {}
    for name, head, tail, parent_name in _BONES:
        eb = edit_bones.new(name)
        eb.head = mathutils.Vector(head)
        eb.tail = mathutils.Vector(tail)
        if parent_name:
            eb.parent = created[parent_name]
            eb.use_connect = False
        created[name] = eb

    bpy.ops.object.mode_set(mode="POSE")
    for pose_bone in arm_obj.pose.bones:
        pose_bone.rotation_mode = "XYZ"
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj


def build_mesh_parts(arm_obj: bpy.types.Object) -> list[bpy.types.Object]:
    feather = _solid_mat("FeatherGreyBeige", (0.60, 0.55, 0.45, 1.0))
    feather_light = _solid_mat("FeatherLight", (0.76, 0.70, 0.58, 1.0))
    blazer = _solid_mat("AcademicBlazer", (0.12, 0.14, 0.18, 1.0))
    blouse = _solid_mat("Blouse", (0.92, 0.88, 0.78, 1.0))
    amber = _solid_mat("AmberEye", (0.88, 0.65, 0.15, 1.0))
    eye_black = _solid_mat("EyeBlack", (0.03, 0.03, 0.035, 1.0))
    beak_mat = _solid_mat("BeakMat", (0.84, 0.55, 0.16, 1.0))
    leg_mat = _solid_mat("LegMat", (0.72, 0.50, 0.18, 1.0))
    tele = _solid_mat("TeleprompterGlass", (0.03, 0.08, 0.10, 1.0))
    tele_frame = _solid_mat("TeleprompterFrame", (0.02, 0.02, 0.025, 1.0))
    text_green = _solid_mat("PromptText", (0.20, 0.95, 0.50, 1.0))

    parts: list[tuple[bpy.types.Object, str]] = []

    def _sphere(name, loc, radius, mat, bone, *, scale=None, segs=18, rings=12):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, radius=radius, location=loc)
        obj = bpy.context.object
        obj.name = name
        if scale:
            obj.scale = scale
            bpy.ops.object.transform_apply(scale=True)
        obj.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        parts.append((obj, bone))
        return obj

    def _cone(name, loc, radius, depth, mat, bone, *, rot=None, verts=14):
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=radius, radius2=0.01, depth=depth, location=loc)
        obj = bpy.context.object
        obj.name = name
        if rot:
            obj.rotation_euler = rot
            bpy.ops.object.transform_apply(rotation=True)
        obj.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        parts.append((obj, bone))
        return obj

    def _cyl(name, loc, radius, depth, mat, bone, *, rot=None, verts=12):
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc)
        obj = bpy.context.object
        obj.name = name
        if rot:
            obj.rotation_euler = rot
            bpy.ops.object.transform_apply(rotation=True)
        obj.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        parts.append((obj, bone))
        return obj

    def _cube(name, loc, dims, mat, bone, *, rot=None):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        obj = bpy.context.object
        obj.name = name
        obj.dimensions = dims
        if rot:
            obj.rotation_euler = rot
        bpy.ops.object.transform_apply(scale=True, rotation=bool(rot))
        obj.data.materials.append(mat)
        parts.append((obj, bone))
        return obj

    # Body: owl torso inside a severe academic blazer.
    _sphere("Mesh_Body", (0, 0, 0.60), 0.30, blazer, "Body", scale=(1.0, 0.88, 1.28))
    _sphere("Mesh_Blouse", (0, -0.16, 0.60), 0.19, blouse, "Body", scale=(0.72, 0.50, 1.10))
    _cube("Mesh_Lapel_L", (-0.12, -0.22, 0.72), (0.12, 0.045, 0.28), blazer, "Body", rot=(0, 0, math.radians(-14)))
    _cube("Mesh_Lapel_R", (0.12, -0.22, 0.72), (0.12, 0.045, 0.28), blazer, "Body", rot=(0, 0, math.radians(14)))

    # Round owl head with facial disk.
    _sphere("Mesh_Head", (0, -0.01, 1.03), 0.23, feather, "Head", scale=(1.05, 0.95, 1.0))
    _sphere("Mesh_FaceDisk", (0, -0.13, 1.04), 0.19, feather_light, "Head", scale=(1.15, 0.34, 0.95))
    for side, sign in (("L", -1), ("R", 1)):
        _cone(f"Mesh_EarTuft_{side}", (sign * 0.11, 0.01, 1.23), 0.055, 0.16, feather, "Head",
              rot=(math.radians(-18), 0, math.radians(sign * 22)))

    # Huge amber eyes with hard eyelashes.
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Eye_{side}", (sign * 0.10, -0.15, 1.07), 0.075, amber, f"Eye.{side}", segs=16, rings=10)
        _sphere(f"Mesh_Pupil_{side}", (sign * 0.10, -0.205, 1.07), 0.030, eye_black, f"Eye.{side}", segs=10, rings=6)
        for i, z in enumerate([1.12, 1.15, 1.09]):
            _cube(f"Mesh_Lash_{side}_{i}", (sign * (0.08 + i * 0.025), -0.205, z), (0.008, 0.025, 0.07),
                  eye_black, f"Eye.{side}", rot=(0, 0, math.radians(sign * (18 + i * 10))))

    # Beak: upper fixed, lower animated.
    _cone("Mesh_BeakUpper", (0, -0.23, 1.03), 0.052, 0.14, beak_mat, "Head", rot=(math.radians(-90), 0, 0))
    _cone("Mesh_BeakLower", (0, -0.21, 0.99), 0.040, 0.10, beak_mat, "Beak", rot=(math.radians(-96), 0, 0))

    # Wings as blazer sleeves.
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Wing_{side}", (sign * 0.31, 0.00, 0.63), 0.17, blazer, f"Wing.{side}",
                scale=(0.42, 0.70, 1.15))
        _sphere(f"Mesh_WingTip_{side}", (sign * 0.42, -0.02, 0.43), 0.06, feather, f"Wing.{side}", segs=10, rings=8)

    # Tail and feet.
    for i, x in enumerate([-0.08, 0.0, 0.08]):
        _sphere(f"Mesh_TailFeather_{i}", (x, 0.30, 0.34), 0.12, feather, "Tail", scale=(0.42, 1.35, 0.38))
    for side, sign in (("L", -1), ("R", 1)):
        _cyl(f"Mesh_Leg_{side}", (sign * 0.10, -0.01, 0.18), 0.026, 0.28, leg_mat, f"Leg.{side}", verts=8)
        _sphere(f"Mesh_Foot_{side}", (sign * 0.10, -0.07, 0.035), 0.055, leg_mat, f"Leg.{side}",
                scale=(1.2, 1.7, 0.45), segs=10, rings=6)

    # Teleprompter in front, attached to body so it travels with the character.
    _cube("Mesh_TeleprompterFrame", (0, -0.52, 0.83), (0.46, 0.035, 0.25), tele_frame, "Body",
          rot=(math.radians(-8), 0, 0))
    _cube("Mesh_TeleprompterGlass", (0, -0.545, 0.84), (0.40, 0.012, 0.19), tele, "Body",
          rot=(math.radians(-8), 0, 0))
    for i, z in enumerate([0.89, 0.84, 0.79]):
        _cube(f"Mesh_PromptLine_{i}", (0, -0.555, z), (0.30 - i * 0.04, 0.006, 0.012), text_green, "Body",
              rot=(math.radians(-8), 0, 0))

    objs: list[bpy.types.Object] = []
    for obj, bone in parts:
        obj.parent = arm_obj
        group = obj.vertex_groups.new(name=bone)
        group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
        modifier = obj.modifiers.new("Armature", "ARMATURE")
        modifier.object = arm_obj
        objs.append(obj)
    return objs


def _fcurve(action: bpy.types.Action, data_path: str, index: int) -> bpy.types.FCurve:
    return action.fcurves.new(data_path=data_path, index=index, action_group="Keys")


def _add_keyframes(fc: bpy.types.FCurve, keys: list[tuple[float, float]], interp: str = "BEZIER") -> None:
    fc.keyframe_points.add(len(keys))
    for i, (frame, val) in enumerate(keys):
        fc.keyframe_points[i].co = (frame, val)
        fc.keyframe_points[i].interpolation = interp


def _add_blinks(action: bpy.types.Action, blink_frames: list[int]) -> None:
    for side in ("L", "R"):
        keys: list[tuple[float, float]] = [(1, 1.0)]
        for frame in blink_frames:
            keys += [(frame - 2, 1.0), (frame, 0.08), (frame + 2, 1.0)]
        fc = _fcurve(action, f'pose.bones["Eye.{side}"].scale', 1)
        _add_keyframes(fc, keys)


def add_idle_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    action = bpy.data.actions.new(name="Idle")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Body"].location', 2)
    _add_keyframes(fc, [(1, 0), (22, 0.012), (44, 0), (66, 0.010), (84, 0)])
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 2)
    _add_keyframes(fc, [(1, 0), (26, math.radians(7)), (58, math.radians(-5)), (84, 0)])
    fc = _fcurve(action, 'pose.bones["Wing.L"].rotation_euler', 1)
    _add_keyframes(fc, [(1, 0), (42, math.radians(-8)), (84, 0)])
    _add_blinks(action, [18, 62])
    return action


def add_talk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    action = bpy.data.actions.new(name="Talk")
    arm_obj.animation_data.action = action

    beak_keys: list[tuple[float, float]] = []
    for cycle in range(4):
        start = 1 + cycle * 12
        beak_keys += [(start, 0.0), (start + 4, math.radians(28)), (start + 9, math.radians(5))]
    beak_keys.append((48, 0.0))
    fc = _fcurve(action, 'pose.bones["Beak"].rotation_euler', 0)
    _add_keyframes(fc, beak_keys)

    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (14, math.radians(4)), (26, math.radians(-3)), (38, math.radians(4)), (48, 0)])
    fc = _fcurve(action, 'pose.bones["Wing.R"].rotation_euler', 1)
    _add_keyframes(fc, [(1, 0), (15, math.radians(26)), (32, math.radians(18)), (48, 0)], interp="LINEAR")
    _add_blinks(action, [12, 36])
    return action


def add_walk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    action = bpy.data.actions.new(name="Walk")
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Root"].location', 1)
    _add_keyframes(fc, [(1, 0), (32, 0.35)], interp="LINEAR")
    fc = _fcurve(action, 'pose.bones["Body"].rotation_euler', 2)
    _add_keyframes(fc, [(1, math.radians(-4)), (16, math.radians(4)), (32, math.radians(-4))])
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 2)
    _add_keyframes(fc, [(1, math.radians(5)), (16, math.radians(-5)), (32, math.radians(5))])
    return action


def push_action_to_nla(arm_obj: bpy.types.Object, action: bpy.types.Action) -> None:
    track = arm_obj.animation_data.nla_tracks.new()
    track.name = f"{action.name}_Track"
    strip = track.strips.new(name=action.name, start=1, action=action)
    strip.repeat = 1


def export_glb(arm_obj: bpy.types.Object, mesh_parts: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    for part in mesh_parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj

    bpy.ops.export_scene.gltf(
        filepath=str(OUT_PATH),
        use_selection=True,
        export_format="GLB",
        export_animations=True,
        export_nla_strips=True,
        export_skins=True,
        export_apply=False,
    )
    print(f"Exported: {OUT_PATH}")


def main() -> None:
    clear_scene()
    arm_obj = build_armature()
    mesh_parts = build_mesh_parts(arm_obj)

    for builder in (add_idle_action, add_talk_action, add_walk_action):
        push_action_to_nla(arm_obj, builder(arm_obj))

    arm_obj.animation_data.action = None
    export_glb(arm_obj, mesh_parts)
    print("Done.")


if __name__ == "__main__":
    main()
