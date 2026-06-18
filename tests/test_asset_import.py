"""Tests for asset import path resolution (Week 4: Real Assets)."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_blender_director.assets import AssetRegistry, AssetSpec, AssetValidationError


class TestAssetSpecExists(unittest.TestCase):
    """AssetSpec.exists reflects whether the file is available."""

    def _make_spec(self, path: Path | None) -> AssetSpec:
        return AssetSpec(
            asset_id="test_asset",
            asset_type="character",
            name="Test",
            source="placeholder",
            path=path,
            metadata={},
            manifest_path=Path("/fake/asset.json"),
        )

    def test_exists_true_when_path_is_none(self) -> None:
        """A placeholder asset with path=None should always report exists=True."""
        spec = self._make_spec(path=None)
        self.assertTrue(spec.exists)

    def test_exists_false_when_path_missing(self, tmp_path=None) -> None:
        """An asset pointing to a non-existent file should report exists=False."""
        missing = Path("/nonexistent/character.glb")
        spec = self._make_spec(path=missing)
        self.assertFalse(spec.exists)

    def test_exists_true_when_path_present(self, tmp_path=None) -> None:
        """An asset whose file actually exists should report exists=True."""
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
            real_path = Path(f.name)
        try:
            spec = self._make_spec(path=real_path)
            self.assertTrue(spec.exists)
        finally:
            os.unlink(real_path)


class TestAllAssetManifestsPresent(unittest.TestCase):
    """All expected asset.json files exist and are valid."""

    ASSETS_ROOT = Path(__file__).resolve().parents[1] / "assets"

    EXPECTED = [
        ("characters", "protagonista_v1"),
        ("environments", "cyberpunk_street_v1"),
        ("environments", "forest_v1"),
        ("animations", "walk_v1"),
        ("animations", "run_v1"),
        ("animations", "idle_v1"),
    ]

    def test_manifests_exist(self) -> None:
        for asset_dir, asset_id in self.EXPECTED:
            manifest = self.ASSETS_ROOT / asset_dir / asset_id / "asset.json"
            with self.subTest(asset=asset_id):
                self.assertTrue(manifest.exists(), f"Missing: {manifest}")

    def test_manifests_have_required_fields(self) -> None:
        for asset_dir, asset_id in self.EXPECTED:
            manifest = self.ASSETS_ROOT / asset_dir / asset_id / "asset.json"
            with self.subTest(asset=asset_id):
                with manifest.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                self.assertEqual(data["id"], asset_id)
                self.assertIn("type", data)
                self.assertIn("name", data)
                self.assertIn("source", data)
                self.assertIn("path", data)  # may be null
                self.assertIn("metadata", data)

    def test_manifests_path_is_string_or_null(self) -> None:
        """All manifests must have a 'path' field that is either null or a string."""
        for asset_dir, asset_id in self.EXPECTED:
            manifest = self.ASSETS_ROOT / asset_dir / asset_id / "asset.json"
            with self.subTest(asset=asset_id):
                with manifest.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                self.assertIn(
                    type(data["path"]), (type(None), str),
                    f"'path' must be null or a string for {asset_id}",
                )


class TestAssetRegistryResolveAll(unittest.TestCase):
    """AssetRegistry can resolve all 6 expected assets without error."""

    ASSETS_ROOT = Path(__file__).resolve().parents[1] / "assets"

    def _registry(self) -> AssetRegistry:
        return AssetRegistry(self.ASSETS_ROOT)

    def test_resolve_character(self) -> None:
        spec = self._registry().resolve("protagonista_v1", "character")
        self.assertEqual(spec.asset_id, "protagonista_v1")
        # path may be None (placeholder) or a resolved Path (real GLB)
        self.assertTrue(spec.path is None or isinstance(spec.path, Path))

    def test_resolve_environments(self) -> None:
        for asset_id in ("cyberpunk_street_v1", "forest_v1"):
            with self.subTest(asset=asset_id):
                spec = self._registry().resolve(asset_id, "environment")
                self.assertEqual(spec.asset_id, asset_id)
                # Exists if path is None (placeholder) or points to an actual file
                if spec.path is None:
                    self.assertTrue(spec.exists)

    def test_resolve_animations(self) -> None:
        for asset_id in ("walk_v1", "run_v1", "idle_v1"):
            with self.subTest(asset=asset_id):
                spec = self._registry().resolve(asset_id, "animation")
                self.assertEqual(spec.asset_id, asset_id)
                self.assertTrue(spec.exists)

    def test_list_all_assets_returns_sixteen(self) -> None:
        specs = self._registry().list_assets()
        self.assertEqual(len(specs), 16)
        ids = {s.asset_id for s in specs}
        for asset_id in ("humbrete_v1", "ciberclarias_v1", "michelito_v1", "randy_v1",
                         "guerrero_v1", "guanajo_v1"):
            self.assertIn(asset_id, ids)

    def test_missing_asset_raises(self) -> None:
        with self.assertRaises(AssetValidationError):
            self._registry().resolve("nonexistent_asset_xyz")


class TestAssetWithRealPath(unittest.TestCase):
    """Simulate an asset with a real file path and verify resolution."""

    ASSETS_ROOT = Path(__file__).resolve().parents[1] / "assets"

    def test_asset_resolves_without_error(self) -> None:
        registry = AssetRegistry(self.ASSETS_ROOT)
        spec = registry.resolve("protagonista_v1", "character")
        self.assertEqual(spec.asset_id, "protagonista_v1")
        # If path is non-null but file doesn't exist yet (GLB not exported), exists=False is OK
        self.assertIsNotNone(spec)

    def test_asset_spec_with_missing_file_path(self) -> None:
        """Directly construct AssetSpec with a non-existent path."""
        spec = AssetSpec(
            asset_id="ghost_asset",
            asset_type="character",
            name="Ghost",
            source="real",
            path=Path("/does/not/exist/character.glb"),
            metadata={},
            manifest_path=Path("/fake/asset.json"),
        )
        self.assertFalse(spec.exists)


if __name__ == "__main__":
    unittest.main()
