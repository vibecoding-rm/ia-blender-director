"""
Blender headless script — construye "Humbrete, el Sabueso de Expediente", el
fiscal televisivo del régimen (caricatura de un bulldog), como GLB riggeado con
acciones NLA Idle / Talk / Walk.

La mandíbula es el hueso `Jaw` (rotación X = abrir la boca) para que el lip-sync
por audio (Rhubarb) lo controle igual que el pico de La Cotorra.

Uso:
    blender --background --python scripts/blender/export_humbrete.py

Salida:
    assets/characters/humbrete_v1/humbrete_v1.glb
"""

import math
from pathlib import Path

import bpy
import mathutils

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "assets" / "characters" / "humbrete_v1" / "humbrete_v1.glb"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# (name, head, tail, parent)
_BONES: list[tuple[str, tuple, tuple, str | None]] = [
    ("Root",   (0, 0, 0),          (0, 0, 0.1),        None),
    ("Body",   (0, 0, 0.50),       (0, 0, 1.00),       "Root"),
    ("Head",   (0, 0, 1.00),       (0, 0, 1.38),       "Body"),
    # Mandíbula: apunta hacia delante (-Y) y abajo; rotar en X abre la boca.
    ("Jaw",    (0, -0.10, 1.06),   (0, -0.30, 1.00),   "Head"),
    ("Arm.L",  (-0.32, 0, 0.92),   (-0.58, 0, 0.66),   "Body"),
    ("Arm.R",  (0.32, 0, 0.92),    (0.58, 0, 0.66),    "Body"),
    ("Leg.L",  (-0.16, 0, 0.50),   (-0.16, 0, 0.04),   "Root"),
    ("Leg.R",  (0.16, 0, 0.50),    (0.16, 0, 0.04),    "Root"),
    ("Tail",   (0, 0.22, 0.58),    (0, 0.36, 0.64),    "Root"),
    # Huesos de ojos verticales: el parpadeo es scale Y (aplasta la esfera)
    ("Eye.L",  (-0.13, -0.20, 1.20), (-0.13, -0.20, 1.27), "Head"),
    ("Eye.R",  (0.13, -0.20, 1.20),  (0.13, -0.20, 1.27),  "Head"),
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
    arm_obj.name = "Humbrete_Armature"
    arm_obj.data.name = "Humbrete_Rig"

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
    """Bulldog rechoncho en traje apretado, con papada, ceño y carpeta secreta.
    Cada parte se ata 100% a un hueso para una deformación claymation rígida."""
    fur        = _solid_mat("Fur",       (0.42, 0.29, 0.17, 1.0))   # marrón-tabaco
    fur_light  = _solid_mat("FurLight",  (0.55, 0.41, 0.26, 1.0))
    suit       = _solid_mat("Suit",      (0.35, 0.35, 0.38, 1.0))   # traje gris
    shirt      = _solid_mat("Shirt",     (0.90, 0.90, 0.86, 1.0))
    tie        = _solid_mat("Tie",       (0.64, 0.12, 0.16, 1.0))
    teeth      = _solid_mat("Teeth",     (0.95, 0.95, 0.92, 1.0))
    nose_mat   = _solid_mat("Nose",      (0.05, 0.05, 0.06, 1.0))
    eye_white  = _solid_mat("EyeWhite",  (0.96, 0.96, 0.94, 1.0))
    eye_black  = _solid_mat("EyeBlack",  (0.04, 0.04, 0.05, 1.0))
    folder     = _solid_mat("Folder",    (0.78, 0.66, 0.42, 1.0))   # carpeta manila
    stamp      = _solid_mat("Stamp",     (0.70, 0.10, 0.10, 1.0))   # sello "MERCENARIO"

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

    def _cyl(name, loc, radius, depth, mat, bone, *, rot=None):
        bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=radius, depth=depth, location=loc)
        obj = bpy.context.object
        obj.name = name
        if rot:
            obj.rotation_euler = rot
            bpy.ops.object.transform_apply(rotation=True)
        obj.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        parts.append((obj, bone))
        return obj

    # Torso: bloque rechoncho con traje gris + camisa/pechera clara al frente
    _sphere("Mesh_Torso", (0, 0, 0.72), 0.34, suit, "Body", scale=(1.15, 0.95, 1.25))
    _sphere("Mesh_Shirt", (0, -0.18, 0.74), 0.20, shirt, "Body", scale=(0.7, 0.55, 1.1))
    _cube("Mesh_Tie", (0, -0.28, 0.66), (0.10, 0.04, 0.34), tie, "Body")

    # Cabeza grande y cuadrada (bulldog)
    _sphere("Mesh_Head", (0, 0, 1.18), 0.30, fur, "Head", scale=(1.15, 1.05, 0.95))
    # Ceño/frente pesada (la marca del personaje: siempre enfadado)
    _cube("Mesh_Brow", (0, -0.26, 1.27), (0.46, 0.14, 0.10), fur, "Head", rot=(math.radians(8), 0, 0))
    # Papada / cachetes colgantes
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Jowl_{side}", (sign * 0.20, -0.16, 1.02), 0.15, fur_light, "Head",
                scale=(0.9, 1.0, 1.2), segs=14, rings=10)

    # Hocico fijo a la cabeza (mandíbula superior) + nariz negra
    _cube("Mesh_Snout", (0, -0.30, 1.12), (0.34, 0.26, 0.16), fur_light, "Head")
    _sphere("Mesh_Nose", (0, -0.44, 1.17), 0.06, nose_mat, "Head", scale=(1.3, 0.9, 0.8), segs=12, rings=8)

    # Mandíbula inferior (se abre con el hueso Jaw) + colmillos
    _cube("Mesh_LowerJaw", (0, -0.28, 1.02), (0.32, 0.24, 0.10), fur_light, "Jaw")
    for side, sign in (("L", -1), ("R", 1)):
        _cube(f"Mesh_Tooth_{side}", (sign * 0.10, -0.36, 1.07), (0.05, 0.05, 0.09), teeth, "Jaw")

    # Orejas dobladas
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Ear_{side}", (sign * 0.30, 0.04, 1.30), 0.10, fur, "Head",
                scale=(0.6, 0.9, 1.3), segs=12, rings=8)

    # Ojos: blanco + pupila, atados a su hueso para parpadear
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Eye_{side}", (sign * 0.13, -0.20, 1.22), 0.07, eye_white, f"Eye.{side}", segs=14, rings=10)
        _sphere(f"Mesh_Pupil_{side}", (sign * 0.13, -0.265, 1.22), 0.030, eye_black, f"Eye.{side}", segs=10, rings=8)

    # Brazos (mangas grises) + manos
    for side, sign in (("L", -1), ("R", 1)):
        _cyl(f"Mesh_Arm_{side}", (sign * 0.45, 0, 0.80), 0.09, 0.42, suit, f"Arm.{side}",
             rot=(0, math.radians(sign * 38), 0))
        _sphere(f"Mesh_Hand_{side}", (sign * 0.58, 0, 0.64), 0.10, fur, f"Arm.{side}", segs=12, rings=8)

    # Piernas (pantalón gris) + pies
    for side, sign in (("L", -1), ("R", 1)):
        _cyl(f"Mesh_Leg_{side}", (sign * 0.16, 0, 0.27), 0.10, 0.46, suit, f"Leg.{side}")
        _sphere(f"Mesh_Foot_{side}", (sign * 0.16, -0.08, 0.05), 0.11, fur, f"Leg.{side}",
                scale=(1.0, 1.5, 0.5), segs=10, rings=8)

    # Colita
    _sphere("Mesh_Tail", (0, 0.30, 0.60), 0.06, fur, "Tail", scale=(1.0, 1.6, 1.0), segs=10, rings=8)

    # Carpeta secreta bajo el brazo derecho (se mueve con el brazo) + sello rojo
    _cube("Mesh_Folder", (0.58, 0.02, 0.66), (0.30, 0.36, 0.04), folder, "Arm.R",
          rot=(0, 0, math.radians(8)))
    _cube("Mesh_Stamp", (0.58, -0.18, 0.70), (0.14, 0.01, 0.08), stamp, "Arm.R")

    # Bind: cada parte 100% a su hueso vía vertex group explícito
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
    """Parpadeo: aplastar los ojos (scale Y) durante ~3 frames."""
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

    # Respiración pesada del torso + leve balanceo de cabeza
    fc = _fcurve(action, 'pose.bones["Body"].location', 2)
    _add_keyframes(fc, [(1, 0), (20, 0.02), (40, 0), (60, 0.015), (75, 0)])
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 1)
    _add_keyframes(fc, [(1, 0), (25, math.radians(4)), (50, math.radians(-4)), (75, 0)])
    # Mandíbula apenas entreabierta (jadeo de bulldog)
    fc = _fcurve(action, 'pose.bones["Jaw"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (15, math.radians(10)), (30, 0), (45, math.radians(10)), (60, 0)])

    _add_blinks(action, [18, 52])
    return action


def add_talk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """Difamación televisiva: la mandíbula ladra, la cabeza embiste, el brazo
    de la carpeta sube acusador."""
    action = bpy.data.actions.new(name="Talk")
    arm_obj.animation_data.action = action

    # Mandíbula abre/cierra en ciclos (4 "ladridos" en 48 frames)
    jaw_keys: list[tuple[float, float]] = []
    for cycle in range(4):
        start = 1 + cycle * 12
        jaw_keys += [(start, 0.0), (start + 4, math.radians(35)), (start + 9, math.radians(6))]
    jaw_keys.append((48, 0.0))
    fc = _fcurve(action, 'pose.bones["Jaw"].rotation_euler', 0)
    _add_keyframes(fc, jaw_keys)

    # Cabeza embiste hacia delante al acusar
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (12, math.radians(8)), (24, math.radians(-2)), (36, math.radians(8)), (48, 0)])

    # Brazo derecho (la carpeta) sube acusador
    fc = _fcurve(action, 'pose.bones["Arm.R"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (10, math.radians(-45)), (24, math.radians(-20)), (38, math.radians(-50)), (48, 0)])
    # Brazo izquierdo gesticula
    fc = _fcurve(action, 'pose.bones["Arm.L"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (16, math.radians(-25)), (32, math.radians(-8)), (48, 0)])

    _add_blinks(action, [10, 34])
    return action


def add_walk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """Caminar pesado de bulldog: balanceo lateral con pisotones."""
    action = bpy.data.actions.new(name="Walk")
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Body"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(8)), (8, math.radians(-8)), (16, math.radians(8)),
                        (24, math.radians(-8)), (32, math.radians(8))])
    fc = _fcurve(action, 'pose.bones["Root"].location', 2)
    _add_keyframes(fc, [(1, 0), (8, 0.04), (16, 0), (24, 0.04), (32, 0)])
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(-5)), (16, math.radians(5)), (32, math.radians(-5))])
    fc = _fcurve(action, 'pose.bones["Tail"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (16, math.radians(20)), (32, 0)])
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
