"""
Blender headless script - exports the remaining reserve characters for
El Noticiero de La Cotorra.

Each character is an original clay-style procedural GLB with a compact rig,
embedded Idle/Talk/Walk NLA actions, eye bones, and an articulated mouth bone
(`Jaw` or `Beak`) for lip-sync.

Usage:
    blender --background --python scripts/blender/export_remaining_characters.py
"""

import math
from pathlib import Path

import bpy
import mathutils

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "assets" / "characters"


CHARACTERS = [
    {
        "id": "arleen_v1",
        "name": "Arleen Chapea",
        "kind": "jutia",
        "mouth": "Jaw",
        "body": (0.48, 0.29, 0.18, 1),
        "body2": (0.64, 0.40, 0.24, 1),
        "accent": (0.05, 0.05, 0.06, 1),
        "prop": "shears",
    },
    {
        "id": "brigada_v1",
        "name": "Brigada Copy-Paste",
        "kind": "clone",
        "mouth": "Jaw",
        "body": (0.22, 0.28, 0.32, 1),
        "body2": (0.38, 0.48, 0.52, 1),
        "accent": (0.10, 0.95, 0.45, 1),
        "prop": "keyboard",
    },
    {
        "id": "lazaro_v1",
        "name": "Lazaro Mediodia",
        "kind": "ferret",
        "mouth": "Jaw",
        "body": (0.55, 0.42, 0.30, 1),
        "body2": (0.78, 0.66, 0.48, 1),
        "accent": (0.78, 0.10, 0.12, 1),
        "prop": "mic",
    },
    {
        "id": "pupila_v1",
        "name": "Fantasma de la Pupila",
        "kind": "portrait",
        "mouth": "Jaw",
        "body": (0.42, 0.43, 0.48, 0.92),
        "body2": (0.78, 0.80, 0.86, 0.75),
        "accent": (0.34, 0.26, 0.18, 1),
        "prop": "frame",
    },
    {
        "id": "chivaton_v1",
        "name": "Gerardo el Chivaton",
        "kind": "goat",
        "mouth": "Jaw",
        "body": (0.75, 0.72, 0.65, 1),
        "body2": (0.52, 0.50, 0.44, 1),
        "accent": (0.20, 0.25, 0.12, 1),
        "prop": "binoculars",
    },
    {
        "id": "marrero_v1",
        "name": "Marrero el Conserje 5 Estrellas",
        "kind": "peacock",
        "mouth": "Beak",
        "body": (0.12, 0.44, 0.55, 1),
        "body2": (0.10, 0.25, 0.44, 1),
        "accent": (0.92, 0.72, 0.20, 1),
        "prop": "keys",
    },
    {
        "id": "bruno_v1",
        "name": "Bruno Bloqueo",
        "kind": "snake",
        "mouth": "Jaw",
        "body": (0.35, 0.42, 0.29, 1),
        "body2": (0.58, 0.67, 0.48, 1),
        "accent": (0.95, 0.95, 0.90, 1),
        "prop": "sign",
    },
    {
        "id": "trovador_v1",
        "name": "Trovador del Picadillo",
        "kind": "songbird",
        "mouth": "Beak",
        "body": (0.76, 0.58, 0.20, 1),
        "body2": (0.92, 0.76, 0.30, 1),
        "accent": (0.45, 0.22, 0.10, 1),
        "prop": "guitar",
    },
]


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.actions, bpy.data.armatures, bpy.data.meshes, bpy.data.materials):
        for block in list(collection):
            collection.remove(block)


def mat(name: str, rgba: tuple) -> bpy.types.Material:
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.82
    return material


def build_armature(char: dict) -> bpy.types.Object:
    mouth = char["mouth"]
    bones = [
        ("Root", (0, 0, 0), (0, 0, 0.1), None),
        ("Body", (0, 0, 0.34), (0, 0, 0.88), "Root"),
        ("Head", (0, 0, 0.90), (0, 0, 1.22), "Body"),
        (mouth, (0, -0.15, 1.02), (0, -0.32, 0.98), "Head"),
        ("Arm.L", (-0.25, 0, 0.72), (-0.48, -0.02, 0.52), "Body"),
        ("Arm.R", (0.25, 0, 0.72), (0.48, -0.02, 0.52), "Body"),
        ("Tail", (0, 0.22, 0.46), (0, 0.48, 0.30), "Body"),
        ("Leg.L", (-0.10, 0, 0.34), (-0.10, -0.02, 0.04), "Root"),
        ("Leg.R", (0.10, 0, 0.34), (0.10, -0.02, 0.04), "Root"),
        ("Eye.L", (-0.10, -0.14, 1.08), (-0.10, -0.14, 1.14), "Head"),
        ("Eye.R", (0.10, -0.14, 1.08), (0.10, -0.14, 1.14), "Head"),
    ]
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm_obj = bpy.context.object
    arm_obj.name = f"{char['id']}_Armature"
    arm_obj.data.name = f"{char['id']}_Rig"
    edit_bones = arm_obj.data.edit_bones
    for bone in list(edit_bones):
        edit_bones.remove(bone)
    created = {}
    for name, head, tail, parent in bones:
        eb = edit_bones.new(name)
        eb.head = mathutils.Vector(head)
        eb.tail = mathutils.Vector(tail)
        if parent:
            eb.parent = created[parent]
            eb.use_connect = False
        created[name] = eb
    bpy.ops.object.mode_set(mode="POSE")
    for pose_bone in arm_obj.pose.bones:
        pose_bone.rotation_mode = "XYZ"
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj


