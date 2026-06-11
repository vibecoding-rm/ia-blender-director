"""
Blender headless script — builds "El Comandante Cerdo", the regime spokesman
of the satire channel, as a rigged GLB with embedded Idle, Talk and Walk
NLA actions (all tracks starting at frame 1).

The archetype reads instantly worldwide (Animal Farm): a pig in an olive-green
uniform with a starred cap delivering official statements.

Usage:
    blender --background --python scripts/blender/export_cerdo.py

Output:
    assets/characters/comandante_cerdo_v1/comandante_cerdo_v1.glb
"""

import math
from pathlib import Path

import bpy
import mathutils

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "assets" / "characters" / "comandante_cerdo_v1" / "comandante_cerdo_v1.glb"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# (name, head, tail, parent)
_BONES: list[tuple[str, tuple, tuple, str | None]] = [
    ("Root",   (0, 0, 0),          (0, 0, 0.1),         None),
    ("Body",   (0, 0, 0.22),       (0, 0, 0.78),        "Root"),
    ("Head",   (0, 0, 0.78),       (0, 0, 1.15),        "Body"),
    ("Jaw",    (0, -0.17, 0.86),   (0, -0.31, 0.82),    "Head"),
    ("Arm.L",  (-0.28, 0, 0.72),   (-0.50, 0, 0.55),    "Body"),
    ("Arm.R",  (0.28, 0, 0.72),    (0.50, 0, 0.55),     "Body"),
    ("Leg.L",  (-0.11, 0, 0.22),   (-0.11, 0, 0.03),    "Root"),
    ("Leg.R",  (0.11, 0, 0.22),    (0.11, 0, 0.03),     "Root"),
    ("Eye.L",  (-0.095, -0.20, 1.04), (-0.095, -0.20, 1.09), "Head"),
    ("Eye.R",  (0.095, -0.20, 1.04),  (0.095, -0.20, 1.09),  "Head"),
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
    arm_obj.name = "Cerdo_Armature"
    arm_obj.data.name = "Cerdo_Rig"

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
    pink       = _solid_mat("PigPink",     (0.93, 0.62, 0.58, 1.0))
    pink_dark  = _solid_mat("PigPinkDark", (0.82, 0.48, 0.46, 1.0))
    uniform    = _solid_mat("Uniform",     (0.26, 0.30, 0.16, 1.0))
    uniform_dk = _solid_mat("UniformDark", (0.18, 0.21, 0.11, 1.0))
    eye_white  = _solid_mat("EyeWhite",    (0.95, 0.95, 0.92, 1.0))
    eye_black  = _solid_mat("EyeBlack",    (0.05, 0.05, 0.06, 1.0))
    star_red   = _solid_mat("StarRed",     (0.82, 0.10, 0.12, 1.0))
    medal_gold = _solid_mat("MedalGold",   (0.92, 0.78, 0.18, 1.0))
    cigar_mat  = _solid_mat("Cigar",       (0.36, 0.22, 0.12, 1.0))
    hoof_mat   = _solid_mat("Hoof",        (0.22, 0.14, 0.12, 1.0))

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

    def _cyl(name, loc, radius, depth, mat, bone, *, rot=None, vertices=14):
        bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
        obj = bpy.context.object
        obj.name = name
        if rot:
            obj.rotation_euler = rot
            bpy.ops.object.transform_apply(rotation=True)
        obj.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        parts.append((obj, bone))
        return obj

    def _cone(name, loc, radius, depth, mat, bone, *, rot=None):
        bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=radius, radius2=0.01, depth=depth, location=loc)
        obj = bpy.context.object
        obj.name = name
        if rot:
            obj.rotation_euler = rot
            bpy.ops.object.transform_apply(rotation=True)
        obj.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        parts.append((obj, bone))
        return obj

    # Body: uniformed barrel belly
    _sphere("Mesh_Body", (0, 0, 0.50), 0.33, uniform, "Body", scale=(1.0, 0.95, 1.18))
    # Belt
    _cyl("Mesh_Belt", (0, 0, 0.36), 0.315, 0.07, uniform_dk, "Body")
    _sphere("Mesh_Buckle", (0, -0.30, 0.36), 0.045, medal_gold, "Body", scale=(1.0, 0.4, 0.8))

    # Medals on the chest (left side, of course)
    for i, (mx, mz) in enumerate([(-0.14, 0.66), (-0.07, 0.64), (-0.105, 0.57)]):
        _sphere(f"Mesh_Medal_{i}", (mx, -0.275, mz), 0.028, medal_gold, "Body", scale=(1.0, 0.4, 1.0), segs=10, rings=8)

    # Head: pink, slightly flattened
    _sphere("Mesh_Head", (0, 0, 0.98), 0.26, pink, "Head", scale=(1.0, 0.92, 0.95))

    # Snout: the pig signature, pointing at the camera (-Y)
    _cyl("Mesh_Snout", (0, -0.255, 0.93), 0.085, 0.10, pink_dark, "Head", rot=(math.radians(90), 0, 0))
    for sign in (-1, 1):
        _sphere(f"Mesh_Nostril_{sign}", (sign * 0.032, -0.305, 0.93), 0.016, eye_black, "Head", segs=8, rings=6)

    # Jaw: lower lip/chin on its own bone so he can deliver statements
    _sphere("Mesh_Jaw", (0, -0.19, 0.835), 0.10, pink_dark, "Jaw", scale=(1.0, 0.8, 0.55))

    # Cigar at the mouth corner (attached to the jaw so it bobs while talking)
    _cyl("Mesh_Cigar", (0.10, -0.27, 0.85), 0.022, 0.16, cigar_mat, "Jaw",
         rot=(math.radians(78), 0, math.radians(-18)), vertices=10)

    # Ears
    for side, sign in (("L", -1), ("R", 1)):
        _cone(f"Mesh_Ear_{side}", (sign * 0.17, 0.02, 1.22), 0.07, 0.14, pink, "Head",
              rot=(math.radians(-15), 0, sign * math.radians(20)))

    # Eyes (small and stern) + angry brows
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Eye_{side}", (sign * 0.095, -0.20, 1.04), 0.045, eye_white, f"Eye.{side}", segs=12, rings=8)
        _sphere(f"Mesh_Pupil_{side}", (sign * 0.095, -0.238, 1.04), 0.018, eye_black, f"Eye.{side}", segs=8, rings=6)
        _sphere(f"Mesh_Brow_{side}", (sign * 0.10, -0.215, 1.10), 0.05, pink_dark, "Head",
                scale=(1.2, 0.35, 0.28))

    # Military cap with red star
    _cyl("Mesh_CapBase", (0, 0.01, 1.22), 0.20, 0.10, uniform_dk, "Head")
    _cyl("Mesh_CapTop", (0, 0.01, 1.275), 0.225, 0.035, uniform_dk, "Head")
    _cyl("Mesh_CapBrim", (0, -0.17, 1.185), 0.11, 0.02, uniform_dk, "Head",
         rot=(math.radians(8), 0, 0))
    _cone("Mesh_CapStar", (0, -0.185, 1.235), 0.035, 0.03, star_red, "Head",
          rot=(math.radians(-90), 0, 0))

    # Arms: uniformed, ending in pink trotters
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Arm_{side}", (sign * 0.36, 0, 0.64), 0.16, uniform, f"Arm.{side}",
                scale=(0.45, 0.55, 1.0))
        _sphere(f"Mesh_Hand_{side}", (sign * 0.44, 0, 0.47), 0.065, pink, f"Arm.{side}", segs=10, rings=8)

    # Legs + hooves
    for side, sign in (("L", -1), ("R", 1)):
        _cyl(f"Mesh_Leg_{side}", (sign * 0.11, 0, 0.13), 0.05, 0.2, uniform_dk, f"Leg.{side}", vertices=10)
        _sphere(f"Mesh_Hoof_{side}", (sign * 0.11, -0.02, 0.03), 0.065, hoof_mat, f"Leg.{side}",
                scale=(1.0, 1.3, 0.5), segs=10, rings=8)

    # Curly tail
    _sphere("Mesh_Tail", (0, 0.32, 0.45), 0.05, pink, "Body", scale=(0.7, 1.2, 0.7), segs=10, rings=8)

    # Bind each part 100% to its bone
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
    """Severo e inmóvil, respira y asiente lento con desaprobación."""
    action = bpy.data.actions.new(name="Idle")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Body"].location', 2)
    _add_keyframes(fc, [(1, 0), (18, 0.012), (36, 0), (50, 0.008), (60, 0)])

    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (25, math.radians(-4)), (45, math.radians(2)), (60, 0)])

    _add_blinks(action, [20, 48])
    return action


