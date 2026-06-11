"""Tests for commands/video.py sync assembly functions."""

from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch
import subprocess


class TestAssembleFramesSync(TestCase):
    def test_returns_false_when_no_frames(self):
        from ai_blender_director.commands.video import assemble_frames_sync
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmp:
            frames_dir = Path(tmp)
            output = frames_dir / "out.mp4"
            result = assemble_frames_sync(frames_dir, output, fps=24)
            self.assertFalse(result)

    def test_returns_true_when_ffmpeg_succeeds(self):
        from ai_blender_director.commands.video import assemble_frames_sync
        import tempfile
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            frames_dir = Path(tmp)
            # Create a dummy PNG so glob finds something
            img = Image.new("RGB", (4, 4), (100, 100, 100))
            img.save(frames_dir / "frame_0001.png")

            output = frames_dir / "out.mp4"
            mock_result = MagicMock()
            mock_result.returncode = 0

            with patch("subprocess.run", return_value=mock_result) as mock_run:
                result = assemble_frames_sync(frames_dir, output, fps=24)

            self.assertTrue(result)
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            self.assertIn("ffmpeg", call_args)
            self.assertIn("-framerate", call_args)

    def test_returns_false_when_ffmpeg_fails(self):
        from ai_blender_director.commands.video import assemble_frames_sync
        import tempfile
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            frames_dir = Path(tmp)
            img = Image.new("RGB", (4, 4))
            img.save(frames_dir / "frame_0001.png")

            output = frames_dir / "out.mp4"
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = b"error"

            with patch("subprocess.run", return_value=mock_result):
                result = assemble_frames_sync(frames_dir, output, fps=24)

            self.assertFalse(result)

    def test_custom_pattern(self):
        from ai_blender_director.commands.video import assemble_frames_sync
        import tempfile
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            frames_dir = Path(tmp)
            img = Image.new("RGB", (4, 4))
            img.save(frames_dir / "beauty_frame_0001.png")

            output = frames_dir / "out.mp4"
            mock_result = MagicMock()
            mock_result.returncode = 0

            with patch("subprocess.run", return_value=mock_result) as mock_run:
                assemble_frames_sync(frames_dir, output, pattern="beauty_frame_*.png")

            call_args = mock_run.call_args[0][0]
            self.assertTrue(any("beauty_frame_*.png" in str(a) for a in call_args))


class TestConcatVideosSync(TestCase):
    def test_returns_false_for_empty_list(self):
        from ai_blender_director.commands.video import concat_videos_sync
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "final.mp4"
            result = concat_videos_sync([], output)
            self.assertFalse(result)

    def test_returns_true_when_ffmpeg_succeeds(self):
        from ai_blender_director.commands.video import concat_videos_sync
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            v1 = tmp_path / "shot1.mp4"
            v2 = tmp_path / "shot2.mp4"
            v1.touch()
            v2.touch()
            output = tmp_path / "final.mp4"

            mock_result = MagicMock()
            mock_result.returncode = 0

            with patch("subprocess.run", return_value=mock_result) as mock_run:
                result = concat_videos_sync([v1, v2], output)

            self.assertTrue(result)
            call_args = mock_run.call_args[0][0]
            self.assertIn("ffmpeg", call_args)
            self.assertIn("concat", call_args)

    def test_concat_list_contains_both_files(self):
        from ai_blender_director.commands.video import concat_videos_sync
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            v1 = tmp_path / "shot1.mp4"
            v2 = tmp_path / "shot2.mp4"
            v1.touch()
            v2.touch()
            output = tmp_path / "final.mp4"

            mock_result = MagicMock()
            mock_result.returncode = 0
            written_content = []

            original_run = subprocess.run

            def capturing_run(args, **kwargs):
                # Read the concat list file passed with -i
                try:
                    i_idx = args.index("-i")
                    concat_file = Path(args[i_idx + 1])
                    if concat_file.exists():
                        written_content.append(concat_file.read_text())
                except (ValueError, IndexError):
                    pass
                return mock_result

            with patch("subprocess.run", side_effect=capturing_run):
                concat_videos_sync([v1, v2], output)

            if written_content:
                content = written_content[0]
                self.assertIn("shot1.mp4", content)
                self.assertIn("shot2.mp4", content)
