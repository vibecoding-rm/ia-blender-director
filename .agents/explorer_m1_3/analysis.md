# Codebase Analysis & Recommendations: Video Assembly, transitions, and zoompan

**Prepared by**: Codebase Explorer 3  
**Status**: Complete  
**Date**: 2026-06-17  

---

## 1. Executive Summary
This report presents the findings of a read-only codebase exploration of the `ia-blender-director` project. The objective is to analyze the current video assembly and concatenation processes, locate where key Pydantic models are defined, and provide detailed recommendations on:
1. Adding transition metadata to the `ShotSpec` model.
2. Refactoring video assembly and hook-card generation to use the `ffmpeg-python` library.
3. Implementing advanced video effects, specifically `xfade` (crossfade transitions) and `zoompan` (Ken Burns effect) for static shots, with a focus on math, audio synchronization, quality optimization, and Blender rendering efficiency.

---

## 2. Current Video Assembly and FFmpeg Subprocesses

### 2.1 File Locations & Entry Points
Video assembly and concatenation are performed in two primary places:
1. **`src/ai_blender_director/postproduction.py`**: Handles the high-level compilation of the short (including prepending hook card, concatenating clips with re-encoding, padding last frame if narration is long, mixing audio/SFX, and burning subtitles).
2. **`src/ai_blender_director/commands/video.py`**: Contains utility functions for frame assembly and video concatenation used by the CLI and background jobs.

### 2.2 Current FFmpeg Subprocess Invocations

#### A. Post-production Padding (`postproduction.py` lines 86-91)
If the TTS narration goes beyond the video duration, the last frame of the video is padded/frozen using `tpad`:
```python
subprocess.run(
    ["ffmpeg", "-y", "-loglevel", "error", "-i", str(base),
     "-vf", f"tpad=stop_mode=clone:stop_duration={pad:.3f}",
     "-c:v", "libx264", "-pix_fmt", "yuv420p", str(padded)],
    capture_output=True,
)
```

#### B. Concatenation with Re-encoding (`postproduction.py` lines 134-139)
Concatenates individual shot clips. Because the hook clip and Blender-rendered shots may use different H.264 profile settings, standard concatenation without re-encoding (`-c copy`) might cause corruption. Re-encoding ensures metadata/resolution alignment:
```python
subprocess.run(
    ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
     "-i", str(list_file), "-r", str(fps),
     "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(output)],
    capture_output=True,
)
```
*Note: `-an` disables the audio track at this stage; audio mixing is done separately in `sfx.py`.*

#### C. Hook Clip Generation with Zoom-out (`branding.py` lines 46-51)
Creates a 1.4-second breaking news title card with a slow zoom-out effect:
```python
zoom = (
    f"zoompan=z='1.10-0.10*on/{frames}':d={frames}"
    f":x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s={width}x{height}:fps={fps}"
)
subprocess.run(
    ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(card_png),
     "-vf", zoom, "-frames:v", str(frames),
     "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output_mp4)],
    capture_output=True,
)
```

#### D. Utility Frame Assembly (`commands/video.py` lines 19-40 and lines 116-125)
Assembles sequential PNG images into an MP4 video using the `glob` pattern type:
- **Async** (for web servers/websockets): uses `asyncio.create_subprocess_exec`.
- **Sync** (for CLI): uses `subprocess.run`.
```python
args = [
    "ffmpeg", "-y",
    "-framerate", str(fps),
    "-pattern_type", "glob",
    "-i", str(frames_dir / pattern),
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    str(output_file),
]
```

#### E. Straight Concatenation (Copy Mode) (`commands/video.py` lines 77-85 and lines 142-149)
Concatenates MP4 files via the concat demuxer without re-encoding (`-c copy`).
```python
args = [
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", tmp.name,
    "-c", "copy",
    str(output_file),
]
```

---

## 3. ShotSpec Model Definition

The `ShotSpec` model is defined in `src/ai_blender_director/models.py` (lines 21-55). It is a frozen Pydantic V2 model representing a single shot specification.

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

It contains fields nested inside `Resolution`, `CameraSpec`, and `AssetRefs`, and it enforces validation using Pydantic's metadata (e.g., limits on duration, FPS, and string lengths).

---

## 4. Recommendations for Refactoring with `ffmpeg-python`

### 4.1 Dependency Addition
First, add `ffmpeg-python` to `pyproject.toml` under the `dependencies` list:
```toml
dependencies = [
    "Pillow>=10.0.0",
    "fastapi>=0.100.0",
    "uvicorn>=0.20.0",
    "google-genai>=0.2.0",
    "sqlalchemy>=2.0.0",
    "websockets>=11.0.0",
    "pydantic-settings>=2.0.0",
    "openai>=1.0.0",
    "ffmpeg-python>=0.2.0",  # Added ffmpeg-python wrapper
]
```

