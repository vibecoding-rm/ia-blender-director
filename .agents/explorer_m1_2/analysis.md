# Video Assembly Analysis & Transition Recommendations

This report explores the `ia-blender-director` codebase to locate video assembly and shot specification logic, and provides concrete recommendations for refactoring the video concatenation engine to use `ffmpeg-python` with `xfade` transitions and a Ken Burns zoom/pan effect for static shots.

---

## 1. Current State Analysis

### 1.1 Video Assembly and Concatenation Locations
Video assembly and concatenation are performed in two primary areas of the codebase:

1. **`src/ai_blender_director/postproduction.py`**
   - **`produce_short(...)`**: Coordinates the entire post-production pipeline (adding the hook card, concatenating video clips, padding the video for TTS narration, mixing audio, and burning subtitles).
   - **`_concat_reencode(clips, output, *, fps)`**: A private helper that concatenates video clips by writing a temporary text file listing clip paths and executing FFmpeg via `subprocess.run()`. It performs a full re-encode to `libx264` with `yuv420p` pixel format to prevent playback corruption due to mismatching codecs/profiles between the hook card (generated in Python) and the clips rendered by Blender.

2. **`src/ai_blender_director/commands/video.py`**
   - **`assemble_video(...)`**: Assembles a glob pattern of PNG frames (`*.png`) into an MP4 video asynchronously using `asyncio.create_subprocess_exec()`.
   - **`concat_videos_async(...)`**: Concatenates a list of MP4 files asynchronously using FFmpeg's `concat` demuxer with `-c copy`.
   - **`assemble_frames_sync(...)`**: A synchronous CLI wrapper around FFmpeg to assemble a frame directory.
   - **`concat_videos_sync(...)`**: A synchronous CLI wrapper around the `concat` demuxer using `-c copy` with a temporary file list.

### 1.2 Current FFmpeg Invocation Analysis
Currently, FFmpeg is executed as a subprocess across multiple stages of the application. The table below lists the commands and arguments used:

| Location | Purpose | Subprocess Type | Key FFmpeg Arguments |
|---|---|---|---|
| `postproduction.py` (Line 86) | Pad video end | `subprocess.run` | `["ffmpeg", "-y", "-loglevel", "error", "-i", base, "-vf", "tpad=stop_mode=clone;stop_duration=...", "-c:v", "libx264", "-pix_fmt", "yuv420p", padded]` |
| `postproduction.py` (Line 134) | Concat & re-encode | `subprocess.run` | `["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", list_file, "-r", fps, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", output]` |
| `commands/video.py` (Line 19) | Async frame assembly | `asyncio.create_subprocess_exec` | `["ffmpeg", "-y", "-framerate", fps, "-pattern_type", "glob", "-i", "*.png", "-c:v", "libx264", "-pix_fmt", "yuv420p", output_file]` |
| `commands/video.py` (Line 77) | Async concat copy | `asyncio.create_subprocess_exec` | `["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_file]` |
| `sfx.py` (Line 57) | SFX synthesis | `subprocess.run` | `["ffmpeg", "-y", "-loglevel", "error", *recipe, path]` (e.g., uses `-f lavfi -i sine=...`) |
| `sfx.py` (Line 129) | Audio track mixing | `subprocess.run` | `["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", filters, "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", output]` |
| `branding.py` (Line 46) | Hook card generation | `subprocess.run` | `["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", card_png, "-vf", "zoompan=...", "-frames:v", frames, "-c:v", "libx264", "-pix_fmt", "yuv420p", output_mp4]` |
| `subtitles.py` (Line 88) | Burn subtitles | `subprocess.run` | `["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-vf", "subtitles=...", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", output]` |

#### Key Observation on Efficiency:
In `produce_short` (`postproduction.py`), the video is written to disk and re-encoded multiple times:
1. **Concat**: Decoded and re-encoded into `_base.mp4`.
2. **Padding**: `_base.mp4` is decoded and re-encoded into `_padded.mp4`.
3. **Audio mix**: Video track is copied from `_padded.mp4` into `_audio.mp4` (no re-encode).
4. **Subtitles**: `_audio.mp4` is decoded and re-encoded into `_final.mp4`.

