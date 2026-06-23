"""
Blender headless script - builds "El Caiman General", the old crocodile
puppet-master behind the throne. Rigged GLB with Idle, Talk and Walk NLA.

The lower jaw is the `Jaw` bone for lip-sync.

Usage:
    blender --background --python scripts/blender/export_caiman.py

Output:
    assets/characters/caiman_v1/caiman_v1.glb
"""

import math
from pathlib import Path

import bpy
import mathutils

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "assets" / "characters" / "caiman_v1" / "caiman_v1.glb"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

_BONES: list[tuple[str, tuple, tuple, str | None]] = [
    ("Root", (0, 0, 0), (0, 0, 0.1), None),
    ("Body", (0, 0, 0.34), (0, 0, 0.86), "Root"),
    ("Head", (0, -0.02, 0.88), (0, -0.34, 1.04), "Body"),
    ("Jaw", (0, -0.34, 0.91), (0, -0.62, 0.86), "Head"),
    ("Tail", (0, 0.26, 0.42), (0, 0.88, 0.28), "Body"),
    ("Arm.L", (-0.25, -0.02, 0.72), (-0.48, -0.10, 0.55), "Body"),
    ("Arm.R", (0.25, -0.02, 0.72), (0.48, -0.10, 0.55), "Body"),
    ("Leg.L", (-0.16, 0.02, 0.34), (-0.24, -0.08, 0.05), "Root"),
    ("Leg.R", (0.16, 0.02, 0.34), (0.24, -0.08, 0.05), "Root"),
    ("Eye.L", (-0.10, -0.30, 1.00), (-0.10, -0.30, 1.06), "Head"),
    ("Eye.R", (0.10, -0.30, 1.00), (0.10, -0.30, 1.06), "Head"),
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
    arm_obj.name = "Caiman_Armature"
    arm_obj.data.name = "Caiman_Rig"

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
    moss = _solid_mat("MossGreen", (0.23, 0.29, 0.16, 1.0))
    belly = _solid_mat("OldBelly", (0.55, 0.58, 0.36, 1.0))
    uniform = _solid_mat("OliveUniform", (0.18, 0.24, 0.12, 1.0))
    dark = _solid_mat("GlassesBlack", (0.015, 0.018, 0.02, 1.0))
    gold = _solid_mat("OldGold", (0.86, 0.68, 0.18, 1.0))
    tooth = _solid_mat("Tooth", (0.94, 0.90, 0.76, 1.0))
    string = _solid_mat("PuppetString", (0.78, 0.78, 0.72, 1.0))
    wood = _solid_mat("ControlWood", (0.34, 0.23, 0.13, 1.0))

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

    def _cone(name, loc, radius, depth, mat, bone, *, rot=None, verts=10):
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=radius, radius2=0.005, depth=depth, location=loc)
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

    # Heavy crocodile body in uniform.
    _sphere("Mesh_Body", (0, 0, 0.58), 0.33, uniform, "Body", scale=(1.10, 0.90, 1.15))
    _sphere("Mesh_Belly", (0, -0.22, 0.53), 0.20, belly, "Body", scale=(0.95, 0.45, 1.0))
    _cyl("Mesh_Belt", (0, -0.01, 0.40), 0.31, 0.055, dark, "Body", verts=18)
    _sphere("Mesh_Medal", (-0.12, -0.28, 0.70), 0.035, gold, "Body", scale=(1.0, 0.45, 1.0))

    # Long crocodile head and articulated lower jaw.
    _sphere("Mesh_Head", (0, -0.20, 0.98), 0.20, moss, "Head", scale=(0.95, 1.55, 0.62))
    _sphere("Mesh_Snout", (0, -0.45, 0.95), 0.16, moss, "Head", scale=(0.92, 1.55, 0.42))
    _sphere("Mesh_Jaw", (0, -0.43, 0.84), 0.13, moss, "Jaw", scale=(0.90, 1.55, 0.32))

    # Teeth on both sides of the mouth.
    for i, x in enumerate([-0.13, -0.07, 0.0, 0.07, 0.13]):
        y = -0.50 - abs(x) * 0.25
        _cone(f"Mesh_ToothTop_{i}", (x, y, 0.88), 0.018, 0.07, tooth, "Head", rot=(math.radians(180), 0, 0), verts=7)
        _cone(f"Mesh_ToothLow_{i}", (x, y, 0.82), 0.016, 0.055, tooth, "Jaw", verts=7)

    # Sunglasses and old general cap.
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Glasses_{side}", (sign * 0.095, -0.33, 1.02), 0.055, dark, f"Eye.{side}", scale=(1.35, 0.38, 0.72))
    _cube("Mesh_GlassesBridge", (0, -0.35, 1.02), (0.08, 0.018, 0.018), dark, "Head")
    _cyl("Mesh_CapBase", (0, -0.12, 1.12), 0.19, 0.08, uniform, "Head")
    _cyl("Mesh_CapTop", (0, -0.12, 1.17), 0.21, 0.035, uniform, "Head")
    _cone("Mesh_CapStar", (0, -0.29, 1.13), 0.035, 0.025, gold, "Head", rot=(math.radians(-90), 0, 0))

    # Arms, legs, claws.
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Arm_{side}", (sign * 0.34, -0.06, 0.62), 0.14, uniform, f"Arm.{side}", scale=(0.48, 0.70, 1.05))
        _sphere(f"Mesh_Hand_{side}", (sign * 0.48, -0.16, 0.48), 0.06, moss, f"Arm.{side}", scale=(1.25, 0.8, 0.55))
        _sphere(f"Mesh_Leg_{side}", (sign * 0.20, -0.01, 0.18), 0.09, uniform, f"Leg.{side}", scale=(0.85, 1.0, 1.5))
        _sphere(f"Mesh_Foot_{side}", (sign * 0.24, -0.14, 0.04), 0.07, moss, f"Leg.{side}", scale=(1.45, 1.6, 0.48))

    # Crocodile tail with dorsal bumps.
    _sphere("Mesh_Tail", (0, 0.54, 0.32), 0.14, moss, "Tail", scale=(0.78, 2.8, 0.55))
    for i, y in enumerate([0.14, 0.28, 0.42, 0.58, 0.74]):
        _cone(f"Mesh_BackSpike_{i}", (0, y, 0.72 - i * 0.06), 0.045, 0.08, moss, "Body", verts=6)

    # Puppet-master control bars and strings hanging down toward the Guanajo.
    _cube("Mesh_ControlBar", (0, -0.03, 1.58), (0.48, 0.045, 0.045), wood, "Body")
    _cube("Mesh_ControlBarCross", (0, -0.03, 1.58), (0.045, 0.045, 0.30), wood, "Body")
    for i, x in enumerate([-0.18, -0.06, 0.06, 0.18]):
        _cyl(f"Mesh_String_{i}", (x, -0.04, 1.18), 0.005, 0.78, string, "Body", verts=6)

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
    _add_keyframes(fc, [(1, 0), (24, 0.01), (48, 0), (72, 0.008), (96, 0)])
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (35, math.radians(-3)), (70, math.radians(2)), (96, 0)])
    fc = _fcurve(action, 'pose.bones["Tail"].rotation_euler', 2)
    _add_keyframes(fc, [(1, math.radians(-3)), (48, math.radians(4)), (96, math.radians(-3))])
    _add_blinks(action, [32, 78])
    return action


