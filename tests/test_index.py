from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_blender_director.db import Base
from ai_blender_director.index import append_index_event, find_job_record, latest_job_records
from ai_blender_director.jobs import RenderJob


def _in_memory_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


class IndexTest(unittest.TestCase):
    def setUp(self):
        self._session_factory = _in_memory_session_factory()

    def _patch(self):
        return patch("ai_blender_director.index.SessionLocal", self._session_factory)

    def _make_job(self, root: Path, job_id: str = "job_001") -> RenderJob:
        return RenderJob(
            job_id=job_id,
            job_dir=root / "renders" / job_id,
            source_shot=root / "source.json",
            job_shot=root / "renders" / job_id / "shot.json",
            output_root=root / "renders",
            profile="preview",
        )

    def test_append_and_find_job(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job = self._make_job(root)
            index_path = root / "renders" / "index.jsonl"

            with self._patch():
                append_index_event(index_path, job, "created", status="created")
                append_index_event(index_path, job, "finished", status="completed", returncode=0)

                latest = latest_job_records(index_path)
                self.assertEqual(len(latest), 1)
                self.assertEqual(latest[0]["status"], "completed")
                self.assertEqual(latest[0]["returncode"], 0)

                found = find_job_record(index_path, "job_")
                self.assertIsNotNone(found)
                self.assertEqual(found["job_id"], "job_001")

    def test_multiple_jobs_latest_returns_all(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job_a = self._make_job(root, "job_a")
            job_b = self._make_job(root, "job_b")
            index_path = root / "renders" / "index.jsonl"

            with self._patch():
                append_index_event(index_path, job_a, "created", status="created")
                append_index_event(index_path, job_b, "created", status="created")

                latest = latest_job_records(index_path)
                self.assertEqual(len(latest), 2)

    def test_find_job_returns_none_for_unknown_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index_path = root / "renders" / "index.jsonl"

            with self._patch():
                found = find_job_record(index_path, "nonexistent")
                self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