### 4.2 Updating models.py with Transition Support
To enable custom transitions between shots, define a `TransitionSpec` model and add it to `ShotSpec`.

#### In `src/ai_blender_director/models.py`:
```python
class TransitionSpec(BaseModel):
    model_config = {"frozen": True}
    
    type: str = Field("fade", max_length=40, description="Transition name: fade, wipeleft, slideup, etc.")
    duration: float = Field(1.0, ge=0.1, le=5.0, description="Transition duration in seconds")

class ShotSpec(BaseModel):
    # ... (existing fields)
    transition: TransitionSpec | None = Field(None, description="Transition to apply after this shot")
```
Adding `transition: TransitionSpec | None = Field(None)` ensures 100% backwards compatibility; existing shot JSON files without a `transition` key will validate and set the field to `None` (representing a straight cut).

#### In `src/ai_blender_director/planner.py` (updating generator):
In `_raw_item_to_shot`, ensure transition info from LLM generation parses correctly:
```python
def _raw_item_to_shot(item: dict, index: int, base_prompt: str, ...) -> dict[str, Any]:
    # ... (existing mapping)
    transition = item.get("transition")
    transition_dict = None
    if transition and transition.get("type"):
        transition_dict = {
            "type": transition.get("type", "fade"),
            "duration": float(transition.get("duration", 1.0))
        }
        
    return {
        # ...
        "transition": transition_dict,
    }
```
Also update the LLM instruction schema `_SCENE_SCHEMA` in `planner.py` to allow the LLM to output transition keys.

---

## 5. Implementation of Advanced Video Effects

### 5.1 xfade Transitions (Crossfade)

The FFmpeg `xfade` filter requires overlapping video streams.
- If `clipA` is `5s` and `clipB` is `5s`, and the transition is `1s`, the total duration of the combined video is `5 + 5 - 1 = 9s`.
- The `xfade` filter takes an `offset` argument representing when the transition begins, measured from the start of the first input stream.

#### Timeline Mathematics for Chaining Multiple xfades:
To chain `N` clips, we must track the accumulated duration and dynamically calculate the offset for each transition.
Let `d_i` be the duration of clip `i`, and `t_i` be the duration of the transition between clip `i` and clip `i+1`.

1. For `i = 0` (first transition):
   $$\text{offset}_0 = d_0 - t_0$$
   The output stream of this first xfade filter has an accumulated duration of:
   $$\text{acc\_dur}_1 = d_0 + d_1 - t_0$$
2. For subsequent clip `i+1`:
   $$\text{offset}_{i} = \text{acc\_dur}_i - t_i$$
   The new accumulated duration becomes:
   $$\text{acc\_dur}_{i+1} = \text{acc\_dur}_i + d_{i+1} - t_i$$

#### Audio Sync (Cut Times & Whooshes)
Currently, `whoosh` sound effects play exactly at the cuts. For crossfade transitions, the audio transition (whoosh) should center around the visual midpoint of the transition.
- **Midpoint calculation**: The transition between clip `i` and clip `i+1` starts at `clip_start[i] + d_i - t_i`. The midpoint (center) of this transition is:
  $$\text{cut\_time}_i = \text{clip\_start}[i] + d_i - \frac{t_i}{2}$$
- **Clip start times calculation**:
  $$\text{clip\_start}[0] = 0.0$$
  $$\text{clip\_start}[i+1] = \text{clip\_start}[i] + d_i - t_i$$

