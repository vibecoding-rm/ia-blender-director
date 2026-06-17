# Handoff Report: Codebase Exploration for Video Transitions and Assembly

This report summarizes Codebase Explorer 1's findings and recommendations for the transition and video assembly refactoring.

---

## 1. Observation
We have inspected the workspace codebase and made the following observations:

* **Observation 1 (ShotSpec Definition):** `ShotSpec` is defined as a Pydantic `BaseModel` in `src/ai_blender_director/models.py` at line 21:
  ```python
  class ShotSpec(BaseModel):
      model_config = {"frozen": True}
  
      scene: str = Field(..., max_length=140)
      style: str = Field(..., max_length=120)
      ...
  ```
* **Observation 2 (Video Assembly subprocess):** Single-shot image sequences are assembled into MP4 in `src/ai_blender_director/commands/video.py` at line 9:
  ```python
  async def assemble_video(input_dir: Path, output_file: Path, fps: int = 24, broadcaster=None, job_id: str = "") -> bool:
      ...
      command = [
          "ffmpeg",
          "-y",
          "-framerate", str(fps),
          "-pattern_type", "glob",
          "-i", f"{input_dir}/*.png",
          "-c:v", "libx264",
          "-pix_fmt", "yuv420p",
          str(output_file)
      ]
      ...
      process = await asyncio.create_subprocess_exec(
          *command,
          stdout=asyncio.subprocess.PIPE,
          stderr=asyncio.subprocess.STDOUT
      )
  ```
* **Observation 3 (Video Concatenation subprocess):** Video concatenation is performed with re-encoding in `src/ai_blender_director/postproduction.py` at line 131:
  ```python
  def _concat_reencode(clips: list[Path], output: Path, *, fps: int) -> bool:
      list_file = output.with_suffix(".txt")
      list_file.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
      result = subprocess.run(
          ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
           "-i", str(list_file), "-r", str(fps),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(output)],
          capture_output=True,
      )
  ```
* **Observation 4 (Zoompan filter example):** A zoompan filter is used for the hook/title card in `src/ai_blender_director/branding.py` at lines 42-45:
  ```python
      zoom = (
          f"zoompan=z='1.10-0.10*on/{frames}':d={frames}"
          f":x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s={width}x{height}:fps={fps}"
      )
  ```
* **Observation 5 (Dependencies):** Dependencies are managed in `pyproject.toml` (lines 10-19), but `ffmpeg-python` is not currently listed.

---

## 2. Logic Chain
1. Since the current codebase calls raw FFmpeg subprocesses directly (Observation 2, Observation 3), wrapping this logic in the structured `ffmpeg-python` library will improve maintainability and enable complex filtering.
2. Because the `broadcaster` class requires asynchronous stdout/stderr output lines for live logging during assembly (Observation 2), compiling the `ffmpeg-python` stream graph via `ffmpeg.compile()` and running it with `asyncio.create_subprocess_exec` is the most seamless way to transition to the library without breaking progress reporting.
3. Adding a new optional nested `TransitionSpec` model (defining transition `name` and `duration`) and a `transition` field to `ShotSpec` (Observation 1) will allow users to customize transitions per shot while remaining backward-compatible.
4. Because the concatenation step in `_concat_reencode` is purely visual (`-an` flag, Observation 3), we can apply video-only `xfade` filter cascades in Python without dealing with audio offset alignment.
5. In addition, when clips overlap by $T_k$ during transitions, the visual midpoint of the transition shifts to $C_k - T_k/2$. Using this formula ensures that the Whoosh sound effects (managed in `mix_audio_track` under `postproduction.py`) are triggered at the correct visual transitions.
6. Since a static camera movement is defined by `camera.movement = "static"`, we can apply a `zoompan` Ken Burns filter during the shot frame-assembly phase (Observation 2) to cleanly output a pre-zoomed/panned MP4 shot, keeping the post-production concat step simple.

---

## 3. Caveats
- No actual source code changes were made as this is a read-only investigation.
- We assumed the target machine has the `ffmpeg` executable installed and accessible in the system PATH.
- `ffmpeg-python` will need to be installed in the project environment.

---

## 4. Conclusion
The codebase is ready for implementing `xfade` transitions and `zoompan` effects using `ffmpeg-python`. The proposed solution involves:
1. Adding `"ffmpeg-python>=0.2.0"` to the `dependencies` list in `pyproject.toml`.
2. Defining `TransitionSpec` and updating `ShotSpec` in `src/ai_blender_director/models.py`.
3. Refactoring `assemble_video(...)` in `src/ai_blender_director/commands/video.py` to compile using `ffmpeg-python` while maintaining its async interface.
4. Replacing the raw `_concat_reencode` demuxer in `src/ai_blender_director/postproduction.py` with a cascading `xfade` filter graph and adjusting whoosh SFX timings.
5. Modifying frame assembly to support `zoompan` filters for shots marked with `"static"`.

---

## 5. Verification Method
To verify the proposed changes once they are implemented:
1. **Dependency Installation:** Run `pip install ffmpeg-python` (or re-install via `pyproject.toml`).
2. **Unit Tests:** Execute the unit tests to ensure that the Pydantic model updates do not break validation:
   * **PowerShell (Windows):**
     ```powershell
     $env:PYTHONPATH="src"
     python -m unittest discover -s tests
     ```
   * **Bash (Linux/macOS):**
     ```bash
     PYTHONPATH=src python -m unittest discover -s tests
     ```
3. **Execution Verification:** Run the pipeline with transitions configured in a plan file (e.g. `examples/shots/smoke_test.json`) using:
   ```bash
   python -m ai_blender_director.cli render examples/shots/smoke_test.json
   ```
   Check the console output for FFmpeg command generation and inspect the resulting output video in `renders/` for visual transitions (e.g. `fade` or `wipeleft`) and Ken Burns effects on static shots.
