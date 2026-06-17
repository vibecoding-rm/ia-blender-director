# Codebase Exploration: Video Assembly & Transitions Recommendations

This report presents findings from a read-only investigation of the `ia-blender-director` codebase regarding video assembly, model definitions, and recommendations for implementing `xfade` transitions and `zoompan` (Ken Burns effect) using the `ffmpeg-python` library.

---

## 1. Analysis of Current Video Assembly & FFmpeg Invocations

FFmpeg is currently invoked via raw subprocesses (either synchronous `subprocess.run` or asynchronous `asyncio.create_subprocess_exec`) in several places across the codebase:

### A. Assembly of Individual Video Shots
* **Location:** `src/ai_blender_director/commands/video.py`
  * **Function:** `assemble_video(...)` (asynchronous, used in server pipeline) and `assemble_frames_sync(...)` (synchronous, used in CLI).
  * **FFmpeg Command:**
    ```bash
    ffmpeg -y -framerate {fps} -pattern_type glob -i "{input_dir}/*.png" -c:v libx264 -pix_fmt yuv420p {output_file}
    ```
  * **Mechanism:** The async version captures stdout/stderr line-by-line using a `readline()` loop on `asyncio.subprocess.PIPE` and forwards it to `broadcaster.add_log(job_id, ...)` for real-time UI logging.

### B. Concatenation of Video Shots (Post-Production)
* **Location:** `src/ai_blender_director/postproduction.py`
  * **Function:** `_concat_reencode(...)`
  * **FFmpeg Command:**
    ```bash
    ffmpeg -y -loglevel error -f concat -safe 0 -i {list_file} -r {fps} -c:v libx264 -pix_fmt yuv420p -an {output_file}
    ```
  * **Mechanism:** Writes a list of files to a temporary `.txt` file using the FFmpeg `concat` demuxer. It re-encodes the visual streams to match target visual parameters and drops audio using the `-an` flag. The audio track is mixed and overlaid later.
* **Location:** `src/ai_blender_director/commands/video.py`
  * **Functions:** `concat_videos_async(...)` and `concat_videos_sync(...)`
  * **FFmpeg Command:**
    ```bash
    ffmpeg -y -f concat -safe 0 -i {concat_list_file} -c copy {output_file}
    ```
  * **Mechanism:** Performs fast concatenation using the demuxer without re-encoding (`-c copy`).

### C. Hook Card (Title Card) Generation
* **Location:** `src/ai_blender_director/branding.py`
  * **Function:** `make_hook_clip(...)`
  * **FFmpeg Command:**
    ```bash
    ffmpeg -y -loglevel error -loop 1 -i {card_png} -vf "zoompan=..." -frames:v {frames} -c:v libx264 -pix_fmt yuv420p {output_mp4}
    ```
  * **Mechanism:** Converts a PIL-rendered PNG image into an MP4 clip with a zoom-out effect using the `zoompan` filter.

### D. Audio Mixing & Sound Effects (SFX)
* **Location:** `src/ai_blender_director/sfx.py`
  * **Function:** `mix_audio_track(...)`
  * **FFmpeg Command:** Utilizes complex filter graphs combining `amix`, `adelay`, `atrim`, `sidechaincompress` to overlay background music, speech, and sound effects (stings/whooshes).
* **Location:** `src/ai_blender_director/tts.py`
  * **Function:** `mux_narration(...)`
  * **FFmpeg Command:** Uses `tpad` filter to clone/freeze the last video frame if the TTS audio extends beyond the video duration.

---

## 2. Model Definitions (`ShotSpec`)

The models are defined in `src/ai_blender_director/models.py`. 
`ShotSpec` is a Pydantic `BaseModel` containing metadata about the shot:
* **Fields:** `scene`, `style`, `duration_seconds`, `fps`, `resolution` (nested `Resolution`), `camera` (nested `CameraSpec`), `lighting`, `subject`, `action`, `weather`, `seed`, and `assets` (nested `AssetRefs`).
* **Instantiation:** Custom `from_dict(cls, data)` method maps legacy top-level keys to nested objects for backward compatibility before validating.

---

## 3. Recommended Pydantic Model Updates

