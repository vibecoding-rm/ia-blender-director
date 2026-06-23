"""
Render a quick character contact sheet for visual QA.

Usage:
    blender --background --python scripts/blender/render_character_contact_sheet.py

Output:
    renders/contact_sheet/characters.png
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "characters"
OUT = ROOT / "renders" / "contact_sheet" / "characters.png"


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def import_character(manifest: Path, index: int, columns: int = 5) -> None:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    raw_path = data.get("path")
    if not raw_path:
        return
    glb = manifest.parent / raw_path
    if not glb.exists():
        return

    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    new_objects = [obj for obj in bpy.context.scene.objects if obj not in before]
    if not new_objects:
        return

    col = index % columns
    row = index // columns
    x = (col - (columns - 1) / 2) * 2.3
    y = row * -2.1

    roots = [obj for obj in new_objects if obj.parent is None or obj.parent not in new_objects]
    for root in roots:
        root.location.x += x
        root.location.y += y
        root.rotation_euler[2] = math.radians(0)

    bpy.ops.object.text_add(location=(x - 0.7, y - 0.75, 0.05), rotation=(math.radians(75), 0, 0))
    label = bpy.context.object
    label.name = f"Label_{data['id']}"
    label.data.body = data["id"]
    label.data.align_x = "CENTER"
    label.data.size = 0.16


def setup_scene(count: int, columns: int = 5) -> None:
    rows = max(1, math.ceil(count / columns))
    bpy.ops.object.light_add(type="AREA", location=(0, -3, 6))
    light = bpy.context.object
    light.name = "ContactSheet_Key"
    light.data.energy = 900
    light.data.size = 6

    bpy.ops.object.camera_add(location=(0, -8.0, 4.6), rotation=(math.radians(62), 0, 0))
    cam = bpy.context.object
    cam.name = "ContactSheet_Camera"
    cam.data.lens = 22
    bpy.context.scene.camera = cam

    bpy.context.scene.render.resolution_x = 1800
    bpy.context.scene.render.resolution_y = max(1100, rows * 420)
    bpy.context.scene.eevee.taa_render_samples = 32
    bpy.context.scene.view_settings.view_transform = "Standard"
    bpy.context.scene.render.film_transparent = False


def main() -> None:
    clear_scene()
    manifests = sorted(ASSETS.glob("*/asset.json"))
    character_manifests = [
        m for m in manifests
        if json.loads(m.read_text(encoding="utf-8")).get("type") == "character"
        and json.loads(m.read_text(encoding="utf-8")).get("path")
    ]
    for i, manifest in enumerate(character_manifests):
        import_character(manifest, i)
    setup_scene(len(character_manifests))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(OUT)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {OUT}")


if __name__ == "__main__":
    main()
