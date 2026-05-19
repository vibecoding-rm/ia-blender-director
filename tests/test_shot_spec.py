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
            }
        )

        self.assertEqual(spec.frame_count, 72)
        self.assertEqual(spec.camera.lens_mm, 50)

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