This multi-stage pipeline invokes `ffmpeg` up to three distinct times for encoding the same video frames. It results in **unnecessary disk I/O**, **slower execution times**, and **cumulative video quality degradation**.

---

## 2. Models Analysis

### 2.1 ShotSpec Definition
The `ShotSpec` model is defined in `src/ai_blender_director/models.py` on line 21. It is a frozen Pydantic model (`model_config = {"frozen": True}`) representing a single shot parameter:

```python
class ShotSpec(BaseModel):
    model_config = {"frozen": True}

    scene: str = Field(..., max_length=140)
    style: str = Field(..., max_length=120)
    duration_seconds: int = Field(..., ge=1, le=60)
    fps: int = Field(..., ge=1, le=60)
    resolution: Resolution
    camera: CameraSpec
    lighting: str = Field(..., max_length=120)
    subject: str = Field(..., max_length=120)
    action: str = Field(..., max_length=160)
    weather: str | None = Field(None, max_length=80)
    seed: int = Field(..., ge=0, le=2_147_483_647)
    assets: AssetRefs = Field(default_factory=AssetRefs)
```

---

## 3. Transition Field & `ffmpeg-python` Refactor Recommendation

### 3.1 Updating `ShotSpec` for Transitions
To support transitions between shots, we recommend adding a `transition` field to `ShotSpec`.

First, define a reusable `TransitionSpec` model in `src/ai_blender_director/models.py`:

```python
from typing import Literal
from pydantic import BaseModel, Field

TransitionType = Literal[
    "fade", "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
    "circleopen", "circleclose", "rectcrop", "multiply",
    "dissolve", "pixelize", "radial", "hblur", "none"
]

class TransitionSpec(BaseModel):
    type: TransitionType = Field(default="none", description="FFmpeg xfade transition type")
    duration: float = Field(default=0.5, ge=0.0, le=5.0, description="Transition duration in seconds")
```

Then, update `ShotSpec` to include the `transition` field (representing the transition *after* this shot, moving to the next shot):

```python
class ShotSpec(BaseModel):
    # ... existing fields ...
    transition: TransitionSpec | None = Field(default_factory=TransitionSpec, description="Transition to the next shot")
```

#### LLM Schema Planning Update
To allow the AI Director to plan transitions, the scene planner schema (`_SCENE_SCHEMA` in `src/ai_blender_director/planner.py`) should be updated:

```python
_SCENE_SCHEMA = {
    # ...
    "shots": [
        {
            # ... existing fields ...
            "transition": {
                "type": "one of: fade, wipeleft, slideleft, circleopen, none",
                "duration": "float (e.g. 0.5)"
            }
        }
    ]
}
```

And update `_raw_item_to_shot(...)` in `planner.py` to extract this field:

```python
        "transition": item.get("transition", {"type": "none", "duration": 0.0}),
```

---

### 3.2 Refactoring Video Assembly to `ffmpeg-python`
`ffmpeg-python` provides a clean, type-safe API to construct complex filter graphs. We can build the **entire post-production pipeline** (concatenation, transitions, padding, audio mixing, ducking, and subtitle burning) in a **single, unified filter graph** that encodes the final video in **one single pass**.

#### 3.2.1 Unified Filter Graph Architecture
Instead of intermediate files, we compose the graph in Python:

```
[Clip 0] ──┐
           ├─► Concat/xfade ─► tpad ─► Subtitles ─► [Output Video Stream]
[Clip 1] ──┘                                               │
                                                           ├─► Output MP4
[Narration] ──► volume/delay ─────┐                        │
[Sting SFX] ──► volume ───────────┼─► amix ───────────────► [Output Audio Stream]
[Whoosh SFX] ─► volume/delay ─────┤
[Music Bed] ──► sidechaincompress ┘
```

#### 3.2.2 Unified Assembly Script Proposal

Here is the proposed implementation using `ffmpeg-python`:

