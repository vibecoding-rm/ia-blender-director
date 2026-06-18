"""
Blender headless script — construye "El Guerrero de Lata": una armadura HUECA
(caballero de lata) con voz distorsionada, espada-antena WiFi y escudo de
"fuente anónima". Nadie ve quién está dentro: solo cables y un teléfono.
GLB riggeado con acciones NLA Idle / Talk / Walk.

La visera inferior es el hueso `Jaw` (rotación X = abrir) para lip-sync.

Uso:
    blender --background --python scripts/blender/export_guerrero.py

Salida:
    assets/characters/guerrero_v1/guerrero_v1.glb
"""

import math
from pathlib import Path

import bpy
import mathutils

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "assets" / "characters" / "guerrero_v1" / "guerrero_v1.glb"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# (name, head, tail, parent)
_BONES: list[tuple[str, tuple, tuple, str | None]] = [
    ("Root",   (0, 0, 0),          (0, 0, 0.1),        None),
    ("Body",   (0, 0, 0.45),       (0, 0, 1.00),       "Root"),
    ("Head",   (0, 0, 1.00),       (0, 0, 1.35),       "Body"),
    ("Jaw",    (0, -0.10, 1.08),   (0, -0.22, 1.04),   "Head"),
    ("Arm.L",  (-0.34, 0, 0.92),   (-0.55, 0, 0.60),   "Body"),
    ("Arm.R",  (0.34, 0, 0.92),    (0.55, 0, 0.60),    "Body"),
    ("Leg.L",  (-0.16, 0, 0.45),   (-0.16, 0, 0.04),   "Root"),
    ("Leg.R",  (0.16, 0, 0.45),    (0.16, 0, 0.04),    "Root"),
    ("Eye.L",  (-0.07, -0.18, 1.16), (-0.07, -0.18, 1.20), "Head"),
    ("Eye.R",  (0.07, -0.18, 1.16),  (0.07, -0.18, 1.20),  "Head"),
]


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.actions, bpy.data.armatures, bpy.data.meshes, bpy.data.materials):
        for block in list(collection):
            collection.remove(block)


def _solid_mat(name: str, rgba: tuple, *, metallic: float = 0.0, emission: float = 0.0) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.45 if metallic else 0.8
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metallic
    if emission > 0.0 and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = rgba
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def build_armature() -> bpy.types.Object:
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm_obj = bpy.context.object
    arm_obj.name = "Guerrero_Armature"
    arm_obj.data.name = "Guerrero_Rig"

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
    """Caballero hueco de lata: casco con visera, peto, cables y teléfono al
    cuello, espada-antena WiFi y escudo de 'fuente anónima'."""
    tin       = _solid_mat("Tin",      (0.50, 0.52, 0.56, 1.0), metallic=0.7)
    tin_dark  = _solid_mat("TinDark",  (0.30, 0.31, 0.34, 1.0), metallic=0.6)
    visor     = _solid_mat("Visor",    (0.03, 0.03, 0.04, 1.0))
    eye_glow  = _solid_mat("EyeGlow",  (0.90, 0.10, 0.10, 1.0), emission=3.0)
    emblem    = _solid_mat("Emblem",   (0.80, 0.66, 0.12, 1.0))   # escudo "fuente anónima"
    antenna   = _solid_mat("Antenna",  (0.10, 0.10, 0.12, 1.0))
    signal    = _solid_mat("Signal",   (0.30, 0.62, 1.0, 1.0), emission=2.5)
    phone     = _solid_mat("Phone",    (0.05, 0.05, 0.06, 1.0))
    cable     = _solid_mat("Cable",    (0.16, 0.16, 0.18, 1.0))

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

    def _cyl(name, loc, radius, depth, mat, bone, *, rot=None, verts=16):
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

    # Peto (torso) metálico hueco
    _sphere("Mesh_Breastplate", (0, 0, 0.72), 0.32, tin, "Body", scale=(1.1, 0.85, 1.25))
    # Hueco del cuello (oscuro) + cables + teléfono institucional asomando
    _cyl("Mesh_NeckGap", (0, 0, 0.99), 0.12, 0.10, visor, "Body", verts=14)
    for i, (dx, rotz) in enumerate([(-0.04, 20), (0.03, -15), (0.06, 35)]):
        _cyl(f"Mesh_Cable_{i}", (dx, -0.02, 1.02), 0.012, 0.12, cable, "Body",
             rot=(math.radians(20), 0, math.radians(rotz)))
    _cube("Mesh_Phone", (0.05, -0.04, 0.96), (0.07, 0.02, 0.12), phone, "Body", rot=(math.radians(12), 0, 0))

    # Casco (yelmo) hueco + visera oscura + visera inferior (Jaw)
    _sphere("Mesh_Helmet", (0, 0, 1.20), 0.21, tin, "Head", scale=(1.0, 1.05, 1.1))
    _cube("Mesh_HelmetCrest", (0, 0.02, 1.36), (0.04, 0.18, 0.10), tin_dark, "Head")
    _cube("Mesh_VisorSlit", (0, -0.18, 1.17), (0.30, 0.10, 0.05), visor, "Head")
    _cube("Mesh_VisorLower", (0, -0.17, 1.07), (0.28, 0.12, 0.07), tin, "Jaw")

    # Ojos: dos puntos rojos en la ranura (lo único que se ve "dentro")
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Eye_{side}", (sign * 0.07, -0.20, 1.17), 0.025, eye_glow, f"Eye.{side}", segs=10, rings=6)

    # Hombreras + brazos + guanteletes
    for side, sign in (("L", -1), ("R", 1)):
        _sphere(f"Mesh_Pauldron_{side}", (sign * 0.34, 0, 0.95), 0.13, tin, f"Arm.{side}", segs=12, rings=8)
        _cyl(f"Mesh_Arm_{side}", (sign * 0.47, 0, 0.74), 0.08, 0.40, tin_dark, f"Arm.{side}",
             rot=(0, math.radians(sign * 35), 0))
        _sphere(f"Mesh_Gauntlet_{side}", (sign * 0.55, 0, 0.58), 0.09, tin, f"Arm.{side}", segs=10, rings=8)

    # Piernas (grebas) + sabatones
    for side, sign in (("L", -1), ("R", 1)):
        _cyl(f"Mesh_Leg_{side}", (sign * 0.16, 0, 0.26), 0.10, 0.42, tin_dark, f"Leg.{side}")
        _sphere(f"Mesh_Foot_{side}", (sign * 0.16, -0.08, 0.04), 0.11, tin, f"Leg.{side}",
                scale=(1.0, 1.6, 0.5), segs=10, rings=8)

    # Espada = antena WiFi (mango + asta + router con arcos de señal), en la mano derecha
    _cube("Mesh_SwordHilt", (0.58, 0, 0.56), (0.05, 0.05, 0.12), tin, "Arm.R")
    _cyl("Mesh_SwordBlade", (0.58, 0, 0.92), 0.018, 0.55, antenna, "Arm.R")
    _cube("Mesh_Router", (0.58, 0, 1.18), (0.12, 0.06, 0.06), antenna, "Arm.R")
    for i, dz in enumerate((0.06, 0.10)):
        _cyl(f"Mesh_Signal_{i}", (0.58, 0, 1.20 + dz), 0.04 + i * 0.03, 0.012, signal, "Arm.R",
             rot=(math.radians(90), 0, 0), verts=14)

    # Escudo con emblema de "FUENTE ANÓNIMA" (mano izquierda)
    _cyl("Mesh_Shield", (-0.58, -0.10, 0.70), 0.20, 0.05, tin, "Arm.L", rot=(math.radians(90), 0, 0), verts=20)
    _cube("Mesh_ShieldEmblem", (-0.58, -0.14, 0.70), (0.12, 0.02, 0.12), emblem, "Arm.L")
    _cube("Mesh_EmblemMark", (-0.58, -0.16, 0.70), (0.03, 0.01, 0.09), tin_dark, "Arm.L")

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


