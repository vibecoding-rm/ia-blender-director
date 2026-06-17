# Handoff Report - Codebase Explorer 2

This report provides the read-only exploration results and recommendations for refactoring video assembly and shot specification logic to support transition and zoompan effects using `ffmpeg-python`.

---

## 1. Observation

During our read-only exploration, we made the following direct observations:

1. **ShotSpec Definition Location**:
   In `src/ai_blender_director/models.py` (line 21), `ShotSpec` is defined as a frozen Pydantic model:
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

2. **FFmpeg Subprocess Invocations in post-production**:
   In `src/ai_blender_director/postproduction.py`, FFmpeg is invoked directly using raw shell lists and `subprocess.run` across multiple stages:
   - **Concatenation** (Lines 134-139):
     ```python
     result = subprocess.run(
         ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
          "-i", str(list_file), "-r", str(fps),
          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(output)],
         capture_output=True,
     )
     ```
   - **Video Padding** (Lines 86-91):
     ```python
     result = subprocess.run(
         ["ffmpeg", "-y", "-loglevel", "error", "-i", str(base),
          "-vf", f"tpad=stop_mode=clone:stop_duration={pad:.3f}",
          "-c:v", "libx264", "-pix_fmt", "yuv420p", str(padded)],
         capture_output=True,
     )
     ```
   - Similar direct invocations exist in `sfx.py` (lines 57 and 129), `branding.py` (line 46), and `subtitles.py` (line 88).

3. **Multi-Pass Quality Loss & Overhead**:
   In `src/ai_blender_director/postproduction.py` (lines 23-128), video is processed sequentially: it re-encodes once in `_concat_reencode`, then re-encodes a second time in `tpad` padding, and a third time when burning subtitles in `burn_subtitles`. This results in cumulative rendering quality loss and significant disk/compute overhead.

4. **Dependencies**:
   `pyproject.toml` (lines 10-19) specifies dependencies, which do not include `ffmpeg-python`.

---

## 2. Logic Chain

1. **ShotSpec Update**:
   - Because `ShotSpec` (Observation 1) is loaded directly from planned JSON output (`planner.py:108`), adding a nested transition configuration will allow the LLM or client to describe the transition type and duration directly inside the shot files.
   - Pydantic's `BaseModel` allows adding optional fields with default values, which keeps the schema backwards-compatible with existing JSON shot plans.

2. **Refactoring to `ffmpeg-python`**:
   - Currently, several separate subprocess runs are executed to perform successive modifications on the video (Observation 2 & 3).
   - `ffmpeg-python` allows building a Directed Acyclic Graph (DAG) representing video and audio filters. By building a single unified filtergraph that chains `xfade` (transitions) -> `tpad` (padding) -> `subtitles` (subtitle burning) for the video, and mixes all narration/SFX/music for the audio, we can perform the entire assembly in a **single pass** of the FFmpeg encoder.
   - This eliminates up to two intermediate decode/re-encode steps, decreasing total post-production time and avoiding cumulative visual quality loss.

3. **Ken Burns Zoom/Pan for Static Shots**:
   - Static shots are defined with `camera.movement = "static"`. If we render a single frame instead of a full animation in Blender, we save substantial Blender rendering cycles.
   - FFmpeg's `zoompan` filter can loop a single static image and apply smooth mathematical transformations over the frame index (`on`), simulating a 3D zoom/pan effect. By incorporating this into the `ffmpeg-python` compilation pipeline, we can transform a static single frame into a fully-timed dynamic MP4 clip instantly.

---

## 3. Caveats

- **FFmpeg Binary Path**: The `ffmpeg-python` wrapper depends on a system-installed `ffmpeg` executable being available on the system `PATH`.
- **Memory Consumption of `zoompan`**: If zoompan parameters are not configured with a specific frame limit (`d` parameter), or if the input size is extremely high, FFmpeg can consume large amounts of memory or crash. Pre-scaling inputs is recommended to maintain stability.
- **Audio Sync**: The durations of the transitions reduce the overall video duration because of the overlapping frames. Timings of narration, music ducking, and transition whoosh sounds must be computed relative to the accumulated transition durations to avoid sync drift.

---

## 4. Conclusion

1. **ShotSpec Model Update**: We recommend adding an optional `transition: TransitionSpec` field to `ShotSpec`, defining `type` and `duration`, defaulting to `"none"` and `0.0`.
2. **Post-Production Refactor**: We recommend refactoring `postproduction.py` to build a single, unified graph via `ffmpeg-python`. This replaces multiple shell calls with a single-pass processing graph.
3. **Optimized Static Shots via Zoompan**: We recommend detecting static shots, rendering a single image from Blender, and generating the clip using the `zoompan` filter with `ffmpeg-python` preset formulas (Zoom In, Zoom Out, Pan Left/Right).

Detailed findings, code snippets, and mathematical equations have been written to `C:\Users\Computops\Desktop\ia-blender-director\.agents\explorer_m1_2\analysis.md`.

---

## 5. Verification Method

To independently verify the investigation findings:
1. View the detailed report file `C:\Users\Computops\Desktop\ia-blender-director\.agents\explorer_m1_2\analysis.md` which contains complete code implementations and filtergraph architectures.
2. Confirm the definition of `ShotSpec` at `src/ai_blender_director/models.py:21`.
3. Inspect `src/ai_blender_director/postproduction.py` to verify the multi-pass subprocess-driven structure.
