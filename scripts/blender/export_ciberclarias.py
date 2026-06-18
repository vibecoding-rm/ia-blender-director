"""
Blender headless script — construye una "Ciberclaria": un bagre (claria) de
fango con teléfono, ojos rojos y camiseta de uniforme. Es la UNIDAD del enjambre
de trolls oficialistas; en escena se instancia/duplica para formar el banco.

La boca es el hueso `Jaw` (rotación X = abrir) para corear consignas vía lip-sync.

Uso:
    blender --background --python scripts/blender/export_ciberclarias.py

Salida:
    assets/characters/ciberclarias_v1/ciberclarias_v1.glb
"""

import math
from pathlib import Path

import bpy
import mathutils

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "assets" / "characters" / "ciberclarias_v1" / "ciberclarias_v1.glb"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# (name, head, tail, parent)
_BONES: list[tuple[str, tuple, tuple, str | None]] = [
    ("Root",   (0, 0, 0),          (0, 0, 0.08),       None),
    ("Body",   (0, 0, 0.18),       (0, 0, 0.55),       "Root"),
    ("Head",   (0, 0, 0.55),       (0, 0, 0.82),       "Body"),
    # Boca ancha de bagre: rotar Jaw en X abre la boca para corear.
    ("Jaw",    (0, -0.08, 0.60),   (0, -0.22, 0.56),   "Head"),
    ("Fin.L",  (-0.16, 0, 0.42),   (-0.32, 0, 0.36),   "Body"),
    ("Fin.R",  (0.16, 0, 0.42),    (0.34, 0, 0.34),    "Body"),
    ("Tail",   (0, 0.14, 0.16),    (0, 0.34, 0.10),    "Root"),
    ("Eye.L",  (-0.10, -0.13, 0.74), (-0.10, -0.13, 0.80), "Head"),
    ("Eye.R",  (0.10, -0.13, 0.74),  (0.10, -0.13, 0.80),  "Head"),
]


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.actions, bpy.data.armatures, bpy.data.meshes, bpy.data.materials):
        for block in list(collection):
            collection.remove(block)


def _solid_mat(name: str, rgba: tuple, *, emission: float = 0.0) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.7
    if emission > 0.0 and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = rgba
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def build_armature() -> bpy.types.Object:
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm_obj = bpy.context.object
    arm_obj.name = "Ciberclaria_Armature"
    arm_obj.data.name = "Ciberclaria_Rig"

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
    """Bagre de fango semi-erguido con teléfono, bigotes y camiseta igual."""
    mud        = _solid_mat("Mud",       (0.29, 0.27, 0.22, 1.0))
    mud_light  = _solid_mat("MudLight",  (0.40, 0.37, 0.29, 1.0))
    shirt      = _solid_mat("Shirt",     (0.64, 0.12, 0.16, 1.0))   # uniforme
    mouth_dark = _solid_mat("MouthDark", (0.10, 0.08, 0.07, 1.0))
    eye_red    = _solid_mat("EyeRed",    (0.90, 0.06, 0.06, 1.0), emission=2.5)
    whisker    = _solid_mat("Whisker",   (0.22, 0.20, 0.16, 1.0))
    phone_body = _solid_mat("Phone",     (0.05, 0.05, 0.06, 1.0))
    phone_scr  = _solid_mat("PhoneScreen", (0.30, 0.62, 1.0, 1.0), emission=2.0)

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

    def _cyl(name, loc, radius, depth, mat, bone, *, rot=None):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=radius, depth=depth, location=loc)
        obj = bpy.context.object
        obj.name = name
        if rot:
            obj.rotation_euler = rot
            bpy.ops.object.transform_apply(rotation=True)
        obj.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        parts.append((obj, bone))
        return obj

    # Cuerpo: ellipsoide de fango (gota gorda), con camiseta de uniforme
    _sphere("Mesh_Body", (0, 0, 0.40), 0.26, mud, "Body", scale=(1.0, 0.85, 1.5))
    _cube("Mesh_Shirt", (0, -0.10, 0.34), (0.40, 0.30, 0.16), shirt, "Body")

    # Cabeza ancha y aplastada de bagre
    _sphere("Mesh_Head", (0, -0.04, 0.66), 0.20, mud_light, "Head", scale=(1.3, 1.2, 0.8))

    # Boca ancha: labio superior (Head) + mandíbula inferior (Jaw) + interior oscuro
    _cube("Mesh_LipUpper", (0, -0.18, 0.64), (0.30, 0.10, 0.05), mud_light, "Head")
    _cube("Mesh_Jaw", (0, -0.17, 0.585), (0.30, 0.12, 0.05), mud_light, "Jaw")
    _cube("Mesh_MouthInside", (0, -0.13, 0.61), (0.24, 0.06, 0.06), mouth_dark, "Jaw")

    # Bigotes (barbillas) del bagre
    for side, sign in (("L", -1), ("R", 1)):
        _cyl(f"Mesh_Whisker_{side}", (sign * 0.12, -0.20, 0.60), 0.008, 0.22, whisker, "Head",
             rot=(math.radians(70), 0, math.radians(sign * 25)))
    _cyl("Mesh_Whisker_Mid", (0, -0.24, 0.62), 0.008, 0.18, whisker, "Head", rot=(math.radians(80), 0, 0))

    # Ojos rojos saltones (emisivos)
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Eye_{side}", (sign * 0.10, -0.13, 0.74), 0.055, eye_red, f"Eye.{side}", segs=12, rings=8)

    # Aleta dorsal + aletas laterales (la derecha sostiene el teléfono)
    _cube("Mesh_DorsalFin", (0, 0.16, 0.58), (0.04, 0.18, 0.22), mud, "Body", rot=(math.radians(20), 0, 0))
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Fin_{side}", (sign * 0.26, 0.02, 0.40), 0.10, mud, f"Fin.{side}",
                scale=(1.2, 0.4, 0.9), segs=10, rings=6)

    # Cola en abanico
    _sphere("Mesh_Tail", (0, 0.30, 0.16), 0.12, mud, "Tail", scale=(0.5, 1.5, 1.1), segs=10, rings=6)

    # Teléfono en la aleta derecha (se mueve con Fin.R) + pantalla encendida
    _cube("Mesh_Phone", (0.34, -0.10, 0.40), (0.10, 0.02, 0.18), phone_body, "Fin.R")
    _cube("Mesh_PhoneScreen", (0.34, -0.115, 0.40), (0.08, 0.01, 0.15), phone_scr, "Fin.R")

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
            keys += [(frame - 2, 1.0), (frame, 0.1), (frame + 2, 1.0)]
        fc = _fcurve(action, f'pose.bones["Eye.{side}"].scale', 1)
        _add_keyframes(fc, keys)