```python
import ffmpeg
from pathlib import Path
from typing import List
from .models import ShotSpec

def assemble_short_with_ffmpeg_python(
    shot_videos: List[Path],
    shot_specs: List[ShotSpec],
    output_video: Path,
    *,
    hook_video: Path | None = None,
    hook_duration: float = 0.0,
    narration_wav: Path | None = None,
    narration_delay: float = 0.0,
    narration_duration: float = 0.0,
    subtitles_ass: Path | None = None,
    sfx_paths: dict = None,
    music_path: Path | None = None,
) -> bool:
    """Assembles the short, applying transitions, padding, subtitles, and mixing audio in a single pass."""
    
    # 1. Gather all video inputs and durations
    video_inputs = []
    durations = []
    transitions = []
    
    # Add hook if present
    if hook_video and hook_video.exists():
        video_inputs.append(ffmpeg.input(str(hook_video)).video)
        durations.append(hook_duration)
        # Hook transitions into the first shot with a hard cut (none) or fade
        transitions.append(ShotSpec.TransitionSpec(type="none", duration=0.0))
        
    for i, path in enumerate(shot_videos):
        video_inputs.append(ffmpeg.input(str(path)).video)
        spec = shot_specs[i]
        durations.append(float(spec.duration_seconds))
        # The last clip has no next clip, transition can be ignored or none
        transitions.append(spec.transition if i < len(shot_videos) - 1 else None)
        
    # 2. Build Video Concatenation & Transitions (xfade) Filter Graph
    current_v = video_inputs[0]
    accumulated_duration = durations[0]
    cut_times = []  # To calculate whoosh triggers at transition centers
    
    for i in range(len(video_inputs) - 1):
        next_v = video_inputs[i + 1]
        next_duration = durations[i + 1]
        t = transitions[i]
        
        # Calculate cut point
        if t and t.type != "none" and t.duration > 0:
            # Validate that transition duration doesn't exceed either clip duration
            trans_dur = min(t.duration, durations[i], next_duration)
            offset = accumulated_duration - trans_dur
            
            # Apply xfade
            current_v = ffmpeg.filter([current_v, next_v], 'xfade', transition=t.type, duration=trans_dur, offset=offset)
            
            # Transition center point for placing the whoosh SFX
            cut_times.append(offset + trans_dur / 2.0)
            accumulated_duration = accumulated_duration + next_duration - trans_dur
        else:
            # Hard cut: use concat filter
            current_v = ffmpeg.concat(current_v, next_v, v=1, a=0)
            cut_times.append(accumulated_duration)
            accumulated_duration = accumulated_duration + next_duration

    # 3. Calculate video padding (if narration is longer)
    total_video_duration = accumulated_duration
    narration_end = narration_delay + narration_duration
    pad = 0.0
    if narration_wav and narration_end > total_video_duration + 0.05:
        pad = narration_end - total_video_duration + 0.3
        current_v = current_v.filter('tpad', stop_mode='clone', stop_duration=pad)
        total_video_duration += pad

    # 4. Burn subtitles (ASS filter)
    if subtitles_ass and subtitles_ass.exists():
        # Escape path for FFmpeg filters (handles Windows backslashes)
        escaped_ass = str(subtitles_ass).replace("\\", "/").replace(":", "\\:")
        current_v = current_v.filter('subtitles', escaped_ass)

    # 5. Build Audio Mixing Pipeline
    audio_streams = []
    
    # A. Narration
    voice_ctrl = None
    if narration_wav and narration_wav.exists():
        narr_audio = ffmpeg.input(str(narration_wav)).audio
        delay_ms = int(narration_delay * 1000)
        narr_delayed = narr_audio.filter('volume', 1.0).filter('adelay', f"{delay_ms}|{delay_ms}")
        audio_streams.append(narr_delayed)
        # Use a copy of narration stream to drive sidechain compression on background music
        voice_ctrl = narr_delayed
        
    # B. Sting SFX (starts at 0.0)
    if sfx_paths and "sting" in sfx_paths:
        sting_audio = ffmpeg.input(str(sfx_paths["sting"])).audio.filter('volume', 0.9)
        audio_streams.append(sting_audio)
        
    # C. Whoosh SFX (triggered at transition centers)
    if sfx_paths and "whoosh" in sfx_paths:
        for t in cut_times:
            delay_ms = int(t * 1000)
            whoosh_audio = ffmpeg.input(str(sfx_paths["whoosh"])).audio.filter('volume', 0.6).filter('adelay', f"{delay_ms}|{delay_ms}")
            audio_streams.append(whoosh_audio)
            
    # D. Music Bed with Sidechain Ducking
    if music_path and music_path.exists():
        music_audio = ffmpeg.input(str(music_path)).audio
        if voice_ctrl:
            bgm_raw = music_audio.filter('volume', 0.25)
            # Sidechaincompress ducks bgm when voice_ctrl is active
            ducked = ffmpeg.filter([bgm_raw, voice_ctrl], 'sidechaincompress', threshold=0.05, ratio=4, attack=50, release=300)
            audio_streams.append(ducked)
        else:
            bgm = music_audio.filter('volume', 0.1)
            audio_streams.append(bgm)

    # 6. Assemble Output Node & Run
    output_opts = {
        'vcodec': 'libx264',
        'pix_fmt': 'yuv420p',
        'r': int(shot_specs[0].fps),
        'loglevel': 'error',
        'y': None
    }
    
    if audio_streams:
        # Mix all audios, normalise off, trim to match final video length
        mixed_audio = ffmpeg.filter(audio_streams, 'amix', inputs=len(audio_streams), normalize=0)
        trimmed_audio = mixed_audio.filter('atrim', duration=total_video_duration)
        
        output_opts['acodec'] = 'aac'
        output_node = ffmpeg.output(current_v, trimmed_audio, str(output_video), **output_opts)
    else:
        output_opts['an'] = None
        output_node = ffmpeg.output(current_v, str(output_video), **output_opts)
        
    # Compile arguments to integrate into async processes if needed
    # args = output_node.get_args()
    
    # Run the filtergraph in a single subprocess pass
    try:
        output_node.run(capture_stdout=True, capture_stderr=True)
        return output_video.exists()
    except ffmpeg.Error as e:
        print("FFmpeg error occurred:", e.stderr.decode('utf-8', errors='replace'))
        return False
```