def _add_eye_flicker(action: bpy.types.Action, frames: list[int]) -> None:
    """Los ojos rojos parpadean como LED (scale Y a casi cero)."""
    for side in ("L", "R"):
        keys: list[tuple[float, float]] = [(1, 1.0)]
        for frame in frames:
            keys += [(frame - 1, 1.0), (frame, 0.15), (frame + 1, 1.0)]
        fc = _fcurve(action, f'pose.bones["Eye.{side}"].scale', 1)
        _add_keyframes(fc, keys, interp="LINEAR")


def add_idle_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    action = bpy.data.actions.new(name="Idle")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action

    # Balanceo metálico pesado + cabeza que escanea + LED parpadeante
    fc = _fcurve(action, 'pose.bones["Body"].rotation_euler', 1)
    _add_keyframes(fc, [(1, 0), (25, math.radians(2)), (50, math.radians(-2)), (75, 0)])
    fc = _fcurve(action, 'pose.bones["Head"].rotation_euler', 2)
    _add_keyframes(fc, [(1, 0), (30, math.radians(12)), (60, math.radians(-12)), (75, 0)])
    _add_eye_flicker(action, [20, 45, 68])
    return action


def add_talk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """Amenaza anónima: la visera castañetea, el cuerpo embiste, la espada-antena sube."""
    action = bpy.data.actions.new(name="Talk")
    arm_obj.animation_data.action = action

    jaw_keys: list[tuple[float, float]] = []
    for cycle in range(5):
        start = 1 + cycle * 9
        jaw_keys += [(start, 0.0), (start + 3, math.radians(28)), (start + 7, math.radians(5))]
    jaw_keys.append((48, 0.0))
    fc = _fcurve(action, 'pose.bones["Jaw"].rotation_euler', 0)
    _add_keyframes(fc, jaw_keys)

    fc = _fcurve(action, 'pose.bones["Body"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (16, math.radians(6)), (32, math.radians(-2)), (48, math.radians(6))])
    # Espada-antena se alza amenazante
    fc = _fcurve(action, 'pose.bones["Arm.R"].rotation_euler', 0)
    _add_keyframes(fc, [(1, 0), (14, math.radians(-55)), (30, math.radians(-30)), (48, math.radians(-55))])
    _add_eye_flicker(action, [8, 22, 40])
    return action


def add_walk_action(arm_obj: bpy.types.Object) -> bpy.types.Action:
    """Marcha pesada que retumba: balanceo de armadura y brazos rígidos."""
    action = bpy.data.actions.new(name="Walk")
    arm_obj.animation_data.action = action

    fc = _fcurve(action, 'pose.bones["Body"].rotation_euler', 1)
    _add_keyframes(fc, [(1, math.radians(5)), (8, math.radians(-5)), (16, math.radians(5)),
                        (24, math.radians(-5)), (32, math.radians(5))])
    fc = _fcurve(action, 'pose.bones["Root"].location', 2)
    _add_keyframes(fc, [(1, 0), (8, 0.05), (16, 0), (24, 0.05), (32, 0)])
    fc = _fcurve(action, 'pose.bones["Arm.L"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(-12)), (16, math.radians(12)), (32, math.radians(-12))])
    fc = _fcurve(action, 'pose.bones["Arm.R"].rotation_euler', 0)
    _add_keyframes(fc, [(1, math.radians(12)), (16, math.radians(-12)), (32, math.radians(12))])
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