def add_talk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """Parte oficial: mandíbula enfática, dedo acusador, cabeza autoritaria."""
    action = bpy.data.actions.new(name="Talk")
    arm_obj.animation_data.action = action

    jaw_keys: list[tuple[float, float]] = []
    for cycle in range(4):
        start = 1 + cycle * 12
        jaw_keys += [(start, 0.0), (start + 4, math.radians(38)), (start + 9, math.radians(6))]
    jaw_keys.append((48, 0.0))
    fc = _fcurve(action, 'pose.bones["Jaw"].rotation_euler', 0)
    _add_keyframes(fc, jaw_keys)

    # Cabeza: énfasis de tribuna (golpes hacia delante)
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (8, math.radians(8)), (16, math.radians(-2)),
                        (26, math.radians(9)), (36, math.radians(-3)), (48, 0)])

    # Brazo derecho: dedo acusador que sube y baja
    fc = _fcurve(action, 'pose.bones["Arm.R"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (10, math.radians(-70)), (20, math.radians(-50)),
                        (30, math.radians(-75)), (40, math.radians(-20)), (48, 0)])

    fc = _fcurve(action, 'pose.bones["Arm.L"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (24, math.radians(-15)), (48, 0)])

    _add_blinks(action, [14, 38])
    return action


def add_walk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """Paso marcial pomposo con barriga."""
    action = bpy.data.actions.new(name="Walk")
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Body"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(7)), (7, math.radians(-7)), (13, math.radians(7)),
                        (19, math.radians(-7)), (25, math.radians(7))])

    fc = _fcurve(action, 'pose.bones["Root"].location', 2)
    _add_keyframes(fc, [(1, 0), (4, 0.04), (7, 0), (10, 0.04), (13, 0),
                        (16, 0.04), (19, 0), (22, 0.04), (25, 0)])

    fc = _fcurve(action, 'pose.bones["Arm.L"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(20)), (13, math.radians(-20)), (25, math.radians(20))])

    fc = _fcurve(action, 'pose.bones["Arm.R"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(-20)), (13, math.radians(20)), (25, math.radians(-20))])

    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 2)
    _add_keyframes(fc, [(1, math.radians(-4)), (13, math.radians(4)), (25, math.radians(-4))])

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
