from __future__ import annotations

import argparse
import unittest
from unittest.mock import patch

from ai_blender_director.commands.management import handle_preflight


class PreflightTest(unittest.TestCase):
    def test_preflight_fails_when_required_binaries_are_missing(self) -> None:
        args = argparse.Namespace(check_comfy=False)

        with patch("ai_blender_director.commands.management._resolve_blender_executable", return_value=None), \
             patch("ai_blender_director.commands.management.shutil.which", return_value=None):
            self.assertEqual(handle_preflight(args), 2)


if __name__ == "__main__":
    unittest.main()
