from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ai_blender_director.assets import AssetRegistry


class AssetRegistryTest(unittest.TestCase):
    def test_resolves_asset_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset_dir = root / "characters" / "hero_v1"
            asset_dir.mkdir(parents=True)
            (asset_dir / "asset.json").write_text(
                json.dumps(
                    {
                        "id": "hero_v1",
                        "type": "character",
                        "name": "Hero",
                        "source": "procedural_placeholder",
                        "path": None,
                        "metadata": {"description": "test"},
                    }
                ),
                encoding="utf-8",
            )

            asset = AssetRegistry(root).resolve("hero_v1", "character")

            self.assertEqual(asset.asset_id, "hero_v1")
            self.assertEqual(asset.asset_type, "character")
            self.assertTrue(asset.exists)

    def test_lists_assets_by_singular_type(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset_dir = root / "characters" / "hero_v1"
            asset_dir.mkdir(parents=True)
            (asset_dir / "asset.json").write_text(
                json.dumps(
                    {
                        "id": "hero_v1",
                        "type": "character",
                        "name": "Hero",
                    }
                ),
                encoding="utf-8",
            )

            assets = AssetRegistry(root).list_assets("character")

            self.assertEqual([asset.asset_id for asset in assets], ["hero_v1"])


if __name__ == "__main__":
    unittest.main()
