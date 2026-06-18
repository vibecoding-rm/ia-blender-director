"""Tests for tts.py — dispatch de motor y fallback a piper."""

import unittest
from pathlib import Path
from unittest.mock import patch

from ai_blender_director import tts


class TTSDispatchTest(unittest.TestCase):
    def test_piper_engine_calls_piper(self):
        with patch.object(tts, "_synthesize_piper", return_value=True) as mock_piper:
            ok = tts.synthesize("hola", Path("out.wav"), engine="piper")
        self.assertTrue(ok)
        mock_piper.assert_called_once()

    def test_unknown_engine_falls_back_to_piper(self):
        with patch.object(tts, "_synthesize_piper", return_value=True) as mock_piper:
            ok = tts.synthesize("hola", Path("out.wav"), engine="inexistente")
        self.assertTrue(ok)
        mock_piper.assert_called_once()

    def test_xtts_failure_falls_back_to_piper(self):
        with patch.object(tts, "_synthesize_xtts", return_value=False) as mock_xtts, \
             patch.object(tts, "_synthesize_piper", return_value=True) as mock_piper:
            ok = tts.synthesize("hola", Path("out.wav"), engine="xtts")
        self.assertTrue(ok)
        mock_xtts.assert_called_once()
        mock_piper.assert_called_once()

    def test_command_engine_requires_template(self):
        with patch.object(tts.settings, "tts_command", None), \
             patch.object(tts, "_synthesize_piper", return_value=True) as mock_piper:
            ok = tts.synthesize("hola", Path("out.wav"), engine="command")
        # sin plantilla, _synthesize_command falla → fallback a piper
        self.assertTrue(ok)
        mock_piper.assert_called_once()


if __name__ == "__main__":
    unittest.main()
