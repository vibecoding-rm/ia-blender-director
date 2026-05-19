from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class AssetValidationError(ValueError):
    """Raised when an asset manifest is missing or invalid."""


@dataclass(frozen=True)
class AssetSpec:
    asset_id: str
    asset_type: str
    name: str
    source: str
    path: Path | None
    metadata: dict[str, Any]
    manifest_path: Path

    @property
    def exists(self) -> bool:
        return self.path is None or self.path.exists()


class AssetRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root

    def resolve(self, asset_id: str, asset_type: str | None = None) -> AssetSpec:
        manifest_path = self._find_manifest(asset_id, asset_type)
        return _load_asset_manifest(manifest_path)

    def list_assets(self, asset_type: str | None = None) -> list[AssetSpec]:
        pattern = f"{_asset_dir_name(asset_type)}/*/asset.json" if asset_type else "*/*/asset.json"
        manifests = sorted(self.root.glob(pattern))
        return [_load_asset_manifest(path) for path in manifests]

    def _find_manifest(self, asset_id: str, asset_type: str | None) -> Path:
        if asset_type:
            manifest = self.root / _asset_dir_name(asset_type) / asset_id / "asset.json"
            if manifest.exists():
                return manifest

        matches = list(self.root.glob(f"*/{asset_id}/asset.json"))
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise AssetValidationError(f"Asset not found: {asset_id}")
        raise AssetValidationError(f"Asset id is ambiguous: {asset_id}")


def _asset_dir_name(asset_type: str) -> str:
    return asset_type if asset_type.endswith("s") else f"{asset_type}s"


def _load_asset_manifest(path: Path) -> AssetSpec:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as exc:
        raise AssetValidationError(f"Asset manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AssetValidationError(f"Invalid asset manifest JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise AssetValidationError(f"Asset manifest must be an object: {path}")

    asset_id = _required_str(data, "id", path)
    asset_type = _required_str(data, "type", path)
    name = _required_str(data, "name", path)
    source = _optional_str(data, "source", default="placeholder")
    relative_path = data.get("path")
    asset_path = None
    if relative_path is not None:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise AssetValidationError(f"'path' must be a non-empty string in {path}")
        asset_path = (path.parent / relative_path).resolve()

    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        raise AssetValidationError(f"'metadata' must be an object in {path}")

    return AssetSpec(
        asset_id=asset_id,
        asset_type=asset_type,
        name=name,
        source=source,
        path=asset_path,
        metadata=metadata,
        manifest_path=path.resolve(),
    )


def _required_str(data: dict[str, Any], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AssetValidationError(f"'{key}' must be a non-empty string in {path}")
    return value.strip()


def _optional_str(data: dict[str, Any], key: str, *, default: str) -> str:
    value = data.get(key, default)
    if not isinstance(value, str) or not value.strip():
        return default
    return value.strip()
