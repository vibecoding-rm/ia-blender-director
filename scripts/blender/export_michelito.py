"""
Blender headless script — construye "Michelito Filo, el Gallito Navaja", la cara
joven del agitprop: un gallo fino con cresta engominada, espejuelos, espolones y
una navajita de cartón. GLB riggeado con acciones NLA Idle / Talk / Walk.

El pico inferior es el hueso `Beak` (rotación X = abrir) para lip-sync.

Uso:
    blender --background --python scripts/blender/export_michelito.py

Salida:
    assets/characters/michelito_v1/michelito_v1.glb
"""

import math
from pathlib import Path

import bpy
import mathutils

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "assets" / "characters" / "michelito_v1" / "michelito_v1.glb"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# (name, head, tail, parent)
_BONES: list[tuple[str, tuple, tuple, str | None]] = [
    ("Root",   (0, 0, 0),          (0, 0, 0.1),        None),
    ("Body",   (0, 0, 0.30),       (0, 0, 0.85),       "Root"),
    ("Head",   (0, 0, 0.85),       (0, 0, 1.18),       "Body"),
    ("Beak",   (0, -0.16, 0.98),   (0, -0.34, 0.96),   "Head"),
    ("Wing.L", (-0.24, 0, 0.72),   (-0.46, 0, 0.55),   "Body"),
    ("Wing.R", (0.24, 0, 0.72),    (0.46, 0, 0.55),    "Body"),
    ("Tail",   (0, 0.22, 0.55),    (0, 0.45, 0.72),    "Body"),
    ("Leg.L",  (-0.10, 0, 0.30),   (-0.10, 0, 0.04),   "Root"),
    ("Leg.R",  (0.10, 0, 0.30),    (0.10, 0, 0.04),    "Root"),
    ("Eye.L",  (-0.10, -0.17, 1.05), (-0.10, -0.17, 1.11), "Head"),
    ("Eye.R",  (0.10, -0.17, 1.05),  (0.10, -0.17, 1.11),  "Head"),
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
    bsdf.inputs["Roughness"].default_value = 0.78
    return mat


def build_armature() -> bpy.types.Object:
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm_obj = bpy.context.object
    arm_obj.name = "Michelito_Armature"
    arm_obj.data.name = "Michelito_Rig"

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
    """Gallo fino joven, chulo, con espejuelos y navajita de cartón."""
    feather       = _solid_mat("Feather",      (0.18, 0.35, 0.47, 1.0))   # azul-petróleo
    feather_light = _solid_mat("FeatherLight", (0.28, 0.48, 0.60, 1.0))
    comb_red      = _solid_mat("CombRed",       (0.78, 0.13, 0.16, 1.0))
    beak_mat      = _solid_mat("BeakMat",       (0.95, 0.72, 0.15, 1.0))
    shirt         = _solid_mat("Shirt",         (0.92, 0.92, 0.90, 1.0))
    glasses       = _solid_mat("Glasses",       (0.05, 0.05, 0.06, 1.0))
    eye_white     = _solid_mat("EyeWhite",      (0.96, 0.96, 0.94, 1.0))
    eye_black     = _solid_mat("EyeBlack",      (0.04, 0.04, 0.05, 1.0))
    leg_mat       = _solid_mat("LegMat",        (0.90, 0.65, 0.15, 1.0))
    blade         = _solid_mat("Blade",         (0.70, 0.72, 0.75, 1.0))

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

    def _cone(name, loc, radius, depth, mat, bone, *, rot=None):
        bpy.ops.mesh.primitive_cone_add(vertices=14, radius1=radius, radius2=0.01, depth=depth, location=loc)
        obj = bpy.context.object
        obj.name = name
        if rot:
            obj.rotation_euler = rot
            bpy.ops.object.transform_apply(rotation=True)
        obj.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        parts.append((obj, bone))
        return obj

    def _cyl(name, loc, radius, depth, mat, bone, *, rot=None):
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=depth, location=loc)
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

    # Cuerpo: torso esbelto azul + camisa moderna (cuello blanco al frente)
    _sphere("Mesh_Body", (0, 0, 0.58), 0.28, feather, "Body", scale=(0.95, 0.9, 1.35))
    _sphere("Mesh_Shirt", (0, -0.14, 0.55), 0.18, shirt, "Body", scale=(0.75, 0.55, 1.1))
    _cube("Mesh_Collar", (0, -0.16, 0.74), (0.30, 0.18, 0.08), shirt, "Body", rot=(math.radians(12), 0, 0))

    # Cabeza redonda
    _sphere("Mesh_Head", (0, 0, 1.02), 0.22, feather_light, "Head")

    # Cresta engominada hacia atrás (varias puntas inclinadas)
    for i, (dy, dz, r) in enumerate([(0.02, 1.22, 0.06), (0.10, 1.20, 0.07), (0.18, 1.15, 0.06)]):
        _sphere(f"Mesh_Comb_{i}", (0, dy, dz), r, comb_red, "Head", scale=(0.5, 1.1, 1.2))
    # Barbas (wattles) rojas bajo el pico
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Wattle_{side}", (sign * 0.05, -0.18, 0.90), 0.04, comb_red, "Head", scale=(0.7, 0.7, 1.3))

    # Pico: superior fijo a la cabeza, inferior al hueso Beak (habla)
    _cone("Mesh_BeakUpper", (0, -0.28, 1.00), 0.07, 0.20, beak_mat, "Head", rot=(math.radians(-90), 0, 0))
    _cone("Mesh_BeakLower", (0, -0.26, 0.95), 0.055, 0.15, beak_mat, "Beak", rot=(math.radians(-94), 0, 0))

    # Espejuelos: dos aros negros + puente (el toque "moderno/irónico")
    for side, sign in (("L", -1), ("R", 1)):
        _cyl(f"Mesh_Glass_{side}", (sign * 0.10, -0.20, 1.05), 0.065, 0.02, glasses, "Head",
             rot=(math.radians(90), 0, 0))
    _cube("Mesh_GlassBridge", (0, -0.20, 1.06), (0.08, 0.02, 0.02), glasses, "Head")

    # Ojos: blanco + pupila, atados a su hueso para parpadear
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Eye_{side}", (sign * 0.10, -0.17, 1.05), 0.055, eye_white, f"Eye.{side}", segs=12, rings=8)
        _sphere(f"Mesh_Pupil_{side}", (sign * 0.10, -0.215, 1.05), 0.022, eye_black, f"Eye.{side}", segs=10, rings=6)

    # Alas
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Wing_{side}", (sign * 0.27, 0.02, 0.62), 0.16, feather, f"Wing.{side}",
                scale=(0.38, 0.7, 1.05))

    # Cola alta de gallo (abanico de plumas inclinadas hacia atrás)
    for i, (dx, dz, sx) in enumerate([(-0.06, 0.78, 0.5), (0.0, 0.86, 0.55), (0.06, 0.78, 0.5)]):
        _sphere(f"Mesh_TailFeather_{i}", (dx, 0.40, dz), 0.16, feather_light, "Tail",
                scale=(sx, 1.6, 0.4))

    # Patas amarillas + pies + espolones; navajita de cartón en la pata derecha
    for side, sign in (("L", -1), ("R", 1)):
        _cyl(f"Mesh_Leg_{side}", (sign * 0.10, 0, 0.16), 0.028, 0.26, leg_mat, f"Leg.{side}")
        _sphere(f"Mesh_Foot_{side}", (sign * 0.10, -0.05, 0.03), 0.06, leg_mat, f"Leg.{side}",
                scale=(1.0, 1.6, 0.5), segs=10, rings=6)
        _cone(f"Mesh_Spur_{side}", (sign * 0.14, 0.04, 0.14), 0.02, 0.08, leg_mat, f"Leg.{side}",
              rot=(0, 0, math.radians(sign * 40)))
    # Navajita de cartón atada al espolón derecho
    _cube("Mesh_Blade", (0.20, 0.02, 0.16), (0.02, 0.04, 0.16), blade, "Leg.R", rot=(0, 0, math.radians(35)))

    # Bind: cada parte 100% a su hueso
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

    # Pecho inflado chulo + ladeo de cabeza irónico + cola
    fc = _fcurve(action, 'pose.bones["Body"].location', 2)
    _add_keyframes(fc, [(1, 0), (18, 0.018), (36, 0), (54, 0.012), (70, 0)])
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 1)
    _add_keyframes(fc, [(1, 0), (20, math.radians(7)), (45, math.radians(-5)), (70, 0)])
    fc = _fcurve(action, 'pose.bones["Tail"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (35, math.radians(6)), (70, 0)])
    _add_blinks(action, [16, 50])
    return action


def add_talk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """Editorial 'Con Filo': pico afilado, cabeza ladeada irónica, ala que apunta."""
    action = bpy.data.actions.new(name="Talk")
    arm_obj.animation_data.action = action

    beak_keys: list[tuple[float, float]] = []
    for cycle in range(4):
        start = 1 + cycle * 12
        beak_keys += [(start, 0.0), (start + 4, math.radians(40)), (start + 9, math.radians(8))]
    beak_keys.append((48, 0.0))
    fc = _fcurve(action, 'pose.bones["Beak"].rotation_euler', 0)
    _add_keyframes(fc, beak_keys)

    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 1)
    _add_keyframes(fc, [(1, 0), (12, math.radians(10)), (24, math.radians(-6)), (36, math.radians(10)), (48, 0)])
    # Ala derecha apunta con ironía
    fc = _fcurve(action, 'pose.bones["Wing.R"].rotation_euler', 1)
    _add_keyframes(fc, [(1, 0), (14, math.radians(40)), (30, math.radians(12)), (48, math.radians(38))])
    fc = _fcurve(action, 'pose.bones["Wing.L"].rotation_euler', 1)
    _add_keyframes(fc, [(1, 0), (20, math.radians(-22)), (48, 0)])
    _add_blinks(action, [10, 34])
    return action


def add_walk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """Caminar chulo de gallo de pelea: pasos altos y pecho marcado."""
    action = bpy.data.actions.new(name="Walk")
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Body"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(7)), (8, math.radians(-7)), (16, math.radians(7)),
                        (24, math.radians(-7)), (32, math.radians(7))])
    fc = _fcurve(action, 'pose.bones["Root"].location', 2)
    _add_keyframes(fc, [(1, 0), (8, 0.05), (16, 0), (24, 0.05), (32, 0)])
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(-6)), (16, math.radians(6)), (32, math.radians(-6))])
    fc = _fcurve(action, 'pose.bones["Tail"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(-8)), (16, math.radians(8)), (32, math.radians(-8))])
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
    push_action_to_nla(arm_obj, talk, start=1)
    walk = add_walk_action(arm_obj)
    push_action_to_nla(arm_obj, walk, start=1)

    arm_obj.animation_data.action = None

    export_glb(arm_obj, mesh_parts)
    print("Done.")


if __name__ == "__main__":
    main()
