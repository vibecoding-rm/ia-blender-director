"""
Blender headless script — construye "El Guanajo Designado", el presidente-puppet:
un guanajo (pavo) desgarbado en un traje que le queda grande, con moco rojo caído
e hilos de marioneta que le salen de la espalda hacia una cruz de control.
GLB riggeado con acciones NLA Idle / Talk / Walk.

El pico inferior es el hueso `Beak` (rotación X = abrir) para lip-sync.

Uso:
    blender --background --python scripts/blender/export_guanajo.py

Salida:
    assets/characters/guanajo_v1/guanajo_v1.glb
"""

import math
from pathlib import Path

import bpy
import mathutils

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "assets" / "characters" / "guanajo_v1" / "guanajo_v1.glb"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# (name, head, tail, parent)
_BONES: list[tuple[str, tuple, tuple, str | None]] = [
    ("Root",   (0, 0, 0),          (0, 0, 0.1),        None),
    ("Body",   (0, 0, 0.40),       (0, 0, 0.92),       "Root"),
    ("Head",   (0, 0, 0.98),       (0, 0, 1.26),       "Body"),
    ("Beak",   (0, -0.14, 1.12),   (0, -0.30, 1.08),   "Head"),
    ("Wing.L", (-0.26, 0, 0.78),   (-0.46, 0, 0.55),   "Body"),
    ("Wing.R", (0.26, 0, 0.78),    (0.46, 0, 0.55),    "Body"),
    ("Tail",   (0, 0.22, 0.55),    (0, 0.42, 0.82),    "Body"),
    ("Leg.L",  (-0.12, 0, 0.40),   (-0.12, 0, 0.04),   "Root"),
    ("Leg.R",  (0.12, 0, 0.40),    (0.12, 0, 0.04),    "Root"),
    ("Eye.L",  (-0.10, -0.16, 1.12), (-0.10, -0.16, 1.18), "Head"),
    ("Eye.R",  (0.10, -0.16, 1.12),  (0.10, -0.16, 1.18),  "Head"),
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
    arm_obj.name = "Guanajo_Armature"
    arm_obj.data.name = "Guanajo_Rig"

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
    """Pavo desgarbado: traje grande, moco rojo, hilos de marioneta y cruz de control."""
    feather       = _solid_mat("Feather",      (0.43, 0.35, 0.23, 1.0))
    feather_light = _solid_mat("FeatherLight", (0.58, 0.49, 0.34, 1.0))
    head_skin     = _solid_mat("HeadSkin",     (0.50, 0.52, 0.62, 1.0))   # piel azulada de pavo
    red_skin      = _solid_mat("RedSkin",      (0.72, 0.16, 0.18, 1.0))   # moco/barba rojos
    beak_mat      = _solid_mat("BeakMat",      (0.85, 0.74, 0.42, 1.0))
    suit          = _solid_mat("Suit",         (0.16, 0.16, 0.20, 1.0))   # traje grande
    shirt         = _solid_mat("Shirt",        (0.92, 0.92, 0.90, 1.0))
    tie           = _solid_mat("Tie",          (0.60, 0.12, 0.16, 1.0))
    eye_white     = _solid_mat("EyeWhite",     (0.96, 0.96, 0.94, 1.0))
    eye_black     = _solid_mat("EyeBlack",     (0.04, 0.04, 0.05, 1.0))
    leg_mat       = _solid_mat("LegMat",       (0.85, 0.55, 0.20, 1.0))
    string_mat    = _solid_mat("String",       (0.78, 0.78, 0.76, 1.0))   # hilos
    bar_mat       = _solid_mat("Bar",          (0.40, 0.28, 0.16, 1.0))   # cruz de control

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

    def _cyl(name, loc, radius, depth, mat, bone, *, rot=None, verts=10):
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

    # Cuerpo: torso ovalado en traje grande + camisa y corbata torcida
    _sphere("Mesh_Body", (0, 0, 0.66), 0.30, suit, "Body", scale=(1.05, 0.92, 1.45))
    _sphere("Mesh_Shirt", (0, -0.16, 0.66), 0.18, shirt, "Body", scale=(0.7, 0.5, 1.15))
    _cube("Mesh_Tie", (0, -0.26, 0.58), (0.09, 0.04, 0.34), tie, "Body", rot=(0, math.radians(6), 0))
    # Solapas grandes del traje
    for side, sign in (("L", -1), ("R", 1)):
        _cube(f"Mesh_Lapel_{side}", (sign * 0.16, -0.20, 0.78), (0.12, 0.05, 0.26), suit, "Body",
              rot=(0, 0, math.radians(sign * 16)))

    # Cuello pelado largo (anillos) + cabeza pequeña
    for i, z in enumerate((0.90, 0.96)):
        _sphere(f"Mesh_Neck_{i}", (0, -0.02, z), 0.09 - i * 0.01, head_skin, "Body", scale=(0.9, 0.9, 0.8), segs=12, rings=8)
    _sphere("Mesh_Head", (0, -0.02, 1.10), 0.15, head_skin, "Head", scale=(1.0, 1.1, 1.0))

    # Moco rojo caído sobre el pico + barba (wattle) roja
    _cone("Mesh_Snood", (0, -0.20, 1.16), 0.035, 0.16, red_skin, "Head", rot=(math.radians(120), 0, 0))
    _sphere("Mesh_Wattle", (0, -0.10, 0.98), 0.05, red_skin, "Head", scale=(0.8, 0.8, 1.4))

    # Pico: superior fijo, inferior al hueso Beak
    _cone("Mesh_BeakUpper", (0, -0.24, 1.12), 0.06, 0.16, beak_mat, "Head", rot=(math.radians(-90), 0, 0))
    _cone("Mesh_BeakLower", (0, -0.22, 1.08), 0.045, 0.11, beak_mat, "Beak", rot=(math.radians(-95), 0, 0))

    # Ojos saltones bobalicones + pupila
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Eye_{side}", (sign * 0.10, -0.14, 1.12), 0.05, eye_white, f"Eye.{side}", segs=12, rings=8)
        _sphere(f"Mesh_Pupil_{side}", (sign * 0.10, -0.18, 1.12), 0.02, eye_black, f"Eye.{side}", segs=8, rings=6)

    # Alas (mangas grandes del traje)
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Wing_{side}", (sign * 0.30, 0.02, 0.66), 0.17, suit, f"Wing.{side}",
                scale=(0.45, 0.7, 1.1))
        _sphere(f"Mesh_Hand_{side}", (sign * 0.42, 0, 0.50), 0.07, head_skin, f"Wing.{side}", segs=10, rings=8)

    # Cola en abanico de pavo (plumas inclinadas hacia atrás)
    for i, (dx, dz, sx) in enumerate([(-0.12, 0.80, 0.4), (-0.06, 0.88, 0.45), (0.0, 0.92, 0.5),
                                      (0.06, 0.88, 0.45), (0.12, 0.80, 0.4)]):
        _sphere(f"Mesh_TailFeather_{i}", (dx, 0.42, dz), 0.16, feather_light if i % 2 else feather, "Tail",
                scale=(sx, 1.5, 0.35))

    # Patas largas y desgarbadas + pies
    for side, sign in (("L", -1), ("R", 1)):
        _cyl(f"Mesh_Leg_{side}", (sign * 0.12, 0, 0.22), 0.028, 0.36, leg_mat, f"Leg.{side}", verts=8)
        _sphere(f"Mesh_Foot_{side}", (sign * 0.12, -0.06, 0.03), 0.06, leg_mat, f"Leg.{side}",
                scale=(1.0, 1.7, 0.5), segs=10, rings=6)

    # Hilos de marioneta + cruz de control encima (lo que delata el personaje)
    _cube("Mesh_ControlBar", (0, 0.05, 1.72), (0.42, 0.05, 0.05), bar_mat, "Body")
    _cube("Mesh_ControlBar2", (0, 0.05, 1.72), (0.05, 0.05, 0.30), bar_mat, "Body")
    string_anchors = [("L", -0.30, 0.78), ("R", 0.30, 0.78), ("Head", 0.0, 1.24), ("Back", 0.0, 0.80)]
    for tag, ax, az in string_anchors:
        mid_z = (az + 1.70) / 2
        length = 1.70 - az
        _cyl(f"Mesh_String_{tag}", (ax * 0.6, 0.04, mid_z), 0.006, length, string_mat, "Body", verts=6)

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

    # Balanceo de marioneta colgada (rígido desde arriba) + cabeza bobalicona
    fc = _fcurve(action, 'pose.bones["Body"].location', 2)
    _add_keyframes(fc, [(1, 0), (20, 0.02), (40, 0), (60, 0.02), (80, 0)])
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 1)
    _add_keyframes(fc, [(1, 0), (25, math.radians(8)), (50, math.radians(-6)), (80, 0)])
    fc = _fcurve(action, 'pose.bones["Beak"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (40, math.radians(6)), (80, 0)])
    _add_blinks(action, [18, 55])
    return action


def add_talk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """Lee de tarjetas con torpeza: pico abre/cierra, cabeza se ladea robótica,
    el ala sube tiesa como tirada por un hilo."""
    action = bpy.data.actions.new(name="Talk")
    arm_obj.animation_data.action = action

    beak_keys: list[tuple[float, float]] = []
    for cycle in range(4):
        start = 1 + cycle * 12
        beak_keys += [(start, 0.0), (start + 4, math.radians(32)), (start + 9, math.radians(6))]
    beak_keys.append((48, 0.0))
    fc = _fcurve(action, 'pose.bones["Beak"].rotation_euler', 0)
    _add_keyframes(fc, beak_keys)

    # Cabeza ladeada robótica (LINEAR para sensación de marioneta tirada por hilos)
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (12, math.radians(7)), (24, math.radians(-4)), (36, math.radians(7)), (48, 0)],
                  interp="LINEAR")
    # Ala derecha sube tiesa (gesto de tribuna)
    fc = _fcurve(action, 'pose.bones["Wing.R"].rotation_euler', 1)
    _add_keyframes(fc, [(1, 0), (14, math.radians(40)), (30, math.radians(35)), (48, 0)], interp="LINEAR")
    _add_blinks(action, [10, 34])
    return action


def add_walk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """Caminar torpe y desgarbado, casi tropezando con los propios hilos."""
    action = bpy.data.actions.new(name="Walk")
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Body"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(6)), (8, math.radians(-9)), (16, math.radians(7)),
                        (24, math.radians(-9)), (32, math.radians(6))])
    fc = _fcurve(action, 'pose.bones["Root"].location', 2)
    _add_keyframes(fc, [(1, 0), (8, 0.06), (14, -0.01), (16, 0), (24, 0.06), (32, 0)])  # un tropezón en 14
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(-5)), (16, math.radians(8)), (32, math.radians(-5))])
    fc = _fcurve(action, 'pose.bones["Tail"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (16, math.radians(8)), (32, 0)])
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