def build_mesh(char: dict, arm_obj: bpy.types.Object) -> list[bpy.types.Object]:
    main = mat("Main", char["body"])
    light = mat("Light", char["body2"])
    accent = mat("Accent", char["accent"])
    black = mat("Black", (0.025, 0.025, 0.03, 1))
    white = mat("White", (0.94, 0.92, 0.86, 1))
    amber = mat("Amber", (0.90, 0.64, 0.15, 1))
    beak = mat("Beak", (0.86, 0.56, 0.16, 1))
    parts: list[tuple[bpy.types.Object, str]] = []

    def sphere(name, loc, radius, material, bone, *, scale=None, segs=16, rings=10):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, radius=radius, location=loc)
        obj = bpy.context.object
        obj.name = name
        if scale:
            obj.scale = scale
            bpy.ops.object.transform_apply(scale=True)
        obj.data.materials.append(material)
        bpy.ops.object.shade_smooth()
        parts.append((obj, bone))
        return obj

    def cube(name, loc, dims, material, bone, *, rot=None):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        obj = bpy.context.object
        obj.name = name
        obj.dimensions = dims
        if rot:
            obj.rotation_euler = rot
        bpy.ops.object.transform_apply(scale=True, rotation=bool(rot))
        obj.data.materials.append(material)
        parts.append((obj, bone))
        return obj

    def cyl(name, loc, radius, depth, material, bone, *, rot=None, verts=12):
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc)
        obj = bpy.context.object
        obj.name = name
        if rot:
            obj.rotation_euler = rot
            bpy.ops.object.transform_apply(rotation=True)
        obj.data.materials.append(material)
        bpy.ops.object.shade_smooth()
        parts.append((obj, bone))
        return obj

    def cone(name, loc, radius, depth, material, bone, *, rot=None, verts=12):
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=radius, radius2=0.006, depth=depth, location=loc)
        obj = bpy.context.object
        obj.name = name
        if rot:
            obj.rotation_euler = rot
            bpy.ops.object.transform_apply(rotation=True)
        obj.data.materials.append(material)
        bpy.ops.object.shade_smooth()
        parts.append((obj, bone))
        return obj

    kind = char["kind"]
    mouth = char["mouth"]
    body_scale = (0.95, 0.85, 1.25)
    if kind in {"snake", "portrait"}:
        body_scale = (0.72, 0.62, 1.55)
    if kind == "peacock":
        body_scale = (0.85, 0.78, 1.35)

    sphere("Mesh_Body", (0, 0, 0.58), 0.30, main, "Body", scale=body_scale)
    sphere("Mesh_Belly", (0, -0.15, 0.56), 0.17, light, "Body", scale=(0.75, 0.42, 1.0))
    sphere("Mesh_Head", (0, -0.02, 1.04), 0.21, light, "Head")

    if mouth == "Beak":
        cone("Mesh_BeakUpper", (0, -0.25, 1.04), 0.055, 0.15, beak, "Head", rot=(math.radians(-90), 0, 0))
        cone("Mesh_BeakLower", (0, -0.22, 0.99), 0.040, 0.10, beak, mouth, rot=(math.radians(-96), 0, 0))
    else:
        sphere("Mesh_Snout", (0, -0.22, 1.00), 0.080, light, "Head", scale=(1.2, 1.45, 0.55))
        sphere("Mesh_Jaw", (0, -0.21, 0.94), 0.075, light, mouth, scale=(1.1, 1.25, 0.42))

    for side, sign in (("L", -1), ("R", 1)):
        eye_mat = amber if kind in {"peacock", "songbird"} else white
        sphere(f"Mesh_Eye_{side}", (sign * 0.10, -0.15, 1.08), 0.055, eye_mat, f"Eye.{side}")
        sphere(f"Mesh_Pupil_{side}", (sign * 0.10, -0.195, 1.08), 0.022, black, f"Eye.{side}", segs=8, rings=6)
        sphere(f"Mesh_Arm_{side}", (sign * 0.31, -0.01, 0.62), 0.13, main, f"Arm.{side}", scale=(0.45, 0.72, 1.05))
        sphere(f"Mesh_Leg_{side}", (sign * 0.10, -0.01, 0.18), 0.055, accent, f"Leg.{side}", scale=(0.75, 0.75, 1.55))
        sphere(f"Mesh_Foot_{side}", (sign * 0.11, -0.08, 0.035), 0.055, accent, f"Leg.{side}", scale=(1.25, 1.65, 0.45))

    # Distinct silhouettes and props.
    if kind == "jutia":
        for side, sign in (("L", -1), ("R", 1)):
            sphere(f"Mesh_Ear_{side}", (sign * 0.14, 0.00, 1.18), 0.055, main, "Head", scale=(0.75, 0.45, 1.0))
        cyl("Mesh_ShearsHandle", (0.42, -0.18, 0.58), 0.035, 0.035, black, "Arm.R", rot=(math.radians(90), 0, 0))
        cube("Mesh_ShearsBlade", (0.48, -0.22, 0.64), (0.02, 0.035, 0.16), accent, "Arm.R", rot=(0, 0, math.radians(35)))
    elif kind == "clone":
        cube("Mesh_Keyboard", (0, -0.34, 0.43), (0.44, 0.08, 0.11), black, "Body")
        for i in range(5):
            cube(f"Mesh_Key_{i}", (-0.16 + i * 0.08, -0.39, 0.48), (0.035, 0.02, 0.018), accent, "Body")
        cube("Mesh_CopyBadge", (0, -0.27, 0.78), (0.22, 0.025, 0.08), accent, "Body")
    elif kind == "ferret":
        sphere("Mesh_LongBody", (0, 0.05, 0.54), 0.22, main, "Body", scale=(0.72, 1.55, 0.80))
        cyl("Mesh_Microphone", (0.38, -0.16, 0.58), 0.035, 0.20, black, "Arm.R", rot=(0, math.radians(35), 0))
        cube("Mesh_Tie", (0, -0.24, 0.63), (0.065, 0.025, 0.28), accent, "Body")
    elif kind == "portrait":
        cube("Mesh_Frame", (0, 0.02, 0.78), (0.70, 0.06, 0.92), accent, "Body")
        cube("Mesh_Canvas", (0, -0.02, 0.80), (0.54, 0.035, 0.70), light, "Body")
        sphere("Mesh_GhostGlow", (0, -0.10, 1.07), 0.24, main, "Head", scale=(1.1, 0.55, 1.1))
    elif kind == "goat":
        for side, sign in (("L", -1), ("R", 1)):
            cone(f"Mesh_Horn_{side}", (sign * 0.10, 0.03, 1.25), 0.035, 0.18, accent, "Head", rot=(math.radians(-20), 0, math.radians(sign * 20)))
        cyl("Mesh_Binoculars_L", (-0.06, -0.24, 1.08), 0.045, 0.07, black, "Head", rot=(math.radians(90), 0, 0))
        cyl("Mesh_Binoculars_R", (0.06, -0.24, 1.08), 0.045, 0.07, black, "Head", rot=(math.radians(90), 0, 0))
        cube("Mesh_Notebook", (0.38, -0.16, 0.55), (0.12, 0.025, 0.16), white, "Arm.R")
    elif kind == "peacock":
        for i, x in enumerate([-0.24, -0.12, 0, 0.12, 0.24]):
            sphere(f"Mesh_TailFan_{i}", (x, 0.36, 0.73 - abs(x) * 0.8), 0.16, light, "Tail", scale=(0.55, 1.35, 0.32))
            sphere(f"Mesh_TailEye_{i}", (x, 0.25, 0.75 - abs(x) * 0.8), 0.045, accent, "Tail", scale=(1.0, 0.35, 1.0))
        cyl("Mesh_KeyRing", (0.39, -0.17, 0.50), 0.045, 0.012, accent, "Arm.R", rot=(math.radians(90), 0, 0))
    elif kind == "snake":
        for i, y in enumerate([0.12, 0.30, 0.48, 0.66]):
            sphere(f"Mesh_Coil_{i}", (0, y, 0.28 + i * 0.04), 0.18, main, "Tail", scale=(1.25, 0.65, 0.45))
        cube("Mesh_BloqueoSign", (0, -0.34, 0.58), (0.42, 0.035, 0.18), white, "Arm.R")
        cube("Mesh_BloqueoLine", (0, -0.37, 0.58), (0.30, 0.010, 0.035), accent, "Arm.R")
    elif kind == "songbird":
        cube("Mesh_GuitarBody", (0.32, -0.20, 0.55), (0.16, 0.05, 0.22), accent, "Arm.R")
        cyl("Mesh_GuitarNeck", (0.18, -0.20, 0.65), 0.015, 0.28, accent, "Arm.R", rot=(0, math.radians(55), 0))
        for x in [-0.10, 0, 0.10]:
            sphere(f"Mesh_Chorus_{x}", (x, 0.36, 0.42), 0.055, light, "Tail")

    if kind not in {"peacock", "portrait", "snake"}:
        sphere("Mesh_Tail", (0, 0.34, 0.36), 0.11, main, "Tail", scale=(0.65, 1.6, 0.55))

    objs = []
    for obj, bone in parts:
        obj.parent = arm_obj
        group = obj.vertex_groups.new(name=bone)
        group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
        modifier = obj.modifiers.new("Armature", "ARMATURE")
        modifier.object = arm_obj
        objs.append(obj)
    return objs


