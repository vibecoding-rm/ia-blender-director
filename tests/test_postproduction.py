import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock
import ffmpeg

from ai_blender_director.postproduction import produce_short
from ai_blender_director.models import ShotSpec, CameraSpec, Resolution, TransitionSpec

class PostProductionTest(unittest.TestCase):
    @patch("ai_blender_director.postproduction.make_hook_clip")
    @patch("ai_blender_director.postproduction.synthesize")
    @patch("ai_blender_director.postproduction.media_duration")
    @patch("ai_blender_director.postproduction.mix_audio_track")
    @patch("ai_blender_director.io.load_shot_spec")
    @patch("ffmpeg.run")
    def test_produce_short_compiles_correct_filters(
        self,
        mock_ffmpeg_run,
        mock_load_spec,
        mock_mix_audio,
        mock_media_duration,
        mock_synthesize,
        mock_make_hook
    ) -> None:
        # Setup mock returns
        mock_make_hook.return_value = True
        mock_synthesize.return_value = True
        mock_media_duration.return_value = 5.0
        
        def mock_mix_audio_side_effect(video, output, **kwargs):
            Path(output).touch()
            return True
        mock_mix_audio.side_effect = mock_mix_audio_side_effect
        
        spec1 = ShotSpec(
            scene="scene 1",
            style="cinematic",
            duration_seconds=4,
            fps=24,
            resolution=Resolution(width=1280, height=720),
            camera=CameraSpec(movement="static", lens_mm=35),
            lighting="soft",
            subject="cotorra",
            action="speaks",
            seed=42,
            transition=TransitionSpec(type="fade", duration=1.0)
        )
        spec2 = ShotSpec(
            scene="scene 2",
            style="cinematic",
            duration_seconds=4,
            fps=24,
            resolution=Resolution(width=1280, height=720),
            camera=CameraSpec(movement="orbit", lens_mm=50),
            lighting="bright",
            subject="cerdo",
            action="runs",
            seed=43,
            transition=TransitionSpec(type="none", duration=0.0)
        )
        mock_load_spec.side_effect = [spec1, spec2]

        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            shot1_mp4 = work_dir / "shot_01.mp4"
            shot2_mp4 = work_dir / "shot_02.mp4"
            shot1_mp4.touch()
            shot2_mp4.touch()
            (work_dir / "shot.json").touch()
            
            output_mp4 = work_dir / "final.mp4"
            
            res = produce_short(
                shot_videos=[shot1_mp4, shot2_mp4],
                shot_durations=[4.0, 4.0],
                output_video=output_mp4,
                resolution=(1280, 720),
                fps=24,
                hook_title="breaking news",
                narration_text="test narration which is long enough",
                voice=None,
                subtitles=True,
                sfx=True
            )
            
            self.assertIsNotNone(res)
            mock_ffmpeg_run.assert_called_once()
            
            compiled_args = ffmpeg.compile(mock_ffmpeg_run.call_args[0][0])
            arg_str = " ".join(compiled_args)
            
            self.assertIn("zoompan", arg_str)
            self.assertIn("xfade", arg_str)
            self.assertIn("ass", arg_str)


if __name__ == "__main__":
    unittest.main()
