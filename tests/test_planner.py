"""Tests for planner.py."""

from unittest import TestCase
from unittest.mock import patch


def _without_openrouter():
    return patch("ai_blender_director.planner.settings.openrouter_api_key", None)


class TestSlugForPrompt(TestCase):
    def test_basic_slug(self):
        from ai_blender_director.planner import slug_for_prompt
        slug = slug_for_prompt("cyberpunk hero walking")
        self.assertEqual(slug, "cyberpunk_hero_walking")

    def test_slug_max_length(self):
        from ai_blender_director.planner import slug_for_prompt
        long = "a" * 100
        slug = slug_for_prompt(long)
        self.assertLessEqual(len(slug), 60)

    def test_slug_special_chars(self):
        from ai_blender_director.planner import slug_for_prompt
        slug = slug_for_prompt("héroe en ciudad!")
        # non-ascii and punctuation become underscores
        self.assertNotIn("!", slug)
        self.assertNotIn(" ", slug)

    def test_slug_empty(self):
        from ai_blender_director.planner import slug_for_prompt
        slug = slug_for_prompt("   ")
        self.assertEqual(slug, "plan")


class TestFallbackPlan(TestCase):
    def test_returns_n_shots(self):
        from ai_blender_director.planner import plan_shots
        with _without_openrouter():
            shots = plan_shots("cyberpunk hero in the rain", n_shots=3)
        self.assertEqual(len(shots), 3)

    def test_cyberpunk_scene_detected(self):
        from ai_blender_director.planner import plan_shots
        with _without_openrouter():
            shots = plan_shots("personaje en calle cyberpunk", n_shots=2)
        self.assertEqual(shots[0]["scene"], "cyberpunk street")

    def test_rain_weather_detected(self):
        from ai_blender_director.planner import plan_shots
        with _without_openrouter():
            shots = plan_shots("hero walking in the rain", n_shots=1)
        self.assertEqual(shots[0].get("weather"), "rain")

    def test_shots_have_required_keys(self):
        from ai_blender_director.planner import plan_shots
        with _without_openrouter():
            shots = plan_shots("any idea", n_shots=2)
        required = {"scene", "style", "duration_seconds", "fps", "resolution",
                    "camera", "lighting", "subject", "action", "seed"}
        for shot in shots:
            for key in required:
                self.assertIn(key, shot, f"Missing key '{key}' in shot")

    def test_unique_seeds(self):
        from ai_blender_director.planner import plan_shots
        with _without_openrouter():
            shots = plan_shots("forest hero", n_shots=3)
        seeds = [s["seed"] for s in shots]
        self.assertEqual(len(seeds), len(set(seeds)), "Seeds should be unique per shot")


class TestWriteShotPlan(TestCase):
    def test_writes_files(self):
        import tempfile, json
        from pathlib import Path
        from ai_blender_director.planner import write_shot_plan

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with _without_openrouter():
                paths = write_shot_plan("cyberpunk rain hero", out, n_shots=2)
            self.assertEqual(len(paths), 2)
            for p in paths:
                self.assertTrue(p.exists())
                data = json.loads(p.read_text())
                self.assertNotIn("_shot_role", data)

    def test_filenames_contain_role(self):
        import tempfile
        from pathlib import Path
        from ai_blender_director.planner import write_shot_plan

        with tempfile.TemporaryDirectory() as tmp:
            with _without_openrouter():
                paths = write_shot_plan("any idea", Path(tmp), n_shots=2)
            names = [p.name for p in paths]
            self.assertTrue(any("establishing" in n or "action" in n or "close_up" in n for n in names))
