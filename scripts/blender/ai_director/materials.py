from __future__ import annotations
import bpy

def is_claymation(spec: dict) -> bool:
    style = spec.get("style", "").lower()
    return any(word in style for word in ("clay", "plastilina", "claymation", "stop motion", "stop-motion"))

def apply_claymation_style() -> None:
    print("  Applying claymation style override.")
    image_color_cache: dict[str, tuple[float, float, float, float] | None] = {}
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        if obj.name.startswith("tv_screen"):
            continue
        for slot_index in range(max(1, len(obj.material_slots))):
            base_color = (0.8, 0.5, 0.35, 1.0)
            old = obj.material_slots[slot_index].material if obj.material_slots else None
            if old is not None:
                if old.use_nodes:
                    bsdf = old.node_tree.nodes.get("Principled BSDF")
                    if bsdf is not None:
                        base_input = bsdf.inputs["Base Color"]
                        sampled = texture_average_color(base_input, image_color_cache)
                        base_color = sampled if sampled else tuple(base_input.default_value)
                else:
                    base_color = tuple(old.diffuse_color)
            clay = clay_material(f"clay_{obj.name}_{slot_index}", base_color)
            if obj.material_slots:
                obj.material_slots[slot_index].material = clay
            else:
                obj.data.materials.append(clay)

def texture_average_color(
    base_input: bpy.types.NodeSocket,
    cache: dict[str, tuple[float, float, float, float] | None],
) -> tuple[float, float, float, float] | None:
    queue = [link.from_node for link in base_input.links]
    seen: set[str] = set()
    image = None
    while queue:
        node = queue.pop(0)
        if node.name in seen or len(seen) > 20:
            continue
        seen.add(node.name)
        if node.type == "TEX_IMAGE" and node.image is not None:
            image = node.image
            break
        for socket in node.inputs:
            queue.extend(link.from_node for link in socket.links)
    if image is not None:
        if image.name in cache:
            return cache[image.name]
        pixel_count = len(image.pixels) // 4
        if pixel_count == 0:
            cache[image.name] = None
            return None
        pixels = image.pixels[:]
        stride = max(1, pixel_count // 4096)
        r = g = b = weight = 0.0
        for i in range(0, pixel_count, stride):
            j = i * 4
            alpha = pixels[j + 3]
            if alpha < 0.1:
                continue
            r += pixels[j] * alpha
            g += pixels[j + 1] * alpha
            b += pixels[j + 2] * alpha
            weight += alpha
        color = (r / weight, g / weight, b / weight, 1.0) if weight > 0 else None
        cache[image.name] = color
        return color
    return None

def clay_material(name: str, color: tuple[float, ...]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = 0.85
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.24
    if "Subsurface Radius" in bsdf.inputs:
        bsdf.inputs["Subsurface Radius"].default_value = (
            max(0.2, color[0]),
            max(0.15, color[1]),
            max(0.12, color[2]),
        )
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.2

    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 35.0
    noise.inputs["Detail"].default_value = 4.0
    fingerprints = nodes.new("ShaderNodeTexVoronoi")
    fingerprints.inputs["Scale"].default_value = 18.0
    fingerprints.inputs["Randomness"].default_value = 0.72
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "FLOAT"
    mix.factor_mode = "UNIFORM"
    mix.inputs["Factor"].default_value = 0.28
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.045
    links.new(noise.outputs["Fac"], mix.inputs["A"])
    links.new(fingerprints.outputs["Distance"], mix.inputs["B"])
    links.new(mix.outputs["Result"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return material

def create_material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    return material

def image_emission_material(name: str, image_path: str, strength: float) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(image_path)
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = strength
    bsdf.inputs["Roughness"].default_value = 0.4
    return material

def emission_material(name: str, color: tuple[float, float, float, float], strength: float) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Emission Color"].default_value = color
    bsdf.inputs["Emission Strength"].default_value = strength
    return material