#### Refactored `_concat_reencode` and `produce_short` in `postproduction.py`:
Here is the proposed Python implementation using `ffmpeg-python`:
```python
import ffmpeg
from pathlib import Path

def _assemble_clips_with_xfade(
    clips: list[Path],
    durations: list[float],
    transitions: list[TransitionSpec | None],
    output: Path,
    fps: int,
    resolution: tuple[int, int],
) -> tuple[bool, list[float]]:
    """Assembles video clips using ffmpeg-python. Handles xfade and straight cuts.
    
    Returns:
        (success_bool, cut_times_for_sfx)
    """
    width, height = resolution
    
    # 1. Normalize all inputs to same resolution, FPS, and pixel format
    normalized_streams = []
    for c in clips:
        stream = ffmpeg.input(str(c))
        # Ensure scaling and frame rate are consistent to avoid xfade filter errors
        stream = ffmpeg.filter(stream, 'scale', width, height)
        stream = ffmpeg.filter(stream, 'fps', fps=fps)
        normalized_streams.append(stream)
        
    # 2. Iterate and apply transitions
    current_video = normalized_streams[0]
    accumulated_duration = durations[0]
    
    clip_starts = [0.0] * len(clips)
    cut_times = []
    
    for i in range(len(clips) - 1):
        next_video = normalized_streams[i+1]
        trans = transitions[i]
        
        if trans and trans.duration > 0:
            trans_duration = trans.duration
            trans_type = trans.type
            
            # Transition center point for the whoosh SFX
            cut_time = clip_starts[i] + durations[i] - (trans_duration / 2.0)
            cut_times.append(round(cut_time, 3))
            
            # Start of next clip
            clip_starts[i+1] = clip_starts[i] + durations[i] - trans_duration
            
            # Apply xfade
            offset = accumulated_duration - trans_duration
            current_video = ffmpeg.filter(
                [current_video, next_video],
                'xfade',
                transition=trans_type,
                duration=trans_duration,
                offset=offset
            )
            
            # Update accumulated duration
            accumulated_duration = accumulated_duration + durations[i+1] - trans_duration
        else:
            # Straight cut (standard concat)
            cut_time = clip_starts[i] + durations[i]
            cut_times.append(round(cut_time, 3))
            
            clip_starts[i+1] = clip_starts[i] + durations[i]
            
            # Concat filter in ffmpeg-python
            current_video = ffmpeg.concat(current_video, next_video, v=1, a=0)
            accumulated_duration = accumulated_duration + durations[i+1]

    # 3. Compile output (disable audio -an, as SFX is mixed in later)
    out = ffmpeg.output(
        current_video,
        str(output),
        vcodec='libx264',
        pix_fmt='yuv420p',
        an=True,
        loglevel='error'
    ).overwrite_output()
    
    try:
        out.run()
        return output.exists(), cut_times
    except ffmpeg.Error as e:
        print(f"ffmpeg-python error: {e.stderr.decode(errors='replace') if e.stderr else str(e)}")
        return False, []
```

---

### 5.2 Zoompan (Ken Burns Effect) for Static Shots

The `zoompan` filter creates motion inside static video clips or single-image renders. However, invoking it directly on low or medium resolution video clips can lead to severe aliasing, pixelation, and shaking/jitter.

#### A. Quality Optimization (Double Resolution Scaling)
To eliminate pixelation and jitter:
1. **Upscale** the input stream to at least $2\times$ the target resolution (or a high fixed resolution like 4K).
2. **Apply `zoompan`** at this higher resolution.
3. **Downscale** back to the target resolution (`width` $\times$ `height`).

#### B. Ensuring Video Compatibility (`d=1`)
By default, the `zoompan` filter converts a single input frame into a sequence. When processing a video sequence frame-by-frame, we must set the duration parameter `d=1`. This instructs FFmpeg to map 1 input frame to exactly 1 output frame.
To make the zoom occur over the whole video, we pass the total frame count ($N = \text{duration} \times \text{fps}$) into the expressions and use the `on` (one-based frame number) variable.

#### C. Zoom and Pan Expressions

- **Zoom In (Center-focused)**:
  - Zoom expression `z`: `1.0 + 0.3 * (on / N)` (zooms in from 1.0 to 1.3).
  - Coordinates `x`, `y` (keeps center focused):
    - `x = (iw - iw/zoom)/2`
    - `y = (ih - ih/zoom)/2`
- **Zoom Out (Center-focused)**:
  - Zoom expression `z`: `1.3 - 0.3 * (on / N)` (zooms out from 1.3 to 1.0).
  - Coordinates `x`, `y`:
    - `x = (iw - iw/zoom)/2`
    - `y = (ih - ih/zoom)/2`
- **Pan Right (Zoomed)**:
  - Zoom expression `z`: `1.25` (pre-zoomed).
  - Coordinates `x`, `y` (pans horizontally from left to right):
    - `x = ((zoom-1)*iw/zoom) * (on / N)`
    - `y = (ih - ih/zoom)/2`
- **Pan Left (Zoomed)**:
  - Zoom expression `z`: `1.25`.
  - Coordinates `x`, `y` (pans horizontally from right to left):
    - `x = ((zoom-1)*iw/zoom) * (1.0 - (on / N))`
    - `y = (ih - ih/zoom)/2`
- **Pan Down (Zoomed)**:
  - Zoom expression `z`: `1.25`.
  - Coordinates `x`, `y` (pans vertically from top to bottom):
    - `x = (iw - iw/zoom)/2`
    - `y = ((zoom-1)*ih/zoom) * (on / N)`
- **Pan Up (Zoomed)**:
  - Zoom expression `z`: `1.25`.
  - Coordinates `x`, `y` (pans vertically from bottom to top):
    - `x = (iw - iw/zoom)/2`
    - `y = ((zoom-1)*ih/zoom) * (1.0 - (on / N))`

