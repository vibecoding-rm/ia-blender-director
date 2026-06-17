# Handoff Report: Read-Only Exploration of Video Assembly, Transitions, and Zoompan

**Working Directory**: `C:\Users\Computops\Desktop\ia-blender-director\.agents\explorer_m1_3`  
**Archetype**: Codebase Explorer 3  
**Roles**: Investigator, Reporter  

---

## 1. Observation

### Video Assembly & FFmpeg Call Analysis
We observed multiple raw `subprocess.run` and `asyncio.create_subprocess_exec` invocations executing FFmpeg commands across the codebase.
- **`src/ai_blender_director/postproduction.py`**:
  - Line 86: Extends the last frame when TTS narration is longer than the video:
    ```python
    result = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(base),
         "-vf", f"tpad=stop_mode=clone:stop_duration={pad:.3f}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(padded)],
        capture_output=True,
    )
    ```
  - Line 134: Concatenates video files with re-encoding:
    ```python
    result = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(list_file), "-r", str(fps),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(output)],
        capture_output=True,
    )
    ```
- **`src/ai_blender_director/branding.py`**:
  - Line 46: Generates a hook card with a slow zoom-out effect:
    ```python
    zoom = (
        f"zoompan=z='1.10-0.10*on/{frames}':d={frames}"
        f":x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s={width}x{height}:fps={fps}"
    )
    result = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(card_png),
         "-vf", zoom, "-frames:v", str(frames),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output_mp4)],
        capture_output=True,
    )
    ```
- **`src/ai_blender_director/commands/video.py`**:
  - Line 19 and Line 116: Assemble sequential PNG images into video files using glob pattern matching (`-pattern_type glob -i <input_dir>/*.png`).
  - Line 77 and Line 142: Concatenate MP4 files without re-encoding using the copy codec (`-c copy`).

### Model Definitions
- **`src/ai_blender_director/models.py`**:
  - Line 21 defines the `ShotSpec` model:
    ```python
    class ShotSpec(BaseModel):
        model_config = {"frozen": True}
        # ...
    ```
  - `ShotSpec` is a frozen Pydantic V2 model validating all fields.
- **`src/ai_blender_director/planner.py`**:
  - Line 15 imports `ShotSpec`.
  - Line 107-108 performs validation of LLM output:
    ```python
    for shot in shots:
        ShotSpec.from_dict(shot)
    ```
  - Line 177: defines the `_raw_item_to_shot` helper mapping fields to dictionaries before validation.

### Project Dependencies
- **`pyproject.toml`**:
  - Lines 10-19 list dependencies. Currently does not include `ffmpeg-python`.

---

## 2. Logic Chain

1. **Re-encoding vs. Copying**: Currently, `postproduction.py` re-encodes concatenated clips to ensure parameters match, which prevents video corruption. When transitions (`xfade`) are introduced, re-encoding is mandatory because cross-fading requires raw frame access. However, `commands/video.py` copies files directly (`-c copy`) for speed when formatting match is assured.
2. **Backward Compatibility**: To add transitions, `ShotSpec` needs a `transition` field. By setting `transition: TransitionSpec | None = Field(None)`, Pydantic will default it to `None` for old files, preserving compatibility.
3. **Timeline Mathematics**: When applying `xfade`, clips overlap. If clip `i` and clip `i+1` have transition duration `t_i`, the next clip starts at offset `clip_start[i] + duration[i] - t_i`. The total duration is reduced. Therefore, the visual center of transition `i` is at `clip_start[i] + duration[i] - t_i / 2`. Sound effects (whooshes) currently mapped to straight cut times must be shifted to this center point to remain synchronized.
4. **Aliasing and Jitter in Zoompan**: The raw FFmpeg `zoompan` filter suffers from subpixel rendering issues resulting in visual jitter. Scaling up the input by $2\times$ before applying `zoompan` and scaling it down afterwards produces clean subpixel interpolations.
5. **Video Compatiblity in Zoompan**: Setting `d=1` on the `zoompan` filter is required when applying it to a video sequence to prevent FFmpeg from multiplying or dropping frames.
6. **Blender Render Avoidance**: If a shot is static, rendering 100+ identical frames in Blender is redundant. We can render a single frame (using `--preview-only`), loop it, and apply zoompan in post-production via FFmpeg to achieve a huge speedup (90%+).

---

## 3. Caveats
- **Testing Environment**: The test suite could not be run locally during exploration because the global Python environment (3.14) lacks `pydantic` and other requirements, and there is no local virtual environment (`.venv`) initialized in the workspace.
- **FFmpeg Executable**: All recommendations assume that a compiled FFmpeg binary is installed and present in the host system's `PATH`.

---

## 4. Conclusion
The codebase is well-structured for these updates. The `ShotSpec` model can be cleanly extended with a nested `TransitionSpec` model while maintaining backward compatibility. Using the `ffmpeg-python` library allows for a cleaner, object-oriented representation of the video pipeline, removing raw shell commands.
Implementing `xfade` transitions requires recursively computing accumulated offset values and updating SFX whoosh cut times to the transition midpoints. Applying `zoompan` requires double-scale padding to prevent alias artifacts and `d=1` configuration for video streams. Still-image looping can be used to optimize Blender rendering times for static shots.

Detailed implementation guides and code templates are written to `C:\Users\Computops\Desktop\ia-blender-director\.\.agents\explorer_m1_3\analysis.md`.

---

## 5. Verification Method

### Testing the Proposed Changes
1. **Adding Dependencies**: Add `ffmpeg-python>=0.2.0` to `pyproject.toml` and rebuild the virtual environment.
2. **Pydantic Validation**:
   - Save a test shot JSON containing a transition object, e.g.:
     ```json
     {
       "scene": "test scene",
       "style": "cinematic",
       "duration_seconds": 4,
       "fps": 24,
       "resolution": {"width": 1280, "height": 720},
       "camera": {"movement": "static", "lens_mm": 35},
       "lighting": "studio",
       "subject": "cube",
       "action": "spins",
       "seed": 1234,
       "transition": {"type": "fade", "duration": 1.0}
     }
     ```
   - Verify that this validates successfully using Python.
   - Verify that a JSON file without a transition field validates successfully and sets the field to `None`.
3. **Unit Tests Execution**:
   - Run the unit tests to ensure no regressions:
     ```bash
     $env:PYTHONPATH="src"
     python -m unittest discover -s tests
     ```
4. **Integration Validation**:
   - Run the command to compile a short concept plan:
     ```bash
     python -m ai_blender_director.cli generate "test concept"
     ```
   - Verify that `produce_short` completes without FFmpeg errors.
