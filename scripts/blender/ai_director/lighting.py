from __future__ import annotations
import bpy

def create_lighting(spec: dict) -> None:
    lighting = spec["lighting"].lower()
    bright = any(w in lighting for w in ("bright", "studio", "broadcast", "daylight"))

    bpy.ops.object.light_add(type="AREA", location=(0, -4, 5))
    key = bpy.context.object
    key.name = "key_light"
    if bright:
        key.data.energy = 1600
    elif "neon" in lighting:
        key.data.energy = 750
    else:
        key.data.energy = 500
    key.data.size = 4
    if "sunset" in lighting:
        key.data.color = (1.0, 0.65, 0.35)
    elif "moonlight" in lighting:
        key.data.color = (0.55, 0.65, 1.0)

    bpy.ops.object.light_add(type="POINT", location=(-3, 2, 3))
    rim = bpy.context.object
    rim.name = "rim_light"
    rim.data.energy = 250
    rim.data.color = (1.0, 1.0, 1.0) if bright else (1.0, 0.1, 0.2)

    if bright:
        bpy.ops.object.light_add(type="AREA", location=(3, -3, 4))
        fill = bpy.context.object
        fill.name = "fill_light"
        fill.data.energy = 700
        fill.data.size = 5
