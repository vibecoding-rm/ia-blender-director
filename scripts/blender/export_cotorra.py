"""
Blender headless script — builds "La Cotorra", the claymation news-anchor
parrot mascot, as a rigged GLB with embedded Idle, Talk and Walk NLA actions.

Usage:
    blender --background --python scripts/blender/export_cotorra.py

Output:
    assets/characters/cotorra_v1/cotorra_v1.glb
"""

import math
from pathlib import Path

import bpy
import mathutils

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "assets" / "characters" / "cotorra_v1" / "cotorra_v1.glb"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# (name, head, tail, parent)
_BONES: list[tuple[str, tuple, tuple, str | None]] = [
    ("Root",   (0, 0, 0),         (0, 0, 0.1),        None),
    ("Body",   (0, 0, 0.25),      (0, 0, 0.75),       "Root"),
    ("Head",   (0, 0, 0.75),      (0, 0, 1.10),       "Body"),
    ("Beak",   (0, -0.16, 0.86),  (0, -0.32, 0.84),   "Head"),
    ("Wing.L", (-0.26, 0, 0.68),  (-0.48, 0, 0.50),   "Body"),
    ("Wing.R", (0.26, 0, 0.68),   (0.48, 0, 0.50),    "Body"),
    ("Tail",   (0, 0.24, 0.45),   (0, 0.46, 0.34),    "Body"),
    ("Leg.L",  (-0.10, 0, 0.25),  (-0.10, 0, 0.04),   "Root"),
    ("Leg.R",  (0.10, 0, 0.25),   (0.10, 0, 0.04),    "Root"),
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
    bsdf.inputs["Roughness"].default_value = 0.8
    return mat


def build_armature() -> bpy.types.Object:
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm_obj = bpy.context.object
    arm_obj.name = "Cotorra_Armature"
    arm_obj.data.name = "Cotorra_Rig"

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
    """Soft rounded parrot. Every part is bound 100% to a single bone so the
    deformation stays clean and claymation-stiff (no auto-weight bleeding)."""
    feather       = _solid_mat("Feather",      (0.16, 0.52, 0.24, 1.0))
    feather_light = _solid_mat("FeatherLight", (0.34, 0.68, 0.32, 1.0))
    belly         = _solid_mat("Belly",        (0.85, 0.78, 0.45, 1.0))
    beak_mat      = _solid_mat("BeakMat",      (0.95, 0.62, 0.12, 1.0))
    eye_white     = _solid_mat("EyeWhite",     (0.96, 0.96, 0.94, 1.0))
    eye_black     = _solid_mat("EyeBlack",     (0.04, 0.04, 0.05, 1.0))
    crest_red     = _solid_mat("CrestRed",     (0.82, 0.10, 0.12, 1.0))
    leg_mat       = _solid_mat("LegMat",       (0.90, 0.55, 0.18, 1.0))

    parts: list[tuple[bpy.types.Object, str]] = []

    def _sphere(name, loc, radius, mat, bone, *, scale=None, segs=20, rings=14):
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

    def _cone(name, loc, radius, depth, mat, bone, *, rot=None):
        bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=radius, radius2=0.012, depth=depth, location=loc)
        obj = bpy.context.object
        obj.name = name
        if rot:
            obj.rotation_euler = rot
            bpy.ops.object.transform_apply(rotation=True)
        obj.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        parts.append((obj, bone))
        return obj

    def _cyl(name, loc, radius, depth, mat, bone):
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=depth, location=loc)
        obj = bpy.context.object
        obj.name = name
        obj.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        parts.append((obj, bone))
        return obj

    # Body: egg shape + lighter belly patch in front (-Y faces the camera)
    _sphere("Mesh_Body", (0, 0, 0.52), 0.30, feather, "Body", scale=(1.0, 0.92, 1.22))
    _sphere("Mesh_Belly", (0, -0.13, 0.48), 0.22, belly, "Body", scale=(0.85, 0.62, 1.05))

    # Head: big and round (claymation cuteness ratio)
    _sphere("Mesh_Head", (0, 0, 0.94), 0.245, feather_light, "Head")

    # Beak: upper fixed to Head, lower jaw on its own Beak bone so it can talk
    _cone("Mesh_BeakUpper", (0, -0.295, 0.905), 0.075, 0.22, beak_mat, "Head",
          rot=(math.radians(-90), 0, 0))
    _cone("Mesh_BeakLower", (0, -0.26, 0.845), 0.055, 0.15, beak_mat, "Beak",
          rot=(math.radians(-94), 0, 0))

    # Eyes: big white spheres + pupils, slightly toward camera
    for sign in (-1, 1):
        _sphere(f"Mesh_Eye_{sign}", (sign * 0.105, -0.165, 1.015), 0.075, eye_white, "Head", segs=14, rings=10)
        _sphere(f"Mesh_Pupil_{sign}", (sign * 0.105, -0.228, 1.018), 0.030, eye_black, "Head", segs=10, rings=8)

    # Red crest: three little flames on top (nod to satire, very recognizable)
    for i, (dy, dz, r) in enumerate([(-0.04, 1.17, 0.055), (0.03, 1.20, 0.065), (0.10, 1.16, 0.05)]):
        _sphere(f"Mesh_Crest_{i}", (0, dy, dz), r, crest_red, "Head", scale=(0.55, 0.8, 1.3))

    # Wings: flattened teardrops
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Wing_{side}", (sign * 0.295, 0.02, 0.60), 0.20, feather, f"Wing.{side}",
                scale=(0.38, 0.75, 1.05))

    # Tail: fan of flattened spheres
    _sphere("Mesh_Tail", (0, 0.33, 0.42), 0.17, feather, "Tail", scale=(0.8, 1.4, 0.45))

    # Legs + feet
    for side, sign in (("L", -1), ("R", 1)):
        _cyl(f"Mesh_Leg_{side}", (sign * 0.10, 0, 0.14), 0.032, 0.22, leg_mat, f"Leg.{side}")
        _sphere(f"Mesh_Foot_{side}", (sign * 0.10, -0.05, 0.035), 0.07, leg_mat, f"Leg.{side}",
                scale=(1.0, 1.6, 0.5), segs=10, rings=8)

    # Bind: each part 100% to its bone via explicit vertex group
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


