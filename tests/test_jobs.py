from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ai_blender_director.jobs import create_render_job, update_render_job_status


class RenderJobTest(unittest.TestCase):
    def test_create_render_job_copies_shot_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shot_path = root / "shot.json"
            shot_path.write_text(
                json.dumps(
                    {
                        "scene": "minimal cinematic stage",
                        "style": "cinematic",
                        "duration_seconds": 1,
                        "fps": 8,
                        "resolution": {"width": 640, "height": 360},
                        "camera": {"movement": "static", "lens_mm": 35},
                        "lighting": "soft studio light",
                        "subject": "test subject",
                        "action": "moves across the frame",
                        "weather": None,
                        "seed": 1,
                    }
                ),
                encoding="utf-8",
            )

            job = create_render_job(shot_path, root / "renders")

            self.assertTrue(job.job_dir.exists())
            self.assertTrue(job.job_shot.exists())
            self.assertTrue(job.manifest_path.exists())
            manifest = json.loads(job.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "created")
            self.assertEqual(manifest["shot"]["scene"], "minimal cinematic stage")

            update_render_job_status(job, "completed", returncode=0)
            manifest = json.loads(job.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["returncode"], 0)


if __name__ == "__main__":
    unittest.main()