def add_talk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    action = bpy.data.actions.new(name="Talk")
    arm_obj.animation_data.action = action

    jaw_keys: list[tuple[float, float]] = []
    for cycle in range(4):
        start = 1 + cycle * 12
        jaw_keys += [(start, 0.0), (start + 4, math.radians(30)), (start + 9, math.radians(5))]
    jaw_keys.append((48, 0.0))
    fc = _fcurve(action, 'pose.bones["Jaw"].rotation_euler', 0)
    _add_keyframes(fc, jaw_keys)

    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (12, math.radians(5)), (24, math.radians(-2)), (36, math.radians(5)), (48, 0)])
    fc = _fcurve(action, 'pose.bones["Arm.R"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (12, math.radians(-36)), (28, math.radians(-50)), (48, 0)], interp="LINEAR")
    _add_blinks(action, [16, 39])
    return action


def add_walk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    action = bpy.data.actions.new(name="Walk")
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Root"].location', 1)
    _add_keyframes(fc, [(1, 0), (36, 0.46)], interp="LINEAR")
    fc = _fcurve(action, 'pose.bones["Body"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(3)), (12, math.radians(-4)), (24, math.radians(4)), (36, math.radians(3))])
    fc = _fcurve(action, 'pose.bones["Tail"].rotation_euler', 2)
    _add_keyframes(fc, [(1, math.radians(-8)), (18, math.radians(8)), (36, math.radians(-8))])
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
