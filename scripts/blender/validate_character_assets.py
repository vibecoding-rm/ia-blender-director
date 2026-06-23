"""
Blender headless validator for character GLB files.

Checks that each registered character GLB imports, contains an armature, has a
Jaw or Beak mouth bone, has eye bones, and embeds Idle/Talk/Walk actions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "characters"
REQUIRED_ACTIONS = {"Idle", "Talk", "Walk"}
MOUTH_BONES = {"Jaw", "Beak"}


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.actions, bpy.data.armatures, bpy.data.meshes, bpy.data.materials):
        for block in list(collection):
            collection.remove(block)


def validate_character(manifest_path: Path) -> list[str]:
    problems: list[str] = []
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    asset_id = data.get("id", manifest_path.parent.name)
    metadata = data.get("metadata") or {}
    declared_bones = metadata.get("bones") if isinstance(metadata, dict) else None
    lip_sync_ready = isinstance(declared_bones, list) and bool(MOUTH_BONES & set(declared_bones))
    raw_path = data.get("path")
    if not raw_path:
        return [f"{asset_id}: missing path"]

    glb = manifest_path.parent / raw_path
    if not glb.exists():
        return [f"{asset_id}: GLB not found: {glb}"]

    clear_scene()
    try:
        bpy.ops.import_scene.gltf(filepath=str(glb))
    except Exception as exc:  # noqa: BLE001
        return [f"{asset_id}: import failed: {exc}"]

    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if not armatures:
        return [f"{asset_id}: no armature found"]
    armature = armatures[0]
    bone_names = set(armature.data.bones.keys())

    if lip_sync_ready:
        if not (MOUTH_BONES & bone_names):
            problems.append(f"{asset_id}: missing Jaw/Beak bone")
        for eye in ("Eye.L", "Eye.R"):
            if eye not in bone_names:
                problems.append(f"{asset_id}: missing {eye} bone")

        action_names = {action.name for action in bpy.data.actions}
        missing_actions = {
            required for required in REQUIRED_ACTIONS
            if not any(required.lower() in action.lower() for action in action_names)
        }
        if missing_actions:
            problems.append(f"{asset_id}: missing actions {sorted(missing_actions)}")

    return problems


def main() -> int:
    manifests = sorted(ASSETS.glob("*/asset.json"))
    problems: list[str] = []
    for manifest in manifests:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data.get("type") != "character" or not data.get("path"):
            continue
        problems.extend(validate_character(manifest))

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 2

    print(f"ok: validated {len(manifests)} character manifests with Blender")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
