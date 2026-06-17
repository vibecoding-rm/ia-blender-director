import os
import sys
from pathlib import Path
import tempfile
import json
import ffmpeg

# Set python path
project_root = Path("C:/Users/Computops/Desktop/ia-blender-director")
sys.path.insert(0, str(project_root / 'src'))

ffmpeg_bin = r"C:\Users\Computops\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
if os.path.exists(ffmpeg_bin):
    os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ["PATH"]

from ai_blender_director.postproduction import produce_short

def generate_dummy_video(path: Path, color: str, duration: float, fps: int = 24, resolution: tuple[int, int] = (1280, 720)):
    width, height = resolution
    stream = ffmpeg.input(f"color=c={color}:s={width}x{height}:d={duration}", f="lavfi")
    stream = ffmpeg.output(stream, str(path), r=fps, vcodec="libx264", pix_fmt="yuv420p")
    ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

def run_debug():
    resolution = (1280, 720)
    fps = 24
    durations = [4.0, 3.0, 5.0]

    with tempfile.TemporaryDirectory() as tmp_dir:
        work_dir = Path(tmp_dir)
        shot1_dir = work_dir / "shot_1"
        shot2_dir = work_dir / "shot_2"
        shot3_dir = work_dir / "shot_3"
        shot1_dir.mkdir()
        shot2_dir.mkdir()
        shot3_dir.mkdir()

        shot1_video = shot1_dir / "video.mp4"
        shot2_video = shot2_dir / "video.mp4"
        shot3_video = shot3_dir / "video.mp4"

        generate_dummy_video(shot1_video, "red", durations[0], fps, resolution)
        generate_dummy_video(shot2_video, "green", durations[1], fps, resolution)
        generate_dummy_video(shot3_video, "blue", durations[2], fps, resolution)

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

        (shot1_dir / "shot.json").write_text(json.dumps(shot1_spec), encoding="utf-8")
        (shot2_dir / "shot.json").write_text(json.dumps(shot2_spec), encoding="utf-8")
        (shot3_dir / "shot.json").write_text(json.dumps(shot3_spec), encoding="utf-8")

        output_video = work_dir / "assembled_output.mp4"

        # Instead of produce_short directly, let's replicate the ffmpeg-python construction and print it
        # Load specs
        from ai_blender_director.models import ShotSpec
        from ai_blender_director.io import load_shot_spec
        
        shot_videos = [shot1_video, shot2_video, shot3_video]
        shot_specs = [load_shot_spec(sv.parent / "shot.json") for sv in shot_videos]
        
        ZOOM_PRESETS = {
            'zoom_in': {
                'z': 'min(1.0+0.0015*on,1.5)',
                'x': 'iw/2-(iw/zoom/2)',
                'y': 'ih/2-(ih/zoom/2)'
            },
            'zoom_out': {
                'z': 'max(1.5-0.0015*on,1.0)',
                'x': 'iw/2-(iw/zoom/2)',
                'y': 'ih/2-(ih/zoom/2)'
            },
            'pan_left': {
                'z': '1.3',
                'x': '(iw-iw/zoom)*max(1.0-on/100,0.0)',
                'y': 'ih/2-(ih/zoom/2)'
            },
            'pan_right': {
                'z': '1.3',
                'x': '(iw-iw/zoom)*min(on/100,1.0)',
                'y': 'ih/2-(ih/zoom/2)'
            }
        }

        video_streams = []
        for i, clip_path in enumerate(shot_videos):
            input_node = ffmpeg.input(str(clip_path))
            v = input_node.video
            
            spec = shot_specs[i]
            if spec and spec.camera.movement.lower() == 'static':
                preset_keys = list(ZOOM_PRESETS.keys())
                preset_name = preset_keys[i % len(preset_keys)]
                preset = ZOOM_PRESETS[preset_name]
                print(f"Applying zoompan '{preset_name}' on clip {i}")
                v = v.filter(
                    'zoompan',
                    z=preset['z'],
                    x=preset['x'],
                    y=preset['y'],
                    d=1,
                    s=f"{resolution[0]}x{resolution[1]}",
                    fps=fps
                )
            
            v = v.filter('scale', w=resolution[0], h=resolution[1])
            v = v.filter('setsar', sar='1/1')
            v = v.filter('settb', tb='1/1000000')
            v = v.filter('setpts', 'PTS-STARTPTS')
            video_streams.append(v)

        # Transitions
        transitions = [(spec.transition.type, spec.transition.duration) for spec in shot_specs[:-1]]
        transitions.append(('none', 0.0))
        
        current_v = video_streams[0]
        accumulated_duration = durations[0]
        
        for i in range(len(shot_videos) - 1):
            t_type, t_dur = transitions[i]
            v_next = video_streams[i+1]
            
            if t_type == 'none' or t_dur <= 0:
                current_v = ffmpeg.concat(current_v, v_next, v=1, a=0)
                accumulated_duration += durations[i+1]
            else:
                offset = accumulated_duration - t_dur
                print(f"Applying transition '{t_type}' duration={t_dur} offset={offset}")
                current_v = ffmpeg.filter((current_v, v_next), 'xfade', transition=t_type, duration=t_dur, offset=offset)
                accumulated_duration = accumulated_duration + durations[i+1] - t_dur

        base = work_dir / "base.mp4"
        stream = ffmpeg.output(current_v, str(base), vcodec='libx264', pix_fmt='yuv420p', an=None).overwrite_output()
        
        cmd = ffmpeg.compile(stream)
        print("FFmpeg command:")
        print(" ".join(cmd))
        
        try:
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
            print("Success!")
        except ffmpeg.Error as e:
            print("FFmpeg failed!")
            print("Stdout:")
            print(e.stdout.decode('utf-8', errors='replace'))
            print("Stderr:")
            print(e.stderr.decode('utf-8', errors='replace'))

if __name__ == "__main__":
    run_debug()