#### D. Python Implementation of Zoompan Effect
```python
def apply_zoompan_effect(
    stream: ffmpeg.nodes.FilterableStream,
    effect: str,
    fps: int,
    duration: float,
    resolution: tuple[int, int]
) -> ffmpeg.nodes.FilterableStream:
    """Applies high-quality zoompan (Ken Burns) effect on a video stream."""
    width, height = resolution
    N = int(duration * fps)
    
    # 1. Scale up to 2x resolution to eliminate aliasing/jitter
    scaled_up = ffmpeg.filter(stream, 'scale', width * 2, height * 2)
    
    # 2. Determine formulas based on effect type
    if effect == "zoom_in":
        z = f"1.0 + 0.3 * (on / {N})"
        x = "(iw - iw/zoom)/2"
        y = "(ih - ih/zoom)/2"
    elif effect == "zoom_out":
        z = f"1.3 - 0.3 * (on / {N})"
        x = "(iw - iw/zoom)/2"
        y = "(ih - ih/zoom)/2"
    elif effect == "pan_right":
        z = "1.25"
        x = f"((zoom-1)*iw/zoom) * (on / {N})"
        y = "(ih - ih/zoom)/2"
    elif effect == "pan_left":
        z = "1.25"
        x = f"((zoom-1)*iw/zoom) * (1.0 - (on / {N}))"
        y = "(ih - ih/zoom)/2"
    elif effect == "pan_down":
        z = "1.25"
        x = "(iw - iw/zoom)/2"
        y = f"((zoom-1)*ih/zoom) * (on / {N})"
    elif effect == "pan_up":
        z = "1.25"
        x = "(iw - iw/zoom)/2"
        y = f"((zoom-1)*ih/zoom) * (1.0 - (on / {N}))"
    else:
        # No motion effect, return scaled original
        return stream

    # 3. Apply zoompan filter at 2x resolution
    zoomed = ffmpeg.filter(
        scaled_up,
        'zoompan',
        z=z,
        x=x,
        y=y,
        d=1,  # Set d=1 to keep 1-to-1 video frame mapping
        s=f'{width * 2}x{height * 2}',
        fps=fps
    )
    
    # 4. Scale down to target resolution
    return ffmpeg.filter(zoomed, 'scale', width, height)
```

#### E. Performance Optimization: Blender Rendering Avoidance
Rendering a multi-second animation in Blender is extremely slow and resource-heavy. If a shot is static (i.e. has no character animation and the camera movement is a simulated post-production effect):
1. **Instruct Blender to render a single frame** instead of the entire sequence.
   - We can run Blender with `--preview-only` flag or modify `configure_render` to render only the middle frame.
2. **Read that single image frame into FFmpeg** as an image input.
3. **Use the `zoompan` filter directly on the static image** in FFmpeg to generate the full `duration_seconds * fps` video sequence.
   - Setting `-loop 1 -t duration` allows FFmpeg to treat the single frame as a loop, and `zoompan` will animate it directly during post-production.
   
This completely bypasses rendering 100+ frames in Blender for still scenes, achieving a **90%+ rendering speedup** while maintaining high-quality camera motion.

---

## 6. Refactoring Hook Clip Generation (`make_hook_clip` in `branding.py`)
To keep video processing consistent, the hook clip card generation should also be refactored using `ffmpeg-python`:
```python
def make_hook_clip_refactored(
    title: str,
    output_mp4: Path,
    *,
    resolution: tuple[int, int],
    fps: int,
    duration: float = 1.4,
) -> bool:
    """Generates the hook card clip with a clean zoom-out effect using ffmpeg-python."""
    width, height = resolution
    card = _render_card(title, width, height)
    card_png = output_mp4.with_suffix(".png")
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    card.save(card_png)

    frames = max(2, int(duration * fps))
    zoom_expr = f"1.10 - 0.10 * (on / {frames})"
    
    # Input looping static png
    input_stream = ffmpeg.input(str(card_png), loop=1, t=duration)
    
    # Apply quality scale optimization
    scaled_up = ffmpeg.filter(input_stream, 'scale', width * 2, height * 2)
    zoomed = ffmpeg.filter(
        scaled_up,
        'zoompan',
        z=zoom_expr,
        x='(iw-iw/zoom)/2',
        y='(ih-ih/zoom)/2',
        d=1,
        s=f'{width * 2}x{height * 2}',
        fps=fps
    )
    scaled_down = ffmpeg.filter(zoomed, 'scale', width, height)
    
    out = ffmpeg.output(
        scaled_down,
        str(output_mp4),
        vcodec='libx264',
        pix_fmt='yuv420p',
        vframes=frames,
        loglevel='error'
    ).overwrite_output()
    
    try:
        out.run()
        card_png.unlink(missing_ok=True)
        return output_mp4.exists()
    except ffmpeg.Error as e:
        print(f"error: hook clip generation failed: {e.stderr.decode(errors='replace') if e.stderr else str(e)}")
        return False
```
