"""Tests for render_shot_to_job."""

import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch


_MINIMAL_SHOT = {
    "scene": "test scene",
    "style": "cinematic",
    "duration_seconds": 4,
    "fps": 24,
    "resolution": {"width": 1280, "height": 720},
    "camera": {"movement": "static", "lens_mm": 35},
    "lighting": "soft",
    "subject": "hero",
    "action": "stands still",
    "weather": None,
    "seed": 12345,
}


class TestRenderShotToJob(TestCase):
    def _write_shot(self, tmp_dir: Path) -> Path:
        shot = tmp_dir / "test_shot.json"
        shot.write_text(json.dumps(_MINIMAL_SHOT), encoding="utf-8")
        return shot

    def test_returns_error_when_blender_not_found(self):
        from ai_blender_director.commands.render import render_shot_to_job

        with tempfile.TemporaryDirectory() as tmp:
            shot = self._write_shot(Path(tmp))
            output_root = Path(tmp) / "renders"

            with patch("shutil.which", return_value=None):
                code, job = render_shot_to_job(
                    shot, output_root, "preview",
                    output_root / "index.jsonl", dry_run=False,
                )

            self.assertEqual(code, 2)
            self.assertIsNone(job)

    def test_dry_run_creates_job_without_blender(self):
        from ai_blender_director.commands.render import render_shot_to_job

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            shot = self._write_shot(tmp_path)
            output_root = tmp_path / "renders"
            index_path = tmp_path / "index.jsonl"

            with patch("shutil.which", return_value="/usr/bin/blender"):
                code, job = render_shot_to_job(
                    shot, output_root, "preview", index_path, dry_run=True,
                )

            self.assertEqual(code, 0)
            self.assertIsNotNone(job)
            self.assertTrue(job.job_dir.exists())
            # index_path is kept for API compat but index is stored in SQLite
            self.assertTrue((job.job_dir / "job.json").exists())

    def test_run_render_shot_is_wrapper(self):
        from ai_blender_director.commands.render import run_render_shot, render_shot_to_job

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            shot = self._write_shot(tmp_path)
            output_root = tmp_path / "renders"
            index_path = tmp_path / "index.jsonl"

            with patch("shutil.which", return_value="/usr/bin/blender"):
                code_wrapper = run_render_shot(
                    shot, output_root, "preview", index_path, dry_run=True,
                )
                # reset for second call
                shot2 = self._write_shot(tmp_path)
                code_inner, _ = render_shot_to_job(
                    shot2, output_root, "preview", index_path, dry_run=True,
                )

            self.assertEqual(code_wrapper, code_inner)

    def test_failed_render_returns_nonzero(self):
        from ai_blender_director.commands.render import render_shot_to_job

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            shot = self._write_shot(tmp_path)
            output_root = tmp_path / "renders"
            index_path = tmp_path / "index.jsonl"

            mock_result = MagicMock()
            mock_result.returncode = 1

            with patch("shutil.which", return_value="/usr/bin/blender"), \
                 patch("subprocess.run", return_value=mock_result):
                code, job = render_shot_to_job(
                    shot, output_root, "preview", index_path, dry_run=False,
                )

            self.assertNotEqual(code, 0)
            self.assertIsNotNone(job)
