from __future__ import annotations
import json
import bpy
from .core import ASSETS_ROOT

def resolve_asset_refs(spec: dict) -> dict:
    refs = {}
    nested_assets = spec.get("assets") if isinstance(spec.get("assets"), dict) else {}
    for key, asset_type in [
        ("character", "characters"),
        ("environment", "environments"),
        ("animation", "animations"),
    ]:
        asset_id = spec.get(key) or nested_assets.get(key)
        if not asset_id:
            continue
        refs[key] = load_asset_ref(asset_id, asset_type)
    return refs

def load_asset_ref(asset_id: str, asset_type: str) -> dict:
    manifest_path = ASSETS_ROOT / asset_type / asset_id / "asset.json"
    if not manifest_path.exists():
        return {
            "id": asset_id,
            "type": asset_type.rstrip("s"),
            "source": "missing",
            "manifest": str(manifest_path),
            "resolved": False,
        }
    with manifest_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    raw_path = data.get("path")
    resolved_path: str | None = None
    if raw_path:
        candidate = (manifest_path.parent / raw_path).resolve()
        resolved_path = str(candidate) if candidate.exists() else None
        if not candidate.exists():
            print(f"  WARNING: asset '{asset_id}' path not found: {candidate}")
    return {
        "id": data.get("id", asset_id),
        "type": data.get("type", asset_type.rstrip("s")),
        "name": data.get("name", asset_id),
        "source": data.get("source", "unknown"),
        "path": resolved_path,
        "manifest": str(manifest_path.resolve()),
        "resolved": True,
        "metadata": data.get("metadata", {}),
    }

def import_glb(path: str, *, label: str = "asset") -> bpy.types.Object | None:
    before = set(bpy.context.scene.objects)
    try:
        bpy.ops.import_scene.gltf(filepath=path)
    except Exception as exc:  # noqa: BLE001
        print(f"  ERROR importing {label} from '{path}': {exc}")
        return None

    new_objects = [obj for obj in bpy.context.scene.objects if obj not in before]
    if not new_objects:
        print(f"  WARNING: import of {label} produced no objects.")
        return None

    root = find_root_object(new_objects)
    print(f"  Imported {len(new_objects)} object(s) for {label}, root: {root.name}")
    return root

def find_root_object(objects: list[bpy.types.Object]) -> bpy.types.Object:
    roots = [obj for obj in objects if obj.parent is None or obj.parent not in objects]
    armatures = [obj for obj in roots if obj.type == "ARMATURE"]
    if armatures:
        return armatures[0]
    return roots[0] if roots else objects[0]
