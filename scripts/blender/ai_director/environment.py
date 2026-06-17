from __future__ import annotations
import bpy
import random
import math
from .assets import import_glb
from .core import ASSETS_ROOT
from .materials import create_material, image_emission_material, emission_material

def create_environment(spec: dict, asset_refs: dict) -> None:
    environment = asset_refs.get("environment")
    if environment:
        print(f"Using environment asset: {environment['id']} ({environment['source']})")
        if environment.get("path"):
            imported = import_glb(environment["path"], label="environment")
            if imported is not None:
                print(f"  Imported environment from: {environment['path']}")
                return
            print(f"  Import failed, falling back to procedural environment.")

    scene_name = spec["scene"].lower()
    if "studio" in scene_name or "news" in scene_name:
        create_news_studio()
    elif "kitchen" in scene_name or "apartment" in scene_name:
        create_kitchen()
    elif "rally" in scene_name or "plaza" in scene_name or "havana" in scene_name:
        create_plaza_rally()
    elif "street" in scene_name or "cyberpunk" in scene_name:
        create_cyberpunk_street()
    elif "forest" in scene_name:
        create_forest()
    elif "room" in scene_name or "interior" in scene_name:
        create_room()
    elif "desert" in scene_name:
        create_desert()
    else:
        create_stage()

def create_stage() -> None:
    add_floor("stage_floor", color=(0.06, 0.06, 0.07, 1.0))

def create_cyberpunk_street() -> None:
    add_floor("wet_asphalt", color=(0.015, 0.015, 0.02, 1.0))
    for index, x in enumerate([-5, -3, 3, 5]):
        height = random.uniform(3.5, 7.0)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, random.uniform(2.5, 5.0), height / 2))
        building = bpy.context.object
        building.name = f"background_building_{index}"
        building.dimensions = (1.2, 1.2, height)
        building.data.materials.append(create_material("building_dark", (0.02, 0.025, 0.035, 1.0)))

        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 1.8, random.uniform(1.4, 3.2)))
        sign = bpy.context.object
        sign.name = f"neon_sign_{index}"
        sign.dimensions = (1.0, 0.05, 0.25)
        color = (1.0, 0.05, 0.15, 1.0) if index % 2 == 0 else (0.0, 0.7, 1.0, 1.0)
        sign.data.materials.append(emission_material(f"neon_{index}", color, 2.5))

def create_forest() -> None:
    add_floor("forest_ground", color=(0.025, 0.08, 0.035, 1.0))
    bark = create_material("tree_bark", (0.18, 0.09, 0.035, 1.0))
    leaves = create_material("tree_canopy", (0.02, 0.20, 0.06, 1.0))
    for index in range(18):
        x = random.uniform(-6, 6)
        y = random.uniform(-1, 7)
        if abs(x) < 1.2 and y < 2.5:
            continue
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.12, depth=random.uniform(2.0, 4.0), location=(x, y, 1.2))
        trunk = bpy.context.object
        trunk.name = f"tree_trunk_{index}"
        trunk.data.materials.append(bark)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.5, 0.9), location=(x, y, random.uniform(2.4, 4.2)))
        canopy = bpy.context.object
        canopy.name = f"tree_canopy_{index}"
        canopy.data.materials.append(leaves)

def create_room() -> None:
    add_floor("room_floor", color=(0.12, 0.11, 0.10, 1.0))
    wall_material = create_material("warm_wall", (0.22, 0.20, 0.18, 1.0))
    for name, location, scale in [
        ("back_wall", (0, 4, 2), (8, 0.12, 4)),
        ("left_wall", (-4, 0, 2), (0.12, 8, 4)),
        ("right_wall", (4, 0, 2), (0.12, 8, 4)),
    ]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        wall = bpy.context.object
        wall.name = name
        wall.dimensions = scale
        wall.data.materials.append(wall_material)

def create_desert() -> None:
    add_floor("desert_sand", color=(0.55, 0.40, 0.19, 1.0))
    rock_material = create_material("desert_rock", (0.24, 0.18, 0.12, 1.0))
    for index in range(8):
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=1,
            radius=random.uniform(0.25, 0.8),
            location=(random.uniform(-5, 5), random.uniform(1, 6), random.uniform(0.15, 0.45)),
        )
        rock = bpy.context.object
        rock.name = f"desert_rock_{index}"
        rock.scale.z = random.uniform(0.3, 0.7)
        rock.data.materials.append(rock_material)

