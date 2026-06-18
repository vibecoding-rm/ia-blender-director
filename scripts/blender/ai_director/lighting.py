from __future__ import annotations
import bpy

def create_lighting(spec: dict) -> None:
    lighting = spec["lighting"].lower()
    bright = any(w in lighting for w in ("bright", "studio", "broadcast", "daylight"))
    configure_world_fill(lighting, bright)

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

def configure_world_fill(lighting: str, bright: bool) -> None:
    world = bpy.context.scene.world or bpy.data.worlds.new("director_world")
    bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    background = nodes.get("Background")
    if background is None:
        return
    if "neon" in lighting:
        background.inputs["Color"].default_value = (0.035, 0.045, 0.08, 1.0)
        background.inputs["Strength"].default_value = 0.28
    elif bright:
        background.inputs["Color"].default_value = (0.72, 0.78, 0.9, 1.0)
        background.inputs["Strength"].default_value = 0.45
    elif "moonlight" in lighting:
        background.inputs["Color"].default_value = (0.28, 0.34, 0.55, 1.0)
        background.inputs["Strength"].default_value = 0.25
    else:
        background.inputs["Color"].default_value = (0.18, 0.2, 0.24, 1.0)
        background.inputs["Strength"].default_value = 0.32
