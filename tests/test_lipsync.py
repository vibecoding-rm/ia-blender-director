"""Tests for lipsync.py — visemas de Rhubarb a apertura de pico."""

import json
import math
import tempfile
import unittest
from pathlib import Path

from ai_blender_director import lipsync


class VisemeMappingTest(unittest.TestCase):
    def test_silence_is_closed(self):
        self.assertEqual(lipsync.VISEME_OPENNESS["X"], 0.0)

    def test_open_vowel_is_widest(self):
        self.assertEqual(max(lipsync.VISEME_OPENNESS.values()), lipsync.VISEME_OPENNESS["D"])

    def test_parse_visemes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "v.json"
            p.write_text(json.dumps({"mouthCues": [
                {"start": 0.0, "end": 0.1, "value": "X"},
                {"start": 0.1, "end": 0.3, "value": "D"},
            ]}))
            cues = lipsync.parse_visemes(p)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[1]["value"], "D")

    def test_cues_to_jaw_track_maps_frames_and_radians(self):
        cues = [
            {"start": 0.0, "value": "X"},
            {"start": 0.5, "value": "D"},
            {"start": 1.0, "value": "A"},
        ]
        max_open = math.radians(45)
        track = lipsync.cues_to_jaw_track(cues, fps=24, max_open_rad=max_open)
        self.assertEqual(len(track), 3)
        # 0.5s a 24fps → frame ~13
        self.assertEqual(track[1][0], round(0.5 * 24) + 1)
        # "D" (vocal abierta) → cerca del máximo
        self.assertAlmostEqual(track[1][1], 0.85 * max_open, places=5)

    def test_start_offset_drops_earlier_cues(self):
        cues = [{"start": 0.2, "value": "D"}, {"start": 2.0, "value": "D"}]
        track = lipsync.cues_to_jaw_track(cues, fps=24, max_open_rad=1.0, start_offset=1.0)
        # solo el cue en t=2.0 (local 1.0) sobrevive
        self.assertEqual(len(track), 1)

    def test_missing_binary_returns_none(self):
        # Si rhubarb no está instalado, generate_visemes degrada a None.
        if not lipsync.rhubarb_available():
            with tempfile.TemporaryDirectory() as tmp:
                out = lipsync.generate_visemes(Path(tmp) / "x.wav", Path(tmp) / "o.json")
                self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main()
