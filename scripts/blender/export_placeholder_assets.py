"""
Blender headless script — builds a rigged humanoid proxy GLB with embedded
Walk, Idle, and Run NLA animations.

Usage:
    blender --background --python scripts/blender/export_placeholder_assets.py

Output:
    assets/characters/protagonista_v1/protagonista_v1.glb
"""

import math
from pathlib import Path

import bpy
import mathutils

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "assets" / "characters" / "protagonista_v1" / "protagonista_v1.glb"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

_BONES: list[tuple[str, tuple, tuple, str | None]] = [
    ("Root",       (0, 0, 0),        (0, 0, 0.1),       None),
    ("Hips",       (0, 0, 0.9),      (0, 0, 1.0),       "Root"),
    ("Spine",      (0, 0, 1.0),      (0, 0, 1.25),      "Hips"),
    ("Chest",      (0, 0, 1.25),     (0, 0, 1.50),      "Spine"),
    ("Neck",       (0, 0, 1.50),     (0, 0, 1.58),      "Chest"),
    ("Head",       (0, 0, 1.58),     (0, 0, 1.80),      "Neck"),
    ("UpperArm.L", (-0.22, 0, 1.45), (-0.45, 0, 1.45),  "Chest"),
    ("LowerArm.L", (-0.45, 0, 1.45), (-0.65, 0, 1.45),  "UpperArm.L"),
    ("Hand.L",     (-0.65, 0, 1.45), (-0.74, 0, 1.45),  "LowerArm.L"),
    ("UpperArm.R", (0.22, 0, 1.45),  (0.45, 0, 1.45),   "Chest"),
    ("LowerArm.R", (0.45, 0, 1.45),  (0.65, 0, 1.45),   "UpperArm.R"),
    ("Hand.R",     (0.65, 0, 1.45),  (0.74, 0, 1.45),   "UpperArm.R"),
    ("Thigh.L",    (-0.11, 0, 0.90), (-0.11, 0, 0.52),  "Hips"),
    ("Shin.L",     (-0.11, 0, 0.52), (-0.11, 0, 0.12),  "Thigh.L"),
    ("Foot.L",     (-0.11, 0, 0.12), (-0.11, 0.16, 0),  "Shin.L"),
    ("Thigh.R",    (0.11, 0, 0.90),  (0.11, 0, 0.52),   "Hips"),
    ("Shin.R",     (0.11, 0, 0.52),  (0.11, 0, 0.12),   "Thigh.R"),
    ("Foot.R",     (0.11, 0, 0.12),  (0.11, 0.16, 0),   "Shin.R"),
]


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    for armature in list(bpy.data.armatures):
        bpy.data.armatures.remove(armature)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)


def _solid_mat(name: str, rgba: tuple) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.6
    return mat


def build_armature() -> bpy.types.Object:
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm_obj = bpy.context.object
    arm_obj.name = "Protagonista_Armature"
    arm_obj.data.name = "Protagonista_Rig"

    edit_bones = arm_obj.data.edit_bones
    for b in list(edit_bones):
        edit_bones.remove(b)

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
    """Create multi-part humanoid mesh; each body part is a separate object."""
    skin  = _solid_mat("Skin",  (0.86, 0.64, 0.50, 1.0))
    suit  = _solid_mat("Suit",  (0.12, 0.22, 0.62, 1.0))
    pants = _solid_mat("Pants", (0.08, 0.08, 0.14, 1.0))
    shoes = _solid_mat("Shoes", (0.06, 0.05, 0.04, 1.0))

    parts: list[bpy.types.Object] = []

    def _cube(name: str, loc: tuple, dims: tuple, mat: bpy.types.Material) -> bpy.types.Object:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        obj = bpy.context.object
        obj.name = name
        obj.dimensions = dims
        bpy.ops.object.transform_apply(scale=True)
        obj.data.materials.append(mat)
        parts.append(obj)
        return obj

    def _cyl(name: str, loc: tuple, radius: float, depth: float, mat: bpy.types.Material,
             *, horizontal: bool = False) -> bpy.types.Object:
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=radius, depth=depth, location=loc)
        obj = bpy.context.object
        obj.name = name
        if horizontal:
            obj.rotation_euler = (0.0, math.pi / 2, 0.0)
            bpy.ops.object.transform_apply(rotation=True)
        obj.data.materials.append(mat)
        parts.append(obj)
        return obj

    def _sphere(name: str, loc: tuple, radius: float, mat: bpy.types.Material,
                segs: int = 12, rings: int = 8) -> bpy.types.Object:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings,
                                              radius=radius, location=loc)
        obj = bpy.context.object
        obj.name = name
        obj.data.materials.append(mat)
        parts.append(obj)
        return obj

    # ── Head & neck ──────────────────────────────────────────────────────────
    _sphere("Mesh_Head", (0, 0, 1.68), 0.145, skin, segs=14, rings=10)
    _cyl("Mesh_Neck", (0, 0, 1.56), 0.055, 0.10, skin)

    # ── Torso ────────────────────────────────────────────────────────────────
    _cube("Mesh_Torso", (0, 0, 1.25), (0.54, 0.28, 0.50), suit)
    _cube("Mesh_Hips",  (0, 0, 0.95), (0.50, 0.26, 0.24), pants)

    # ── Arms (horizontal cylinders along X) ──────────────────────────────────
    for side, sign in (("L", -1), ("R", 1)):
        _cyl(f"Mesh_UpperArm_{side}", (sign * 0.34, 0, 1.44), 0.065, 0.24, suit,  horizontal=True)
        _cyl(f"Mesh_LowerArm_{side}", (sign * 0.56, 0, 1.44), 0.055, 0.22, skin, horizontal=True)
        _sphere(f"Mesh_Hand_{side}",  (sign * 0.71, 0, 1.43), 0.065, skin, segs=8, rings=6)

    # ── Legs ─────────────────────────────────────────────────────────────────
    for side, sign in (("L", -1), ("R", 1)):
        _cyl(f"Mesh_Thigh_{side}", (sign * 0.115, 0, 0.72), 0.090, 0.38, pants)
        _cyl(f"Mesh_Shin_{side}",  (sign * 0.115, 0, 0.32), 0.075, 0.38, pants)
        _cube(f"Mesh_Foot_{side}", (sign * 0.115, 0.05, 0.05), (0.12, 0.22, 0.09), shoes)

    # ── Parent all parts to armature with auto weights ───────────────────────
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")

    return parts


