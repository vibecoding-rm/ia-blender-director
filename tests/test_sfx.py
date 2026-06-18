from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_blender_director.sfx import mix_audio_track


class MixAudioTrackTest(unittest.TestCase):
    def test_mix_audio_uses_loudness_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "video.mp4"
            narration = root / "narration.wav"
            output = root / "out.mp4"
            video.touch()
            narration.touch()

            mock_result = MagicMock()
            mock_result.returncode = 0

            def fake_run(args, **kwargs):
                output.touch()
                return mock_result

            with patch("ai_blender_director.sfx.ensure_sfx", return_value={}), \
                 patch("subprocess.run", side_effect=fake_run) as mock_run:
                self.assertTrue(
                    mix_audio_track(
                        video,
                        output,
                        narration_wav=narration,
                        narration_delay=0.0,
                        cut_times=[],
                        with_sting=False,
                    )
                )

            args = mock_run.call_args[0][0]
            arg_str = " ".join(args)
            self.assertIn("loudnorm", arg_str)
            self.assertIn("I=-14", arg_str)
            self.assertIn("-b:a", args)
            self.assertIn("192k", args)


if __name__ == "__main__":
    unittest.main()