def create_news_studio() -> None:
    add_floor("studio_floor", color=(0.88, 0.88, 0.90, 1.0))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 5, 2.2))
    backdrop = bpy.context.object
    backdrop.name = "news_backdrop"
    backdrop.dimensions = (14, 0.15, 5.0)
    backdrop.data.materials.append(emission_material("backdrop_blue", (0.04, 0.10, 0.42, 1.0), 0.3))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1.6, 0.52))
    desk = bpy.context.object
    desk.name = "news_desk"
    desk.dimensions = (2.8, 0.75, 1.04)
    desk.data.materials.append(create_material("desk_dark", (0.10, 0.10, 0.16, 1.0)))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1.22, 0.52))
    panel = bpy.context.object
    panel.name = "desk_panel"
    panel.dimensions = (2.75, 0.04, 1.00)
    panel.data.materials.append(emission_material("panel_cyan", (0.0, 0.55, 1.0, 1.0), 1.8))

    screens_dir = ASSETS_ROOT / "branding" / "screens"
    screen_images = ["screen_left.png", "screen_center.png", "screen_right.png"]
    for i, (sx, sz) in enumerate([(-3.2, 2.3), (0.0, 2.6), (3.2, 2.3)]):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(sx, 4.9, sz), rotation=(math.radians(90), 0, 0))
        screen = bpy.context.object
        screen.name = f"tv_screen_{i}"
        screen.scale = (1.7, 1.0, 1.0)
        image_path = screens_dir / screen_images[i]
        if image_path.exists():
            screen.data.materials.append(
                image_emission_material(f"screen_{i}", str(image_path), 1.6)
            )
        else:
            color = (1.0, 0.18, 0.06, 1.0) if i != 1 else (0.08, 0.45, 1.0, 1.0)
            screen.data.materials.append(emission_material(f"screen_{i}", color, 3.5))

    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.015, depth=0.35, location=(0.35, 1.45, 1.2))
    mic_stand = bpy.context.object
    mic_stand.name = "desk_mic_stand"
    mic_stand.rotation_euler = (math.radians(-18), 0, 0)
    mic_stand.data.materials.append(create_material("mic_dark", (0.05, 0.05, 0.06, 1.0)))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8, radius=0.045, location=(0.35, 1.40, 1.38))
    mic_head = bpy.context.object
    mic_head.name = "desk_mic_head"
    mic_head.data.materials.append(create_material("mic_foam", (0.65, 0.08, 0.10, 1.0)))

    wall_mat = create_material("studio_wall", (0.82, 0.84, 0.87, 1.0))
    for name, loc, dims in [
        ("studio_left",  (-6, 0, 2.2), (0.12, 12, 5.0)),
        ("studio_right", ( 6, 0, 2.2), (0.12, 12, 5.0)),
        ("studio_ceil",  ( 0, 0, 4.5), (12, 12, 0.12)),
    ]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        w = bpy.context.object
        w.name = name
        w.dimensions = dims
        w.data.materials.append(wall_mat)

def create_kitchen() -> None:
    add_floor("kitchen_floor", color=(0.52, 0.42, 0.32, 1.0))

    wall_mat = create_material("kitchen_wall", (0.75, 0.70, 0.62, 1.0))
    for name, loc, dims in [
        ("back_wall",  (0,  4.0, 2.0), (8.0, 0.12, 4.0)),
        ("left_wall",  (-4, 0.0, 2.0), (0.12, 8.0, 4.0)),
        ("right_wall", ( 4, 0.0, 2.0), (0.12, 8.0, 4.0)),
    ]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        w = bpy.context.object
        w.name = name
        w.dimensions = dims
        w.data.materials.append(wall_mat)

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 3.6, 0.45))
    counter = bpy.context.object
    counter.name = "kitchen_counter"
    counter.dimensions = (4.5, 0.65, 0.90)
    counter.data.materials.append(create_material("counter_mat", (0.20, 0.20, 0.22, 1.0)))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.5, 0.38))
    table = bpy.context.object
    table.name = "kitchen_table"
    table.dimensions = (1.5, 0.9, 0.76)
    table.data.materials.append(create_material("table_wood", (0.28, 0.18, 0.10, 1.0)))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(1.6, 3.3, 1.12))
    tv = bpy.context.object
    tv.name = "old_tv_casing"
    tv.dimensions = (0.48, 0.35, 0.42)
    tv.data.materials.append(create_material("tv_casing", (0.16, 0.14, 0.11, 1.0)))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(1.6, 3.14, 1.12))
    screen = bpy.context.object
    screen.name = "old_tv_screen"
    screen.dimensions = (0.40, 0.04, 0.34)
    screen.data.materials.append(emission_material("tv_glow", (0.18, 0.48, 0.90, 1.0), 2.5))

    bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4, radius=0.08, location=(0, 2, 3.6))
    bulb = bpy.context.object
    bulb.name = "ceiling_bulb"
    bulb.data.materials.append(emission_material("bulb_warm", (1.0, 0.92, 0.72, 1.0), 8.0))

