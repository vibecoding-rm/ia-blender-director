from pathlib import Path
from unittest import TestCase

from ai_blender_director.assets import AssetRegistry
from ai_blender_director.character_registry import character_asset_ids, character_schema_text, detect_character


class TestCharacterRegistry(TestCase):
    def test_registry_covers_all_character_assets(self) -> None:
        catalog_ids = {asset.asset_id for asset in AssetRegistry(Path("assets")).list_assets("character")}
        registry_ids = set(character_asset_ids())

        self.assertEqual(registry_ids, catalog_ids)

    def test_schema_lists_legacy_and_current_protagonists(self) -> None:
        schema = character_schema_text()

        self.assertIn("protagonista_v1", schema)
        self.assertIn("protagonista_v2", schema)

    def test_exact_asset_id_wins_over_generic_keywords(self) -> None:
        self.assertEqual(detect_character("usar protagonista_v1 como proxy"), "protagonista_v1")
        self.assertEqual(detect_character("personaje hero caminando"), "protagonista_v2")

    def test_detection_is_accent_insensitive(self) -> None:
        self.assertEqual(detect_character("el caim\u00e1n mueve los hilos"), "caiman_v1")
        self.assertEqual(detect_character("el caiman mueve los hilos"), "caiman_v1")
        self.assertEqual(detect_character("h\u00e9roe caminando"), "protagonista_v2")
