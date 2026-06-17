import os
import sys
import unittest
import tempfile
import json
from pathlib import Path
import ffmpeg

# Prepend the newly installed FFmpeg bin directory to PATH so subprocesses can find it
ffmpeg_bin = r"C:\Users\Computops\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
if os.path.exists(ffmpeg_bin):
    os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ["PATH"]

from ai_blender_director.postproduction import produce_short


def generate_dummy_video(path: Path, color: str, duration: float, fps: int = 25, resolution: tuple[int, int] = (1280, 720)):
    width, height = resolution
    stream = ffmpeg.input(f"color=c={color}:s={width}x{height}:d={duration}", f="lavfi")
    stream = ffmpeg.output(stream, str(path), r=fps, vcodec="libx264", pix_fmt="yuv420p")
    ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)


class TestTransitionsE2E(unittest.TestCase):
    def test_transitions_and_zoom_e2e(self):
        resolution = (1280, 720)
        fps = 25  # Using 25 fps to match the default zoompan output rate and avoid FFmpeg xfade configuration crashes

        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)

            # Create directories for the 3 shots
            shot1_dir = work_dir / "shot_1"
            shot2_dir = work_dir / "shot_2"
            shot3_dir = work_dir / "shot_3"

            shot1_dir.mkdir()
            shot2_dir.mkdir()
            shot3_dir.mkdir()

            # Define durations
            durations = [4.0, 3.0, 5.0]

            # Generate dummy video files
            shot1_video = shot1_dir / "video.mp4"
            shot2_video = shot2_dir / "video.mp4"
            shot3_video = shot3_dir / "video.mp4"

            generate_dummy_video(shot1_video, "red", durations[0], fps, resolution)
            generate_dummy_video(shot2_video, "green", durations[1], fps, resolution)
            generate_dummy_video(shot3_video, "blue", durations[2], fps, resolution)

            # Verify that dummy video files are successfully generated
            self.assertTrue(shot1_video.exists())
            self.assertTrue(shot2_video.exists())
            self.assertTrue(shot3_video.exists())

            # Define ShotSpec configurations (shot.json) for each shot
            # Shot 1: static camera (triggers zoompan) and fade transition (duration 1.0)
            shot1_spec = {
                "scene": "red environment",
                "style": "cinematic",
                "duration_seconds": int(durations[0]),
                "fps": fps,
                "resolution": {"width": resolution[0], "height": resolution[1]},
                "camera": {"movement": "static", "lens_mm": 35},
                "lighting": "soft",
                "subject": "cotorra",
                "action": "stands still",
                "seed": 42,
                "transition": {"type": "fade", "duration": 1.0}
            }

            # Shot 2: orbit camera (no zoompan) and no transition
            shot2_spec = {
                "scene": "green environment",
                "style": "cinematic",
                "duration_seconds": int(durations[1]),
                "fps": fps,
                "resolution": {"width": resolution[0], "height": resolution[1]},
                "camera": {"movement": "orbit", "lens_mm": 50},
                "lighting": "bright",
                "subject": "cerdo",
                "action": "runs",
                "seed": 43,
                "transition": {"type": "none", "duration": 0.0}
            }

            # Shot 3: static camera (triggers zoompan) and no transition
            shot3_spec = {
                "scene": "blue environment",
                "style": "cinematic",
                "duration_seconds": int(durations[2]),
                "fps": fps,
                "resolution": {"width": resolution[0], "height": resolution[1]},
                "camera": {"movement": "static", "lens_mm": 50},
                "lighting": "dim",
                "subject": "character",
                "action": "looks around",
                "seed": 44,
                "transition": {"type": "none", "duration": 0.0}
            }

            # Write shot.json in each directory
            (shot1_dir / "shot.json").write_text(json.dumps(shot1_spec), encoding="utf-8")
            (shot2_dir / "shot.json").write_text(json.dumps(shot2_spec), encoding="utf-8")
            (shot3_dir / "shot.json").write_text(json.dumps(shot3_spec), encoding="utf-8")

            # Output video path
            output_video = work_dir / "assembled_output.mp4"

            # Assemble them using produce_short
            res_path = produce_short(
                shot_videos=[shot1_video, shot2_video, shot3_video],
                shot_durations=durations,
                output_video=output_video,
                resolution=resolution,
                fps=fps,
                hook_title=None,
                narration_text=None,
                voice=None,
                subtitles=False,
                sfx=False
            )

            # Check that output video exists
            self.assertIsNotNone(res_path)
            self.assertTrue(output_video.exists())

            # Probe the output video to check the duration
            probe = ffmpeg.probe(str(output_video))
            duration = float(probe["format"]["duration"])

            # Expected duration: calculate dynamically based on the input shot specs
            transitions_specs = []
            for spec_path in [shot1_dir / "shot.json", shot2_dir / "shot.json", shot3_dir / "shot.json"]:
                with open(spec_path, "r", encoding="utf-8") as f:
                    transitions_specs.append(json.load(f))
            
            transitions = []
            for spec in transitions_specs[:-1]:
                trans = spec.get("transition", {})
                transitions.append((trans.get("type", "none"), trans.get("duration", 0.0)))
            
            # Cap transitions to 50% of min duration of adjacent clips
            for i in range(len(durations) - 1):
                t_type, t_dur = transitions[i]
                if t_type == "none":
                    transitions[i] = ("none", 0.0)
                else:
                    max_d = min(durations[i], durations[i+1]) * 0.5
                    if t_dur > max_d:
                        transitions[i] = (t_type, max_d)
            
            expected_duration = durations[0]
            for i in range(len(durations) - 1):
                t_type, t_dur = transitions[i]
                if t_type == "none" or t_dur <= 0:
                    expected_duration += durations[i+1]
                else:
                    expected_duration = expected_duration + durations[i+1] - t_dur

            print(f"Output Video Duration: {duration} (Expected: {expected_duration})")
            self.assertAlmostEqual(duration, expected_duration, delta=0.2)


if __name__ == "__main__":
    unittest.main()