def add_idle_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    action = bpy.data.actions.new(name="Idle")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action

    # Flotación viscosa + cola y aletas ondeando
    fc = _fcurve(action, 'pose.bones["Body"].location', 2)
    _add_keyframes(fc, [(1, 0), (20, 0.02), (40, 0), (60, 0.02), (80, 0)])
    fc = _fcurve(action, 'pose.bones["Tail"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(-12)), (20, math.radians(12)), (40, math.radians(-12)),
                        (60, math.radians(12)), (80, math.radians(-12))])
    fc = _fcurve(action, 'pose.bones["Jaw"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (40, math.radians(8)), (80, 0)])
    _add_blinks(action, [22, 60])
    return action


def add_talk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """Corea consignas: boca abre/cierra rápido (bot), levanta el teléfono."""
    action = bpy.data.actions.new(name="Talk")
    arm_obj.animation_data.action = action

    jaw_keys: list[tuple[float, float]] = []
    for cycle in range(6):  # consignas cortas y repetitivas tipo bot
        start = 1 + cycle * 8
        jaw_keys += [(start, 0.0), (start + 3, math.radians(30)), (start + 6, 0.0)]
    jaw_keys.append((48, 0.0))
    fc = _fcurve(action, 'pose.bones["Jaw"].rotation_euler', 0)
    _add_keyframes(fc, jaw_keys)

    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (12, math.radians(6)), (24, 0), (36, math.radians(6)), (48, 0)])
    # Aleta derecha levanta el teléfono (reportar)
    fc = _fcurve(action, 'pose.bones["Fin.R"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (12, math.radians(-40)), (28, math.radians(-15)), (48, math.radians(-40))])
    _add_blinks(action, [14, 38])
    return action


def add_walk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """'Nado' del enjambre: ondulación de cuerpo y cola."""
    action = bpy.data.actions.new(name="Walk")
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Body"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(-8)), (10, math.radians(8)), (20, math.radians(-8)),
                        (30, math.radians(8))])
    fc = _fcurve(action, 'pose.bones["Tail"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(20)), (10, math.radians(-20)), (20, math.radians(20)),
                        (30, math.radians(-20))])
    fc = _fcurve(action, 'pose.bones["Root"].location', 2)
    _add_keyframes(fc, [(1, 0), (10, 0.03), (20, 0), (30, 0.03)])
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