def create_plaza_rally() -> None:
    add_floor("plaza_ground", color=(0.34, 0.30, 0.26, 1.0))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 7, 4.5))
    building = bpy.context.object
    building.name = "gov_facade"
    building.dimensions = (14, 2.5, 10.0)
    building.data.materials.append(create_material("facade_mat", (0.70, 0.65, 0.55, 1.0)))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 5.85, 3.8))
    poster = bpy.context.object
    poster.name = "rubio_poster"
    poster.dimensions = (3.0, 0.06, 2.2)
    poster.data.materials.append(emission_material("poster_red", (0.75, 0.06, 0.06, 1.0), 1.2))

    for x in (-4.5, 0.0, 4.5):
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.06, depth=5.0,
                                             location=(x, 4.0, 2.5))
        pole = bpy.context.object
        pole.name = f"lamp_pole_{int(x)}"
        pole.data.materials.append(create_material("pole_dark", (0.10, 0.10, 0.10, 1.0)))

        bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4, radius=0.12,
                                              location=(x, 4.0, 5.1))
        head = bpy.context.object
        head.name = f"lamp_head_{int(x)}"
        head.data.materials.append(emission_material("lamp_warm", (1.0, 0.88, 0.65, 1.0), 4.0))

    for bx, bz in ((-6, 5), (6, 4)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(bx, 4, bz / 2))
        sb = bpy.context.object
        sb.name = f"side_building_{bx}"
        sb.dimensions = (2.5, 4.0, float(bz))
        sb.data.materials.append(create_material("side_facade", (0.55, 0.50, 0.42, 1.0)))

def add_floor(name: str, *, color: tuple[float, float, float, float]) -> None:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -0.05))
    floor = bpy.context.object
    floor.name = name
    floor.dimensions = (14, 14, 0.1)
    floor.data.materials.append(create_material(f"{name}_material", color))

def create_rain_system() -> None:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(100, 100, 100))
    streak = bpy.context.object
    streak.name = "rain_streak_instance"
    streak.dimensions = (0.015, 0.015, 0.35)
    mat = bpy.data.materials.new("rain_streak_material")
    mat.diffuse_color = (0.55, 0.75, 1.0, 0.6)
    streak.data.materials.append(mat)

    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 9))
    emitter = bpy.context.object
    emitter.name = "rain_emitter"
    emitter.hide_render = True

    ps = emitter.modifiers.new("rain_ps", type="PARTICLE_SYSTEM")
    s = ps.particle_system.settings
    s.name = "rain_settings"
    s.type = "EMITTER"
    s.count = 400
    s.frame_start = 1
    s.frame_end = 500
    s.lifetime = 25
    s.lifetime_random = 0.3
    s.emit_from = "FACE"
    s.use_emit_random = True
    s.normal_factor = 0.0
    s.factor_random = 0.4
    s.object_align_factor[2] = -8.0
    s.render_type = "OBJECT"
    s.instance_object = streak
    s.particle_size = 0.8
    s.use_rotation_instance = True

def create_fog_volume() -> None:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1, 3))
    vol = bpy.context.object
    vol.name = "fog_volume"
    vol.dimensions = (14, 12, 8)

    mat = bpy.data.materials.new("fog_volume_material")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (300, 0)
    scatter = nodes.new("ShaderNodeVolumeScatter")
    scatter.location = (0, 0)
    scatter.inputs["Density"].default_value = 0.08
    scatter.inputs["Color"].default_value = (0.75, 0.82, 0.95, 1.0)
    links.new(scatter.outputs["Volume"], output.inputs["Volume"])
    vol.data.materials.append(mat)

    bpy.context.scene.eevee.use_volumetric_shadows = True

def create_snow_system() -> None:
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.04, location=(100, 100, 100))
    flake = bpy.context.object
    flake.name = "snow_flake_instance"
    mat = bpy.data.materials.new("snow_flake_material")
    mat.diffuse_color = (0.95, 0.97, 1.0, 0.9)
    flake.data.materials.append(mat)

    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 7))
    emitter = bpy.context.object
    emitter.name = "snow_emitter"
    emitter.hide_render = True

    ps = emitter.modifiers.new("snow_ps", type="PARTICLE_SYSTEM")
    s = ps.particle_system.settings
    s.name = "snow_settings"
    s.type = "EMITTER"
    s.count = 250
    s.frame_start = 1
    s.frame_end = 500
    s.lifetime = 60
    s.lifetime_random = 0.4
    s.emit_from = "FACE"
    s.use_emit_random = True
    s.normal_factor = 0.0
    s.factor_random = 0.8
    s.object_align_factor[2] = -1.5
    s.render_type = "OBJECT"
    s.instance_object = flake
    s.particle_size = 1.0