def fcurve(action: bpy.types.Action, data_path: str, index: int) -> bpy.types.FCurve:
    return action.fcurves.new(data_path=data_path, index=index, action_group="Keys")


def keys(fc: bpy.types.FCurve, values: list[tuple[float, float]], interp: str = "BEZIER") -> None:
    fc.keyframe_points.add(len(values))
    for i, (frame, value) in enumerate(values):
        fc.keyframe_points[i].co = (frame, value)
        fc.keyframe_points[i].interpolation = interp


def blink(action: bpy.types.Action) -> None:
    for side in ("L", "R"):
        fc = fcurve(action, f'pose.bones["Eye.{side}"].scale', 1)
        keys(fc, [(1, 1), (18, 1), (20, 0.08), (22, 1), (48, 1), (50, 0.08), (52, 1), (70, 1)])


def add_actions(char: dict, arm_obj: bpy.types.Object) -> None:
    mouth = char["mouth"]

    idle = bpy.data.actions.new(name="Idle")
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = idle
    keys(fcurve(idle, 'pose.bones["Body"].location', 2), [(1, 0), (24, 0.012), (48, 0), (72, 0.010), (84, 0)])
    keys(fcurve(idle, 'pose.bones["Head"].rotation_euler', 2), [(1, 0), (28, math.radians(5)), (58, math.radians(-4)), (84, 0)])
    blink(idle)
    push_action_to_nla(arm_obj, idle)

    talk = bpy.data.actions.new(name="Talk")
    arm_obj.animation_data.action = talk
    mouth_keys = []
    for cycle in range(4):
        start = 1 + cycle * 12
        mouth_keys += [(start, 0.0), (start + 4, math.radians(30)), (start + 9, math.radians(6))]
    mouth_keys.append((48, 0.0))
    keys(fcurve(talk, f'pose.bones["{mouth}"].rotation_euler', 0), mouth_keys)
    keys(fcurve(talk, 'pose.bones["Head"].rotation_euler', 0), [(1, 0), (14, math.radians(4)), (28, math.radians(-3)), (48, 0)])
    keys(fcurve(talk, 'pose.bones["Arm.R"].rotation_euler', 1), [(1, 0), (16, math.radians(28)), (34, math.radians(18)), (48, 0)])
    blink(talk)
    push_action_to_nla(arm_obj, talk)

    walk = bpy.data.actions.new(name="Walk")
    arm_obj.animation_data.action = walk
    keys(fcurve(walk, 'pose.bones["Root"].location', 1), [(1, 0), (32, 0.35)], "LINEAR")
    keys(fcurve(walk, 'pose.bones["Body"].rotation_euler', 2), [(1, math.radians(-4)), (16, math.radians(4)), (32, math.radians(-4))])
    keys(fcurve(walk, 'pose.bones["Tail"].rotation_euler', 2), [(1, math.radians(-6)), (16, math.radians(6)), (32, math.radians(-6))])
    push_action_to_nla(arm_obj, walk)

    arm_obj.animation_data.action = None


def push_action_to_nla(arm_obj: bpy.types.Object, action: bpy.types.Action) -> None:
    track = arm_obj.animation_data.nla_tracks.new()
    track.name = f"{action.name}_Track"
    strip = track.strips.new(name=action.name, start=1, action=action)
    strip.repeat = 1


def export_one(char: dict) -> None:
    clear_scene()
    arm_obj = build_armature(char)
    mesh_parts = build_mesh(char, arm_obj)
    add_actions(char, arm_obj)

    out_path = OUT_ROOT / char["id"] / f"{char['id']}.glb"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    for part in mesh_parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.export_scene.gltf(
        filepath=str(out_path),
        use_selection=True,
        export_format="GLB",
        export_animations=True,
        export_nla_strips=True,
        export_skins=True,
        export_apply=False,
    )
    print(f"Exported: {out_path}")


def main() -> None:
    for char in CHARACTERS:
        export_one(char)
    print("Done.")


if __name__ == "__main__":
    main()
