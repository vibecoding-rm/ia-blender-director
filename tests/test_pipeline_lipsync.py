"""Tests for the end-to-end lip-sync wiring in the multi-shot pipeline."""

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_blender_director.commands import pipeline


def _shot_json(character: str | None) -> dict:
    return {
        "scene": "news studio", "style": "claymation", "duration_seconds": 4, "fps": 24,
        "resolution": {"width": 720, "height": 1280},
        "camera": {"movement": "static", "lens_mm": 35},
        "lighting": "bright studio", "subject": "cotorra anchor", "action": "presents",
        "seed": 1, "character": character,
    }


class PrepareLipsyncTest(unittest.TestCase):
    def _args(self, tmp: Path) -> argparse.Namespace:
        return argparse.Namespace(
            narration="hola, esto es el noticiero", duration=4,
            output_root=tmp, voice=None,
        )

    def _write_shots(self, tmp: Path, characters: list[str | None]) -> list[Path]:
        paths = []
        for i, ch in enumerate(characters):
            p = tmp / f"shot_{i:02d}.json"
            p.write_text(json.dumps(_shot_json(ch)), encoding="utf-8")
            paths.append(p)
        return paths

    def test_injects_visemes_with_cumulative_offsets(self):
        with tempfile.TemporaryDirectory() as tmpd:
            tmp = Path(tmpd)
            paths = self._write_shots(tmp, ["cotorra_v1", "cotorra_v1", "cotorra_v1"])

            def fake_synth(text, out, *, voice=None):
                Path(out).write_bytes(b"RIFF")
                return True

            def fake_visemes(wav, out_json, **kw):
                Path(out_json).write_text('{"mouthCues": []}')
                return Path(out_json)

            with patch("ai_blender_director.tts.synthesize", side_effect=fake_synth), \
                 patch("ai_blender_director.lipsync.generate_visemes", side_effect=fake_visemes):
                wav = pipeline._prepare_lipsync(self._args(tmp), paths, "slug")

            self.assertIsNotNone(wav)
            offsets = [json.loads(p.read_text())["narration_offset"] for p in paths]
            self.assertEqual(offsets, [0.0, 4.0, 8.0])
            for p in paths:
                self.assertIn("visemes_path", json.loads(p.read_text()))

    def test_skips_shots_without_character(self):
        with tempfile.TemporaryDirectory() as tmpd:
            tmp = Path(tmpd)
            paths = self._write_shots(tmp, ["cotorra_v1", None])

            with patch("ai_blender_director.tts.synthesize",
                       side_effect=lambda t, o, *, voice=None: (Path(o).write_bytes(b"x"), True)[1]), \
                 patch("ai_blender_director.lipsync.generate_visemes",
                       side_effect=lambda w, o, **k: (Path(o).write_text("{}"), Path(o))[1]):
                pipeline._prepare_lipsync(self._args(tmp), paths, "slug")

            self.assertIn("visemes_path", json.loads(paths[0].read_text()))
            self.assertNotIn("visemes_path", json.loads(paths[1].read_text()))

    def test_no_rhubarb_returns_wav_without_injection(self):
        with tempfile.TemporaryDirectory() as tmpd:
            tmp = Path(tmpd)
            paths = self._write_shots(tmp, ["cotorra_v1"])

            with patch("ai_blender_director.tts.synthesize",
                       side_effect=lambda t, o, *, voice=None: (Path(o).write_bytes(b"x"), True)[1]), \
                 patch("ai_blender_director.lipsync.generate_visemes", return_value=None):
                wav = pipeline._prepare_lipsync(self._args(tmp), paths, "slug")

            self.assertIsNotNone(wav)  # WAV reutilizable en postproducción
            self.assertNotIn("visemes_path", json.loads(paths[0].read_text()))

    def test_no_narration_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpd:
            tmp = Path(tmpd)
            args = argparse.Namespace(narration=None, duration=4, output_root=tmp, voice=None)
            self.assertIsNone(pipeline._prepare_lipsync(args, [], "slug"))


if __name__ == "__main__":
    unittest.main()