---

## 4. xfade and zoompan Implementation Guidelines

### 4.1 xfade Transitions
FFmpeg's `xfade` filter handles transition transitions between two video streams.

#### How `xfade` Timings Work:
1. Stream A (`current_v`) and Stream B (`next_v`) overlap by `duration` seconds.
2. The `offset` argument determines the exact time in the *cumulative* output stream where Stream B begins to fade in.
3. Therefore, `offset = duration_of_A_so_far - transition_duration`.
4. The resulting stream length is `duration_A + duration_B - transition_duration`.

#### Codebase Integration:
Validate that the transition duration does not exceed the length of either clip in the validation layer (e.g., in `produce_short` or within `ShotSpec` configuration):

```python
# Validation check
if transition.duration > min(duration_A, duration_B):
    raise ShotValidationError("Transition duration cannot be longer than the clips themselves.")
```

---

### 4.2 zoompan (Ken Burns Effect) for Static Shots

#### The Optimization:
If a shot has a camera movement of `"static"`, instead of Blender rendering `N` identical frames (which is computationally expensive), we can:
1. Modify the Blender renderer to output only a **single frame** (e.g., frame 1 or the mid-shot frame).
2. Save it as a single PNG image.
3. Apply FFmpeg's `zoompan` filter to generate a full-length MP4 clip with the Ken Burns zoom/pan effect.

This cuts Blender render times for static shots by **95-98%** while achieving a highly professional dynamic camera feel in post-production.

#### zoompan Parametric Formula:
The `zoompan` filter format:
`zoompan=z='z_expr':x='x_expr':y='y_expr':d=frames:s=Wxh:fps=fps`

Here are the mathematical expressions for different presets:

1. **Zoom In (Centered)**:
   - `z`: `'1.0 + 0.1 * on / {frames}'` (zooms from 1.0 to 1.1)
   - `x`: `'(iw - iw/zoom)/2'`
   - `y`: `'(ih - ih/zoom)/2'`
   
