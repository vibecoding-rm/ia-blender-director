from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class DatabaseInitializationTest(unittest.TestCase):
    def test_import_does_not_create_renders_directory(self) -> None:
        import ai_blender_director.db as db

        with tempfile.TemporaryDirectory() as directory:
            db_dir = Path(directory) / "renders"

            with patch.object(db, "DB_DIR", db_dir), \
                 patch.object(db, "DB_PATH", db_dir / "jobs.db"), \
                 patch.object(db, "_engine", None), \
                 patch.object(db, "_session_factory", None):
                self.assertFalse(db_dir.exists())
                db.ensure_database()
                db.get_engine().dispose()

            self.assertTrue(db_dir.exists())


if __name__ == "__main__":
    unittest.main()