To support transitions and custom Ken Burns movements, we recommend adding:
1. A **`TransitionSpec`** sub-model.
2. A **`transition`** field to `ShotSpec`.
3. A **`zoompan`** field to `ShotSpec` (or inside `CameraSpec`).

### Code Snippet for `src/ai_blender_director/models.py`:

```python
# Add this model definition above ShotSpec
class TransitionSpec(BaseModel):
    name: str = Field(
        "fade", 
        max_length=40, 
        description="Name of the FFmpeg xfade transition (e.g., fade, wipeleft, slideup, circlecrop, pixelize)"
    )
    duration: float = Field(
        0.5, 
        ge=0.1, 
        le=5.0, 
        description="Duration of the transition in seconds"
    )

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
    
    # New Fields
    transition: TransitionSpec | None = Field(
        None, 
        description="Optional transition to apply AFTER this shot when concatenating with the next shot"
    )
    zoompan: str | None = Field(
        None, 
        pattern="^(in|out)$", 
        description="Optional Ken Burns effect ('in' or 'out') applied to static shots"
    )
```

---

## 4. Refactoring Video Assembly with `ffmpeg-python`

The `ffmpeg-python` library allows building a clean DAG (Directed Acyclic Graph) of video and audio streams. To keep real-time UI logging intact, we recommend using the `ffmpeg.compile()` API to generate the raw argument list and executing it with `asyncio.create_subprocess_exec`.

### Refactoring `assemble_video` in `src/ai_blender_director/commands/video.py`:

```python
import ffmpeg

async def assemble_video(input_dir: Path, output_file: Path, fps: int = 24, broadcaster=None, job_id: str = "") -> bool:
    if not input_dir.exists():
        msg = f"error: input directory {input_dir} not found."
        if broadcaster:
            broadcaster.add_log(job_id, msg + "\n")
        return False

    # Build the ffmpeg-python stream graph
    stream = (
        ffmpeg
        .input(f"{input_dir}/*.png", pattern_type="glob", framerate=fps)
        .output(str(output_file), vcodec="libx264", pix_fmt="yuv420p")
        .overwrite_output()
    )

    # Compile the graph into command line arguments
    command = ffmpeg.compile(stream)

    msg = f"Running: {' '.join(command)}\n"
    if broadcaster:
        broadcaster.add_log(job_id, msg)

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )

    while True:
        line = await process.stdout.readline()
        if not line:
            break
        decoded = line.decode('utf-8', errors='replace')
        if broadcaster:
            broadcaster.add_log(job_id, decoded)

    await process.wait()
    return process.returncode == 0
```

---

## 5. Implementing `xfade` Transitions

The `xfade` filter blends two video streams using an overlap period. To concatenate $N$ clips with transitions, we must chain `xfade` filters sequentially.

### The Mathematics of Transition Offsets
When overlapping clips with transitions:
1. Let $D_i$ be the duration of clip $i$.
2. Let $T_i$ be the transition duration between clip $i$ and clip $i+1$.
3. When combining the current accumulated stream (total duration $C_k$) with the next clip $k+1$, the transition must start at:
   $$O_k = C_k - T_k$$
4. The cumulative duration of the output stream increases to:
   $$C_{k+1} = C_k + D_{k+1} - T_k$$
5. For the sound effects (like whooshes) that trigger at the cuts, the visual midpoint of the transition is:
   $$\text{midpoint}_k = C_k - \frac{T_k}{2}$$

### python implementation for `_concat_reencode` in `src/ai_blender_director/postproduction.py`:

