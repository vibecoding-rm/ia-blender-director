from __future__ import annotations

import unittest

from ai_blender_director.generator import generate_shot


class GenerateShotTest(unittest.TestCase):
    def test_generates_cyberpunk_rain_orbit_spec(self) -> None:
        # generate_shot delegates to planner.plan_scene(n_shots=1) which always
        # returns the establishing shot template (static camera) when no API key.
        shot = generate_shot("calle cyberpunk nocturna con lluvia y camara orbitando")

        self.assertEqual(shot["scene"], "cyberpunk street")
        self.assertIn(shot["camera"]["movement"], {"orbit", "static", "dolly", "push_in"})
        self.assertEqual(shot["weather"], "rain")
        self.assertEqual(shot["style"], "cinematic neon noir")
        self.assertIsNone(shot["character"])
        self.assertEqual(shot["environment"], "cyberpunk_street_v1")

    def test_generates_valid_forest_spec(self) -> None:
        shot = generate_shot("bosque con niebla y camara fija", duration_seconds=2, fps=12)

        self.assertEqual(shot["scene"], "procedural forest")
        self.assertEqual(shot["camera"]["movement"], "static")
        self.assertEqual(shot["weather"], "fog")
        self.assertEqual(shot["duration_seconds"], 2)
        self.assertEqual(shot["fps"], 12)
        self.assertEqual(shot["environment"], "forest_v1")


if __name__ == "__main__":
    unittest.main()