def _fcurve(action: bpy.types.Action, data_path: str, index: int) -> bpy.types.FCurve:
    return action.fcurves.new(data_path=data_path, index=index, action_group="Keys")


def _add_keyframes(fc: bpy.types.FCurve, keys: list[tuple[float, float]], interp: str = "BEZIER") -> None:
    fc.keyframe_points.add(len(keys))
    for i, (frame, val) in enumerate(keys):
        fc.keyframe_points[i].co = (frame, val)
        fc.keyframe_points[i].interpolation = interp


def add_walk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    action = bpy.data.actions.new(name="Walk")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Root"].location', 1)
    _add_keyframes(fc, [(1, 0.0), (25, 1.0)], "LINEAR")

    fc = _fcurve(action, 'pose.bones["Hips"].location', 2)
    _add_keyframes(fc, [(1, 0), (7, 0.04), (13, 0), (19, 0.04), (25, 0)])

    fc = _fcurve(action, 'pose.bones["Thigh.L"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(25)), (13, math.radians(-25)), (25, math.radians(25))])

    fc = _fcurve(action, 'pose.bones["Thigh.R"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(-25)), (13, math.radians(25)), (25, math.radians(-25))])

    fc = _fcurve(action, 'pose.bones["Shin.L"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(-5)), (7, math.radians(-20)), (13, math.radians(-5)), (19, math.radians(-20)), (25, math.radians(-5))])

    fc = _fcurve(action, 'pose.bones["Shin.R"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(-20)), (7, math.radians(-5)), (13, math.radians(-20)), (19, math.radians(-5)), (25, math.radians(-20))])

    fc = _fcurve(action, 'pose.bones["UpperArm.L"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(-20)), (13, math.radians(20)), (25, math.radians(-20))])

    fc = _fcurve(action, 'pose.bones["UpperArm.R"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(20)), (13, math.radians(-20)), (25, math.radians(20))])

    fc = _fcurve(action, 'pose.bones["Spine"].rotation_euler', 2)
    _add_keyframes(fc, [(1, math.radians(-3)), (7, math.radians(3)), (13, math.radians(-3)), (19, math.radians(3)), (25, math.radians(-3))])

    return action


def add_idle_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    action = bpy.data.actions.new(name="Idle")
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Chest"].location', 2)
    _add_keyframes(fc, [(1, 0), (15, 0.02), (30, 0), (45, -0.005), (60, 0)])

    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (30, math.radians(2)), (60, 0)])

    return action


def add_run_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    action = bpy.data.actions.new(name="Run")
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Root"].location', 1)
    _add_keyframes(fc, [(1, 0.0), (13, 2.0)], "LINEAR")

    fc = _fcurve(action, 'pose.bones["Hips"].location', 2)
    _add_keyframes(fc, [(1, 0), (4, 0.07), (7, 0), (10, 0.07), (13, 0)])

    fc = _fcurve(action, 'pose.bones["Thigh.L"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(45)), (7, math.radians(-45)), (13, math.radians(45))])

    fc = _fcurve(action, 'pose.bones["Thigh.R"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(-45)), (7, math.radians(45)), (13, math.radians(-45))])

    fc = _fcurve(action, 'pose.bones["Shin.L"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(-5)), (4, math.radians(-40)), (7, math.radians(-5)), (10, math.radians(-40)), (13, math.radians(-5))])

    fc = _fcurve(action, 'pose.bones["Shin.R"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(-40)), (4, math.radians(-5)), (7, math.radians(-40)), (10, math.radians(-5)), (13, math.radians(-40))])

    fc = _fcurve(action, 'pose.bones["UpperArm.L"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(-35)), (7, math.radians(35)), (13, math.radians(-35))])

    fc = _fcurve(action, 'pose.bones["UpperArm.R"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(35)), (7, math.radians(-35)), (13, math.radians(35))])

    return action


def push_action_to_nla(arm_obj: bpy.types.Object, action: bpy.types.Action, start: int = 1) -> None:
    track = arm_obj.animation_data.nla_tracks.new()
    track.name = f"{action.name}_Track"
    strip = track.strips.new(name=action.name, start=start, action=action)
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

    walk = add_walk_action(arm_obj)
    push_action_to_nla(arm_obj, walk, start=1)

    idle = add_idle_action(arm_obj)
    push_action_to_nla(arm_obj, idle, start=30)

    run = add_run_action(arm_obj)
    push_action_to_nla(arm_obj, run, start=100)

    arm_obj.animation_data.action = None

    export_glb(arm_obj, mesh_parts)
    print("Done.")


if __name__ == "__main__":
    main()
