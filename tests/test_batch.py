import tempfile
import unittest
from pathlib import Path

from ai_blender_director.commands.batch import load_episodes


def _write(tmp: str, content: str) -> Path:
    path = Path(tmp) / "episodios.jsonl"
    path.write_text(content, encoding="utf-8")
    return path


class TestLoadEpisodes(unittest.TestCase):
    def test_loads_episodes_with_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, '# comentario\n{"id": "ep1", "prompt": "noticias"}\n')
            episodes = load_episodes(path)
            self.assertEqual(len(episodes), 1)
            self.assertEqual(episodes[0]["id"], "ep1")
            self.assertEqual(episodes[0]["shots"], 6)
            self.assertTrue(episodes[0]["vertical"])

    def test_overrides_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, '{"id": "ep1", "prompt": "p", "shots": 4, "vertical": false}\n')
            episode = load_episodes(path)[0]
            self.assertEqual(episode["shots"], 4)
            self.assertFalse(episode["vertical"])

    def test_missing_required_field_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, '{"id": "ep1"}\n')
            with self.assertRaises(ValueError):
                load_episodes(path)

    def test_duplicate_id_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, '{"id": "a", "prompt": "x"}\n{"id": "a", "prompt": "y"}\n')
            with self.assertRaises(ValueError):
                load_episodes(path)

    def test_invalid_json_raises_with_line_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, '{"id": "a", "prompt": "x"}\nno es json\n')
            with self.assertRaises(ValueError) as ctx:
                load_episodes(path)
            self.assertIn("línea 2", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
