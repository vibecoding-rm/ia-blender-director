from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_blender_director.index import append_index_event, find_job_record, latest_job_records, read_index
from ai_blender_director.jobs import RenderJob


class IndexTest(unittest.TestCase):
    def test_append_and_read_index_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job = RenderJob(
                job_id="job_001",
                job_dir=root / "renders" / "job_001",
                source_shot=root / "source.json",
                job_shot=root / "renders" / "job_001" / "shot.json",
                output_root=root / "renders",
                profile="preview",
            )

            index_path = root / "renders" / "index.jsonl"
            append_index_event(index_path, job, "created", status="created")
            append_index_event(index_path, job, "finished", status="completed", returncode=0)

            records = read_index(index_path)

            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["event"], "created")
            self.assertEqual(records[1]["status"], "completed")
            self.assertEqual(records[1]["returncode"], 0)

            latest = latest_job_records(index_path)
            self.assertEqual(len(latest), 1)
            self.assertEqual(latest[0]["status"], "completed")

            found = find_job_record(index_path, "job_")
            self.assertIsNotNone(found)
            self.assertEqual(found["job_id"], "job_001")


if __name__ == "__main__":
    unittest.main()
