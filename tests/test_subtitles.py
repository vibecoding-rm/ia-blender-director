import unittest
from pathlib import Path
import tempfile

from ai_blender_director.subtitles import chunk_narration, caption_timings, write_ass


class TestChunkNarration(unittest.TestCase):
    def test_splits_long_sentence_by_max_words(self):
        text = "uno dos tres cuatro cinco seis siete ocho nueve diez"
        chunks = chunk_narration(text, max_words=5)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], "uno dos tres cuatro cinco")

    def test_respects_sentence_boundaries(self):
        chunks = chunk_narration("Primera frase corta. Segunda frase corta.")
        self.assertEqual(chunks, ["Primera frase corta.", "Segunda frase corta."])

    def test_empty_text(self):
        self.assertEqual(chunk_narration("   "), [])


class TestCaptionTimings(unittest.TestCase):
    def test_total_duration_and_offset(self):
        chunks = ["hola mundo", "segunda parte"]
        timings = caption_timings(chunks, audio_duration=10.0, start_offset=1.4)
        self.assertAlmostEqual(timings[0][0], 1.4)
        self.assertAlmostEqual(timings[-1][1], 11.4, places=5)
        # contiguos: el fin de uno es el inicio del siguiente
        self.assertAlmostEqual(timings[0][1], timings[1][0], places=5)

    def test_proportional_to_length(self):
        timings = caption_timings(["ab", "abababab"], audio_duration=10.0)
        self.assertLess(timings[0][1] - timings[0][0], timings[1][1] - timings[1][0])


class TestWriteAss(unittest.TestCase):
    def test_writes_valid_ass_with_uppercase_dialogue(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "subs.ass"
            write_ass([(0.0, 2.5, "hola cuba")], path, play_res=(720, 1280))
            content = path.read_text(encoding="utf-8")
            self.assertIn("[Events]", content)
            self.assertIn("HOLA CUBA", content)
            self.assertIn("0:00:02.50", content)


if __name__ == "__main__":
    unittest.main()