2. **Zoom Out (Centered)**:
   - `z`: `'1.1 - 0.1 * on / {frames}'` (zooms from 1.1 down to 1.0)
   - `x`: `'(iw - iw/zoom)/2'`
   - `y`: `'(ih - ih/zoom)/2'`

3. **Pan Right**:
   - `z`: `'1.2'` (static zoom to allow panning margin)
   - `x`: `'(iw - iw/zoom) * (on / {frames})'` (slide from left edge to right)
   - `y`: `'(ih - ih/zoom)/2'` (centered vertically)

4. **Pan Left**:
   - `z`: `'1.2'`
   - `x`: `'(iw - iw/zoom) * (1 - on / {frames})'` (slide right-to-left)
   - `y`: `'(ih - ih/zoom)/2'`

5. **Zoom In & Pan Right**:
   - `z`: `'1.0 + 0.2 * on / {frames}'`
   - `x`: `'(iw - iw/zoom) * (on / {frames})'`
   - `y`: `'(ih - ih/zoom)/2'`

#### Implementing with `ffmpeg-python`:
To generate a video clip from a single static PNG image using `zoompan` and `ffmpeg-python`:

```python
def create_zoompan_clip(
    image_path: Path,
    output_video: Path,
    *,
    fps: int = 24,
    duration: float = 4.0,
    resolution: tuple[int, int] = (1080, 1920),
    effect: str = "zoom_in",
) -> bool:
    width, height = resolution
    total_frames = int(duration * fps)
    
    # 1. Loop single image as a raw input
    input_img = ffmpeg.input(str(image_path), loop=1, t=duration)
    
    # 2. Select expressions based on preset
    if effect == "zoom_in":
        z_expr = f"1.0 + 0.1 * on / {total_frames}"
        x_expr = "(iw - iw/zoom)/2"
        y_expr = "(ih - ih/zoom)/2"
    elif effect == "zoom_out":
        z_expr = f"1.1 - 0.1 * on / {total_frames}"
        x_expr = "(iw - iw/zoom)/2"
        y_expr = "(ih - ih/zoom)/2"
    elif effect == "pan_right":
        z_expr = "1.2"
        x_expr = f"(iw - iw/zoom) * (on / {total_frames})"
        y_expr = "(ih - ih/zoom)/2"
    elif effect == "pan_left":
        z_expr = "1.2"
        x_expr = f"(iw - iw/zoom) * (1 - on / {total_frames})"
        y_expr = "(ih - ih/zoom)/2"
    else:  # Static fallback
        z_expr = "1.0"
        x_expr = "0"
        y_expr = "0"

    # 3. Apply the zoompan filter
    zoomed = input_img.filter(
        'zoompan',
        z=z_expr,
        x=x_expr,
        y=y_expr,
        d=total_frames,
        s=f"{width}x{height}",
        fps=fps
    )
    
    # 4. Save video clip
    out = zoomed.output(
        str(output_video),
        vframes=total_frames,
        pix_fmt='yuv420p',
        vcodec='libx264',
        r=fps,
        **{'loglevel': 'error', 'y': None}
    )
    
    try:
        out.run()
        return output_video.exists()
    except ffmpeg.Error as e:
        print("Zoompan compilation failed:", e.stderr.decode('utf-8', errors='replace'))
        return False
```

#### Important Gotchas:
1. **Memory / Jitter**: Setting `d=total_frames` (which outputs all zoomed frames sequentially from the first input frame) is more stable and uses less memory in FFmpeg than looping the input image and doing a 1:1 frame zoom.
2. **Resolution Downscaling**: FFmpeg's `zoompan` filter has an internal default buffer resolution of 1280x720. If input images are vertical (e.g., 1080x1920) or larger, they may get downsampled first, resulting in pixelation.
   - **Fix**: Pre-scale the input image to a high resolution (or use the original source scale) and make sure `s={width}x{height}` is explicitly configured in the zoompan filter to force high-resolution output buffers.