```python
def concat_with_transitions(
    clips: list[Path],
    durations: list[float],
    transitions: list[TransitionSpec | None],
    output: Path,
    resolution: tuple[int, int],
    fps: int
) -> tuple[bool, float, list[float]]:
    """
    Concatenates video clips with xfade transitions.
    Returns: (success_status, total_output_duration, adjusted_cut_times)
    """
    import ffmpeg
    width, height = resolution
    
    if not clips:
        return False, 0.0, []

    # 1. Standardize all input streams (vital for xfade filter compatibility)
    inputs = []
    for c in clips:
        in_stream = (
            ffmpeg
            .input(str(c))
            .filter('scale', width, height)
            .filter('fps', fps=fps)
            .filter('format', 'yuv420p')
        )
        inputs.append(in_stream)

    # 2. Iterate and chain xfade filters
    current_stream = inputs[0]
    current_duration = durations[0]
    cut_times = []
    
    for i in range(1, len(clips)):
        next_stream = inputs[i]
        next_duration = durations[i]
        
        # Determine transition details
        trans = transitions[i - 1]
        t_name = trans.name if trans else "fade"
        t_duration = trans.duration if trans else 0.01  # 0.01s is visually a cut, avoids empty filters

        # Offset is where the transition starts
        offset = current_duration - t_duration
        
        # The center of the transition is where a Whoosh SFX should trigger
        cut_times.append(round(current_duration - t_duration / 2, 3))
        
        # Apply xfade
        current_stream = ffmpeg.filter(
            [current_stream, next_stream],
            'xfade',
            transition=t_name,
            duration=t_duration,
            offset=offset
        )
        
        # Update cumulative duration
        current_duration = current_duration + next_duration - t_duration

    # 3. Output without audio (an) to let post-production mix audio separately
    output_stream = (
        current_stream
        .output(str(output), vcodec="libx264", pix_fmt="yuv420p", an=True)
        .overwrite_output()
    )

    try:
        ffmpeg.run(output_stream, capture_stdout=True, capture_stderr=True)
        return True, current_duration, cut_times
    except ffmpeg.Error as e:
        print(e.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
        return False, 0.0, []
```

---

## 6. Implementing `zoompan` (Ken Burns Effect)

Applying Ken Burns effect to a static shot is best integrated directly into the **frame assembly** stage (`assemble_video` or `assemble_frames_sync`), ensuring that the resulting shot MP4 is already zoomed/panned before entering the concatenation pipeline.

### Caveats of the FFmpeg `zoompan` Filter:
1. **Frame Rate:** The `zoompan` filter defaults to `25` fps output and expects `25` fps input. You must pass `fps=fps` as a parameter to avoid stuttering or rate mismatch.
2. **Output Size:** You must specify `s={width}x{height}` to force the zoomed canvas to render at the target aspect ratio, rather than defaulting to `640x480`.
3. **Panning Formula:** Keeps the center aligned by tracking `(iw-iw/zoom)/2`.

### Python Implementation for Zoompan during Frame Assembly:

```python
def assemble_shot_with_zoompan(
    input_dir: Path,
    output_file: Path,
    fps: int,
    duration_seconds: int,
    resolution: tuple[int, int],
    zoom_type: str | None = None
) -> bool:
    import ffmpeg
    width, height = resolution
    frames = duration_seconds * fps
    
    # 1. Define zoom expression based on zoom_type (in or out)
    if zoom_type == "in":
        z_expr = f"1.00+0.10*on/{frames}"
    elif zoom_type == "out":
        z_expr = f"1.10-0.10*on/{frames}"
    else:
        # Default frame assembly without zoompan
        return assemble_video_normal(input_dir, output_file, fps)

    x_expr = "(iw-iw/zoom)/2"
    y_expr = "(ih-ih/zoom)/2"

    # 2. Input sequence
    input_stream = ffmpeg.input(f"{input_dir}/*.png", pattern_type="glob", framerate=fps)

    # 3. Apply Zoompan
    zoomed_stream = ffmpeg.filter(
        input_stream,
        'zoompan',
        z=z_expr,
        x=x_expr,
        y=y_expr,
        d=frames,
        s=f"{width}x{height}",
        fps=fps
    )

    # 4. Output video
    output_stream = (
        zoomed_stream
        .output(str(output_file), vcodec="libx264", pix_fmt="yuv420p")
        .overwrite_output()
    )

    try:
        ffmpeg.run(output_stream, capture_stdout=True, capture_stderr=True)
        return True
    except ffmpeg.Error as e:
        print(e.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
        return False
```

---

## 7. Dependency Changes
* Add `"ffmpeg-python>=0.2.0"` to the `dependencies` list in `pyproject.toml`.
