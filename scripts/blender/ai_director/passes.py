from __future__ import annotations
import bpy
from pathlib import Path

def render_control_passes(output_dir: Path, subject: bpy.types.Object) -> dict[str, str]:
    passes_dir = output_dir / "passes"
    passes_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.frame_set(1)
    frame = scene.frame_current

    mark_subject_for_passes(subject, pass_index=1)

    enable_view_layer_passes(scene)

    bpy.context.evaluated_depsgraph_get()

    setup_compositor_pass_nodes(scene, passes_dir)

    original_filepath = scene.render.filepath
    original_format = scene.render.image_settings.file_format
    try:
        scene.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(write_still=False)
    finally:
        scene.render.filepath = original_filepath
        scene.render.image_settings.file_format = original_format
        clear_compositor(scene)
        reset_subject_pass_index(subject)

    frame_str = f"{frame:04d}"
    result: dict[str, str] = {
        "beauty":      str(resolve_pass_file(passes_dir / f"beauty_frame_{frame_str}.png")),
        "depth_proxy": str(resolve_pass_file(passes_dir / f"depth_proxy_frame_{frame_str}.png")),
        "normal_proxy": str(resolve_pass_file(passes_dir / f"normal_proxy_frame_{frame_str}.png")),
    }
    mask_candidate = passes_dir / f"subject_mask_frame_{frame_str}.png"
    if mask_candidate.exists():
        result["subject_mask"] = str(mask_candidate)
    return result

def mark_subject_for_passes(subject: bpy.types.Object, *, pass_index: int) -> None:
    subject.pass_index = pass_index
    for child in subject.children_recursive:
        child.pass_index = pass_index
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            for mod in obj.modifiers:
                if mod.type == "ARMATURE" and mod.object == subject:
                    obj.pass_index = pass_index
                    break

def reset_subject_pass_index(subject: bpy.types.Object) -> None:
    subject.pass_index = 0
    for child in subject.children_recursive:
        child.pass_index = 0
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.pass_index != 0:
            obj.pass_index = 0

def enable_view_layer_passes(scene: bpy.types.Scene) -> None:
    vl = scene.view_layers[0]
    vl.use_pass_z = True
    vl.use_pass_normal = True
    vl.use_pass_object_index = True
    vl.use_pass_combined = True

def setup_compositor_pass_nodes(scene: bpy.types.Scene, passes_dir: Path) -> None:
    scene.use_nodes = True
    tree = scene.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    rl = nodes.new("CompositorNodeRLayers")
    rl.location = (-300, 0)
    nodes.remove(rl)
    rl = nodes.new("CompositorNodeRLayers")
    rl.location = (-300, 0)

    beauty_out = file_output_node(nodes, passes_dir, "beauty_frame_", x=200, y=300)
    links.new(rl.outputs["Image"], beauty_out.inputs[0])

    composite = nodes.new("CompositorNodeComposite")
    composite.location = (200, 150)
    links.new(rl.outputs["Image"], composite.inputs["Image"])

    normalize = nodes.new("CompositorNodeNormalize")
    normalize.location = (-50, 0)
    links.new(rl.outputs["Depth"], normalize.inputs[0])
    depth_out = file_output_node(nodes, passes_dir, "depth_proxy_frame_", x=200, y=0)
    links.new(normalize.outputs[0], depth_out.inputs[0])

    normal_out = file_output_node(nodes, passes_dir, "normal_proxy_frame_", x=200, y=-200)
    links.new(rl.outputs["Normal"], normal_out.inputs[0])

    id_mask = nodes.new("CompositorNodeIDMask")
    id_mask.location = (-50, -300)
    id_mask.index = 1
    id_mask.use_antialiasing = True
    mask_out = file_output_node(nodes, passes_dir, "subject_mask_frame_", x=200, y=-400)
    if "IndexOB" in rl.outputs:
        links.new(rl.outputs["IndexOB"], id_mask.inputs[0])
        links.new(id_mask.outputs[0], mask_out.inputs[0])
    else:
        rgb_white = nodes.new("CompositorNodeRGB")
        rgb_white.outputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
        rgb_white.location = (-50, -500)
        links.new(rgb_white.outputs[0], mask_out.inputs[0])

def file_output_node(
    nodes: bpy.types.NodeTree,
    base_dir: Path,
    slot_prefix: str,
    *,
    x: float,
    y: float,
) -> bpy.types.CompositorNodeOutputFile:
    node = nodes.new("CompositorNodeOutputFile")
    node.location = (x, y)
    node.base_path = str(base_dir)
    node.format.file_format = "PNG"
    node.format.color_mode = "RGB"
    node.format.color_depth = "8"
    node.file_slots[0].path = slot_prefix
    return node

def clear_compositor(scene: bpy.types.Scene) -> None:
    if scene.use_nodes and scene.node_tree:
        scene.node_tree.nodes.clear()
    scene.use_nodes = False

def resolve_pass_file(path: Path) -> Path:
    return path if path.exists() else path.with_suffix("")
