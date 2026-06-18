"""
Blender headless script — construye "Randy Redondo, la Tortuga de Mesa", el
decano de la propaganda: una tortuga vieja con gafas y traje, atrapada tras una
mesa redonda. GLB riggeado con acciones NLA Idle / Talk / Walk (lentas).

La mandíbula es el hueso `Jaw` (rotación X = abrir) para lip-sync.

Uso:
    blender --background --python scripts/blender/export_randy.py

Salida:
    assets/characters/randy_v1/randy_v1.glb
"""

import math
from pathlib import Path

import bpy
import mathutils

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "assets" / "characters" / "randy_v1" / "randy_v1.glb"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# (name, head, tail, parent)
_BONES: list[tuple[str, tuple, tuple, str | None]] = [
    ("Root",   (0, 0, 0),          (0, 0, 0.1),        None),
    ("Body",   (0, 0, 0.34),       (0, 0, 0.74),       "Root"),
    ("Head",   (0, -0.05, 0.80),   (0, -0.15, 1.02),   "Body"),
    ("Jaw",    (0, -0.14, 0.88),   (0, -0.26, 0.84),   "Head"),
    ("Arm.L",  (-0.28, 0, 0.58),   (-0.46, 0, 0.46),   "Body"),
    ("Arm.R",  (0.28, 0, 0.58),    (0.46, 0, 0.46),    "Body"),
    ("Leg.L",  (-0.16, 0, 0.30),   (-0.16, 0, 0.05),   "Root"),
    ("Leg.R",  (0.16, 0, 0.30),    (0.16, 0, 0.05),    "Root"),
    ("Tail",   (0, 0.26, 0.34),    (0, 0.38, 0.30),    "Root"),
    ("Eye.L",  (-0.09, -0.18, 0.95), (-0.09, -0.18, 1.01), "Head"),
    ("Eye.R",  (0.09, -0.18, 0.95),  (0.09, -0.18, 1.01),  "Head"),
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
    arm_obj.name = "Randy_Armature"
    arm_obj.data.name = "Randy_Rig"

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
    """Tortuga vieja con caparazón (logo despegado), gafas, traje y mesa redonda."""
    shell       = _solid_mat("Shell",      (0.33, 0.42, 0.18, 1.0))   # verde-oliva
    shell_dark  = _solid_mat("ShellDark",  (0.24, 0.30, 0.13, 1.0))
    skin        = _solid_mat("Skin",       (0.54, 0.54, 0.48, 1.0))    # piel gris
    suit        = _solid_mat("Suit",       (0.30, 0.22, 0.14, 1.0))    # traje marrón
    glasses     = _solid_mat("Glasses",    (0.05, 0.05, 0.06, 1.0))
    eye_white   = _solid_mat("EyeWhite",   (0.96, 0.96, 0.94, 1.0))
    eye_black   = _solid_mat("EyeBlack",   (0.04, 0.04, 0.05, 1.0))
    beak_tan    = _solid_mat("BeakTan",    (0.70, 0.62, 0.40, 1.0))
    table       = _solid_mat("Table",      (0.35, 0.24, 0.15, 1.0))
    logo        = _solid_mat("Logo",       (0.70, 0.12, 0.12, 1.0))    # logo del canal
    cup         = _solid_mat("Cup",        (0.90, 0.90, 0.88, 1.0))

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

    def _cyl(name, loc, radius, depth, mat, bone, *, rot=None, verts=20):
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

    def _torus(name, loc, major, minor, mat, bone):
        bpy.ops.mesh.primitive_torus_add(location=loc, major_radius=major, minor_radius=minor,
                                         major_segments=24, minor_segments=10)
        obj = bpy.context.object
        obj.name = name
        obj.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        parts.append((obj, bone))
        return obj

    # Caparazón (domo) sobre la espalda + plastrón claro al frente
    _sphere("Mesh_Shell", (0, 0.06, 0.62), 0.34, shell, "Body", scale=(1.15, 1.0, 0.8))
    _sphere("Mesh_Plastron", (0, -0.18, 0.52), 0.24, suit, "Body", scale=(0.9, 0.5, 1.0))
    # Líneas de escudos (scutes) sugeridas con cubitos oscuros
    for i, dx in enumerate((-0.14, 0.0, 0.14)):
        _cube(f"Mesh_Scute_{i}", (dx, 0.06, 0.82), (0.03, 0.30, 0.02), shell_dark, "Body")
    # Logo del canal medio despegado (cuadro inclinado)
    _cube("Mesh_Logo", (0.14, -0.10, 0.66), (0.14, 0.02, 0.12), logo, "Body", rot=(0, 0, math.radians(18)))

    # Cuello arrugado (anillos apilados) + cabeza
    for i, z in enumerate((0.74, 0.80)):
        _sphere(f"Mesh_NeckRing_{i}", (0, -0.04, z), 0.10 - i * 0.01, skin, "Body", scale=(1.0, 1.0, 0.6), segs=12, rings=8)
    _sphere("Mesh_Head", (0, -0.08, 0.92), 0.16, skin, "Head", scale=(1.05, 1.15, 0.95))

    # Pico de tortuga: superior fijo, inferior al hueso Jaw
    _cube("Mesh_BeakUpper", (0, -0.22, 0.90), (0.16, 0.12, 0.05), beak_tan, "Head")
    _cube("Mesh_Jaw", (0, -0.21, 0.855), (0.16, 0.12, 0.04), beak_tan, "Jaw")

    # Gafas grandes (dos lentes + puente)
    for side, sign in (("L", -1), ("R", 1)):
        _cyl(f"Mesh_Glass_{side}", (sign * 0.09, -0.20, 0.95), 0.06, 0.02, glasses, "Head",
             rot=(math.radians(90), 0, 0), verts=16)
    _cube("Mesh_GlassBridge", (0, -0.20, 0.95), (0.08, 0.02, 0.02), glasses, "Head")

    # Ojos somnolientos (achatados) + pupila
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Eye_{side}", (sign * 0.09, -0.18, 0.95), 0.05, eye_white, f"Eye.{side}",
                scale=(1.0, 1.0, 0.7), segs=12, rings=8)
        _sphere(f"Mesh_Pupil_{side}", (sign * 0.09, -0.225, 0.95), 0.02, eye_black, f"Eye.{side}", segs=8, rings=6)

    # Brazos (mangas marrón) + manos; patas traseras gruesas
    for side, sign in (("L", -1), ("R", 1)):
        _cyl(f"Mesh_Arm_{side}", (sign * 0.36, 0, 0.52), 0.07, 0.30, suit, f"Arm.{side}",
             rot=(0, math.radians(sign * 45), 0))
        _sphere(f"Mesh_Hand_{side}", (sign * 0.46, -0.02, 0.44), 0.08, skin, f"Arm.{side}", segs=10, rings=8)
        _cyl(f"Mesh_Leg_{side}", (sign * 0.16, 0, 0.16), 0.09, 0.26, skin, f"Leg.{side}")
        _sphere(f"Mesh_Foot_{side}", (sign * 0.16, -0.06, 0.04), 0.09, skin, f"Leg.{side}",
                scale=(1.0, 1.4, 0.5), segs=10, rings=6)

    # Colita
    _cone_loc = None
    _sphere("Mesh_Tail", (0, 0.34, 0.30), 0.05, skin, "Tail", scale=(1.0, 1.6, 1.0), segs=8, rings=6)

    # Mesa redonda que la atrapa (anillo + tablero) + taza de café
    _torus("Mesh_TableRing", (0, -0.05, 0.46), 0.46, 0.05, table, "Root")
    _cyl("Mesh_TableTop", (0, -0.05, 0.43), 0.46, 0.03, table, "Root", verts=28)
    _cyl("Mesh_Cup", (0.22, -0.18, 0.49), 0.05, 0.07, cup, "Root", verts=12)

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
            # Parpadeo lento de tortuga vieja
            keys += [(frame - 4, 1.0), (frame, 0.1), (frame + 4, 1.0)]
        fc = _fcurve(action, f'pose.bones["Eye.{side}"].scale', 1)
        _add_keyframes(fc, keys)


