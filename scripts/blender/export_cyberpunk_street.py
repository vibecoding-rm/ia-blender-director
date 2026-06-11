"""
Blender headless script: generate a procedural cyberpunk street and export as GLB.

Run with:
    blender --background --python scripts/blender/export_cyberpunk_street.py

Output: assets/environments/cyberpunk_street_v1/cyberpunk_street_v1.glb
"""

import math
import sys
from pathlib import Path

import bpy
import mathutils

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT / "assets" / "environments" / "cyberpunk_street_v1" / "cyberpunk_street_v1.glb"


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)


def make_material(name: str, color: tuple, emission: tuple | None = None) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.8
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 8.0

    return mat


def make_wet_ground_material() -> bpy.types.Material:
    mat = bpy.data.materials.new(name="WetGround")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.05, 0.05, 0.07, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.05   # very smooth = wet
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.9
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat


def add_ground_plane() -> bpy.types.Object:
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = "Ground"
    obj.data.materials.append(make_wet_ground_material())
    return obj


def add_building(
    x: float,
    y: float,
    width: float,
    depth: float,
    height: float,
    side: str,
    index: int,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(x, y, height / 2),
    )
    obj = bpy.context.object
    obj.name = f"Building_{side}_{index}"
    obj.scale = (width, depth, height)
    bpy.ops.object.transform_apply(scale=True)

    color = (0.04 + index * 0.01, 0.04, 0.06)
    obj.data.materials.append(make_material(f"BuildingMat_{index}", color))
    return obj


def add_buildings() -> None:
    configs = [
        # (x, y, width, depth, height)
        (-7.0,  2.0, 3.0, 4.0, 12.0),
        (-8.5, -3.0, 2.5, 3.5,  8.0),
        (-6.5,  7.0, 3.5, 4.0, 16.0),
        (-7.5, -8.0, 3.0, 3.0, 10.0),
        ( 7.0,  2.0, 3.0, 4.0, 14.0),
        ( 8.5, -3.0, 2.5, 3.5,  9.0),
        ( 6.5,  7.0, 3.5, 4.0, 18.0),
        ( 7.5, -8.0, 3.0, 3.0, 11.0),
    ]
    for i, (x, y, w, d, h) in enumerate(configs):
        side = "L" if x < 0 else "R"
        add_building(x, y, w, d, h, side, i)


def add_neon_sign(
    x: float,
    y: float,
    z: float,
    width: float,
    height: float,
    color: tuple,
    name: str,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (width, 0.05, height)
    bpy.ops.object.transform_apply(scale=True)
    mat = make_material(f"NeonMat_{name}", color, emission=color)
    obj.data.materials.append(mat)
    return obj


def add_neon_lights() -> None:
    signs = [
        (-5.5,  1.5, 4.0, 1.5, 0.4, (1.0, 0.1, 0.1), "NeonRed_1"),
        (-5.5, -2.0, 5.5, 1.2, 0.3, (0.1, 0.9, 1.0), "NeonCyan_1"),
        (-5.5,  5.0, 3.5, 2.0, 0.5, (0.9, 0.1, 0.9), "NeonPurple_1"),
        ( 5.5,  1.5, 4.5, 1.5, 0.4, (0.1, 0.9, 1.0), "NeonCyan_2"),
        ( 5.5, -2.5, 3.0, 1.8, 0.3, (1.0, 0.5, 0.1), "NeonOrange_1"),
        ( 5.5,  6.0, 5.0, 1.2, 0.4, (1.0, 0.1, 0.1), "NeonRed_2"),
    ]
    for sign in signs:
        add_neon_sign(*sign)


def add_street_lamps() -> None:
    for i, y in enumerate([-6, -2, 2, 6]):
        for side_x in (-4.5, 4.5):
            # Pole
            bpy.ops.mesh.primitive_cylinder_add(
                radius=0.05, depth=5.0,
                location=(side_x, y, 2.5),
            )
            pole = bpy.context.object
            pole.name = f"LampPole_{i}_{side_x}"
            pole.data.materials.append(
                make_material(f"PoleMat_{i}", (0.1, 0.1, 0.1))
            )
            # Light head
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=0.12,
                location=(side_x, y, 5.1),
            )
            head = bpy.context.object
            head.name = f"LampHead_{i}_{side_x}"
            head.data.materials.append(
                make_material(f"LampMat_{i}", (1.0, 0.9, 0.7), emission=(1.0, 0.9, 0.7))
            )


def add_pavement_lines() -> None:
    for i in range(-4, 5):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(float(i) * 2, 0, 0.001))
        line = bpy.context.object
        line.name = f"PaveLine_{i}"
        line.scale = (0.15, 10.0, 0.002)
        bpy.ops.object.transform_apply(scale=True)
        line.data.materials.append(
            make_material(f"LineM_{i}", (0.8, 0.8, 0.8))
        )


def export_glb(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        export_apply=True,
        export_materials="EXPORT",
        export_lights=False,
    )
    print(f"Exported: {path}")


def main() -> None:
    clear_scene()
    add_ground_plane()
    add_buildings()
    add_neon_lights()
    add_street_lamps()
    add_pavement_lines()
    export_glb(OUTPUT_PATH)
    print("Done.")


if __name__ == "__main__":
    main()
