from __future__ import annotations

import unittest

from ai_blender_director.generator import generate_shot


class GenerateShotTest(unittest.TestCase):
    def test_generates_cyberpunk_rain_orbit_spec(self) -> None:
        shot = generate_shot("calle cyberpunk nocturna con lluvia y camara orbitando")

        self.assertEqual(shot["scene"], "cyberpunk street")
        self.assertEqual(shot["camera"]["movement"], "orbit")
        self.assertEqual(shot["weather"], "rain")
        self.assertEqual(shot["style"], "cinematic neon noir")

    def test_generates_valid_forest_spec(self) -> None:
        shot = generate_shot("bosque con niebla y camara fija", duration_seconds=2, fps=12)

        self.assertEqual(shot["scene"], "procedural forest")
        self.assertEqual(shot["camera"]["movement"], "static")
        self.assertEqual(shot["weather"], "fog")
        self.assertEqual(shot["duration_seconds"], 2)
        self.assertEqual(shot["fps"], 12)


if __name__ == "__main__":
    unittest.main()
