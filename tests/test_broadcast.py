"""Tests for broadcast.py — overlays de noticiero."""

import unittest
from pathlib import Path
import tempfile

import ffmpeg

from ai_blender_director import broadcast


class RenderOverlayTest(unittest.TestCase):
    RES = (720, 1280)

    def test_lower_third_is_full_frame_rgba(self):
        img = broadcast.render_lower_third("La Cotorra", "Corresponsal", self.RES)
        self.assertEqual(img.size, self.RES)
        self.assertEqual(img.mode, "RGBA")
        # tiene contenido (no es totalmente transparente)
        self.assertGreater(img.getextrema()[3][1], 0)

    def test_corner_bug_renders(self):
        img = broadcast.render_corner_bug("Última Hora", self.RES)
        self.assertEqual(img.size, self.RES)
        self.assertEqual(img.mode, "RGBA")

    def test_ticker_strip_wider_than_frame(self):
        bg, strip, width = broadcast.render_ticker("noticias del régimen", self.RES)
        self.assertEqual(bg.size, self.RES)
        self.assertGreaterEqual(width, self.RES[0])
        self.assertEqual(strip.width, width)


class ApplyOverlaysTest(unittest.TestCase):
    RES = (720, 1280)

    def test_no_overlay_returns_same_stream(self):
        base = ffmpeg.input("in.mp4").video
        out = broadcast.apply_overlays(
            base, Path("."), "x", resolution=self.RES, fps=24, video_duration=5.0
        )
        self.assertIs(out, base)

    def test_overlays_appear_in_compiled_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            base = ffmpeg.input("in.mp4").video
            out = broadcast.apply_overlays(
                base, work, "x",
                resolution=self.RES, fps=24, video_duration=5.0,
                lower_third=("La Cotorra", "Corresponsal"),
                ticker_text="noticias oficiales",
                corner_bug="En Vivo",
            )
            # Stream final escribible → grafo compilable con overlays
            args = " ".join(ffmpeg.compile(ffmpeg.output(out, str(work / "o.mp4"))))
            self.assertIn("overlay", args)
            # Se generaron los PNG de los overlays
            self.assertTrue((work / "x_lower_third.png").exists())
            self.assertTrue((work / "x_ticker_bg.png").exists())
            self.assertTrue((work / "x_corner_bug.png").exists())


if __name__ == "__main__":
    unittest.main()