def add_idle_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    action = bpy.data.actions.new(name="Idle")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action

    # Respiración lentísima + cabeza que cabecea de sueño
    fc = _fcurve(action, 'pose.bones["Body"].location', 2)
    _add_keyframes(fc, [(1, 0), (40, 0.015), (90, 0)])
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (45, math.radians(8)), (90, 0)])
    fc = _fcurve(action, 'pose.bones["Jaw"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (60, math.radians(5)), (90, 0)])
    _add_blinks(action, [30, 75])
    return action


def add_talk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """Monólogo interminable: mandíbula lenta y monótona, cabeceo solemne."""
    action = bpy.data.actions.new(name="Talk")
    arm_obj.animation_data.action = action

    # Ciclos lentos (3 en 60 frames) — habla pausada y eterna
    jaw_keys: list[tuple[float, float]] = []
    for cycle in range(3):
        start = 1 + cycle * 20
        jaw_keys += [(start, 0.0), (start + 8, math.radians(22)), (start + 16, math.radians(4))]
    jaw_keys.append((60, 0.0))
    fc = _fcurve(action, 'pose.bones["Jaw"].rotation_euler', 0)
    _add_keyframes(fc, jaw_keys)

    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (20, math.radians(6)), (40, math.radians(-3)), (60, math.radians(6))])
    fc = _fcurve(action, 'pose.bones["Arm.R"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (30, math.radians(-18)), (60, 0)])
    _add_blinks(action, [18, 48])
    return action


def add_walk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """'Caminar' de tortuga: lentísimo balanceo del caparazón."""
    action = bpy.data.actions.new(name="Walk")
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Body"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(4)), (20, math.radians(-4)), (40, math.radians(4)),
                        (60, math.radians(-4))])
    fc = _fcurve(action, 'pose.bones["Root"].location', 2)
    _add_keyframes(fc, [(1, 0), (20, 0.02), (40, 0), (60, 0.02)])
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(-4)), (30, math.radians(4)), (60, math.radians(-4))])
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