def add_idle_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    action = bpy.data.actions.new(name="Idle")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Body"].location', 2)
    _add_keyframes(fc, [(1, 0), (15, 0.015), (30, 0), (45, 0.01), (60, 0)])

    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 2)
    _add_keyframes(fc, [(1, 0), (20, math.radians(5)), (40, math.radians(-4)), (60, 0)])

    fc = _fcurve(action, 'pose.bones["Tail"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (30, math.radians(8)), (60, 0)])
    return action


def add_talk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """News-anchor delivery: beak flaps, head nods, wings gesture."""
    action = bpy.data.actions.new(name="Talk")
    arm_obj.animation_data.action = action

    # Lower beak opens by rotating around X (4 syllable cycles in 48 frames)
    beak_keys: list[tuple[float, float]] = []
    for cycle in range(4):
        start = 1 + cycle * 12
        beak_keys += [(start, 0.0), (start + 4, math.radians(28)), (start + 9, math.radians(4))]
    beak_keys.append((48, 0.0))
    fc = _fcurve(action, 'pose.bones["Beak"].rotation_euler', 0)
    _add_keyframes(fc, beak_keys)

    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (12, math.radians(6)), (24, math.radians(-3)), (36, math.radians(5)), (48, 0)])

    fc = _fcurve(action, 'pose.bones["Wing.L"].rotation_euler', 1)
    _add_keyframes(fc, [(1, 0), (10, math.radians(-35)), (22, math.radians(-10)), (34, math.radians(-40)), (48, 0)])

    fc = _fcurve(action, 'pose.bones["Wing.R"].rotation_euler', 1)
    _add_keyframes(fc, [(1, 0), (16, math.radians(30)), (30, math.radians(8)), (42, math.radians(35)), (48, 0)])
    return action


def add_walk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """Comedic waddle: body rolls side to side with little hops."""
    action = bpy.data.actions.new(name="Walk")
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Body"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(10)), (7, math.radians(-10)), (13, math.radians(10)),
                        (19, math.radians(-10)), (25, math.radians(10))])

    fc = _fcurve(action, 'pose.bones["Root"].location', 2)
    _add_keyframes(fc, [(1, 0), (4, 0.05), (7, 0), (10, 0.05), (13, 0),
                        (16, 0.05), (19, 0), (22, 0.05), (25, 0)])

    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(-6)), (7, math.radians(6)), (13, math.radians(-6)),
                        (19, math.radians(6)), (25, math.radians(-6))])

    fc = _fcurve(action, 'pose.bones["Wing.L"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(-15)), (13, math.radians(-30)), (25, math.radians(-15))])

    fc = _fcurve(action, 'pose.bones["Wing.R"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(30)), (13, math.radians(15)), (25, math.radians(30))])
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

    idle = add_idle_action(arm_obj)
    push_action_to_nla(arm_obj, idle, start=1)

    talk = add_talk_action(arm_obj)
    push_action_to_nla(arm_obj, talk, start=80)

    walk = add_walk_action(arm_obj)
    push_action_to_nla(arm_obj, walk, start=160)

    arm_obj.animation_data.action = None

    export_glb(arm_obj, mesh_parts)
    print("Done.")


if __name__ == "__main__":
    main()
