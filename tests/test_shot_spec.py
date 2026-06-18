from __future__ import annotations

import unittest

from ai_blender_director.models import ShotSpec, ShotValidationError


class ShotSpecTest(unittest.TestCase):
    def test_valid_spec_computes_frame_count(self) -> None:
        spec = ShotSpec.from_dict(
            {
                "scene": "test scene",
                "style": "cinematic",
                "duration_seconds": 3,
                "fps": 24,
                "resolution": {"width": 1280, "height": 720},
                "camera": {"movement": "slow dolly", "lens_mm": 50},
                "lighting": "soft key",
                "subject": "cube",
                "action": "moves forward",
                "weather": None,
                "seed": 7,
                "character": "protagonista_v1",
                "environment": "cyberpunk_street_v1",
                "animation": "walk_v1",
            }
        )

        self.assertEqual(spec.frame_count, 72)
        self.assertEqual(spec.camera.lens_mm, 50)
        self.assertEqual(spec.assets.character, "protagonista_v1")
        self.assertEqual(spec.character, "protagonista_v1")
        self.assertEqual(spec.transition.type, "none")
        self.assertEqual(spec.transition.duration, 0.5)

    def test_assets_mapping_is_normalized_to_properties(self) -> None:
        spec = ShotSpec.from_dict(
            {
                "scene": "test scene",
                "style": "cinematic",
                "duration_seconds": 3,
                "fps": 24,
                "resolution": {"width": 1280, "height": 720},
                "camera": {"movement": "slow dolly", "lens_mm": 50},
                "lighting": "soft key",
                "subject": "cube",
                "action": "moves forward",
                "weather": None,
                "seed": 7,
                "assets": {"character": "protagonista_v1", "environment": "forest_v1"},
            }
        )

        self.assertEqual(spec.character, "protagonista_v1")
        self.assertEqual(spec.environment, "forest_v1")
        self.assertEqual(spec.assets.character, "protagonista_v1")

    def test_transition_spec(self) -> None:
        spec = ShotSpec.from_dict(
            {
                "scene": "test scene",
                "style": "cinematic",
                "duration_seconds": 3,
                "fps": 24,
                "resolution": {"width": 1280, "height": 720},
                "camera": {"movement": "slow dolly", "lens_mm": 50},
                "lighting": "soft key",
                "subject": "cube",
                "action": "moves forward",
                "weather": None,
                "seed": 7,
                "transition": {"type": "fade", "duration": 1.2}
            }
        )
        self.assertEqual(spec.transition.type, "fade")
        self.assertEqual(spec.transition.duration, 1.2)

    def test_rejects_invalid_transition(self) -> None:
        with self.assertRaises(ShotValidationError):
            ShotSpec.from_dict(
                {
                    "scene": "test scene",
                    "style": "cinematic",
                    "duration_seconds": 3,
                    "fps": 24,
                    "resolution": {"width": 1280, "height": 720},
                    "camera": {"movement": "slow dolly", "lens_mm": 50},
                    "lighting": "soft key",
                    "subject": "cube",
                    "action": "moves forward",
                    "weather": None,
                    "seed": 7,
                    "transition": {"type": "invalid_type", "duration": 0.5}
                }
            )

    def test_rejects_unbounded_duration(self) -> None:
        with self.assertRaises(ShotValidationError):
            ShotSpec.from_dict(
                {
                    "scene": "test scene",
                    "style": "cinematic",
                    "duration_seconds": 500,
                    "fps": 24,
                    "resolution": {"width": 1280, "height": 720},
                    "camera": {"movement": "slow dolly"},
                    "lighting": "soft key",
                    "subject": "cube",
                    "action": "moves forward",
                    "weather": None,
                    "seed": 7,
                }
            )


if __name__ == "__main__":
    unittest.main()
