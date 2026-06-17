from __future__ import annotations
import bpy
from mathutils import Vector
from .core import slug
from .assets import import_glb
from .materials import emission_material, create_material

def create_subject(spec: dict, asset_refs: dict) -> bpy.types.Object:
    character = asset_refs.get("character")
    if character:
        print(f"Using character asset: {character['id']} ({character['source']})")
        if character.get("path"):
            imported = import_glb(character["path"], label="character")
            if imported is not None:
                imported.name = f"subject_{slug(spec['subject'])}"
                imported.location = (0, 0, 0)
                normalize_subject(imported)
                print(f"  Imported character from: {character['path']}")
                return imported
            print(f"  Import failed, falling back to procedural character.")

    subject_name = spec["subject"].lower()
    if character or "character" in subject_name or "hero" in subject_name or "humano" in subject_name:
        subject = create_humanoid_proxy(spec)
    elif "vehicle" in subject_name:
        subject = create_vehicle_proxy(spec)
    else:
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 1))
        subject = bpy.context.object
    subject.name = f"subject_{slug(spec['subject'])}"

    if not subject.data.materials:
        subject.data.materials.append(emission_material("subject_neon_material", (0.1, 0.8, 1.0, 1.0), 0.5))
    return subject

def subject_bounds(subject: bpy.types.Object) -> tuple[float, float]:
    meshes = [o for o in [subject, *subject.children_recursive] if o.type == "MESH"]
    if not meshes:
        return subject.location.z, 1.7
    zs = [
        (obj.matrix_world @ Vector(corner)).z
        for obj in meshes
        for corner in obj.bound_box
    ]
    return min(zs), max(zs) - min(zs)

def normalize_subject(subject: bpy.types.Object, *, target_height: float = 1.7) -> None:
    min_z, height = subject_bounds(subject)
    if height > 0 and not (1.2 <= height <= 2.5):
        factor = target_height / height
        subject.scale = tuple(s * factor for s in subject.scale)
        bpy.context.view_layer.update()
        min_z, height = subject_bounds(subject)
        print(f"  Normalized subject scale by {factor:.3f} (height {height:.2f}m)")
    if abs(min_z) > 1e-4:
        subject.location.z -= min_z
        bpy.context.view_layer.update()
        print(f"  Grounded subject (was floating at z={min_z:.3f})")

def subject_height(subject: bpy.types.Object) -> float:
    _, height = subject_bounds(subject)
    return height if height > 0 else 1.7

def create_humanoid_proxy(spec: dict) -> bpy.types.Object:
    body_material = emission_material("hero_body_material", (0.1, 0.8, 1.0, 1.0), 0.35)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.0))
    body = bpy.context.object
    body.name = "humanoid_body"
    body.dimensions = (0.7, 0.35, 1.35)
    body.data.materials.append(body_material)

    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.32, location=(0, 0, 1.85))
    head = bpy.context.object
    head.name = "humanoid_head"
    head.data.materials.append(body_material)
    head.parent = body
    return body

def create_vehicle_proxy(spec: dict) -> bpy.types.Object:
    material = create_material("vehicle_material", (0.05, 0.08, 0.10, 1.0))
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.45))
    vehicle = bpy.context.object
    vehicle.name = "vehicle_body"
    vehicle.dimensions = (2.3, 1.1, 0.55)
    vehicle.data.materials.append(material)
    return vehicle
