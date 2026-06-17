# Review and Handoff Report — 2026-06-17

## Review Summary

**Verdict**: **REQUEST_CHANGES**

*Note on Verdict*: While all 86 unit tests pass, we identified a critical integrity violation in the test suite where the mock in `tests/test_transitions.py` is self-certifying (hardcodes the expected output of `ffprobe` to `14.0` regardless of the actual implementation output). Furthermore, a major bug exists in the zoompan filter implementation which changes video durations for static shots when running at non-default frame rates (e.g. 12 fps claymation).

---

## Findings

### [Critical] Finding 1 — Integrity Violation: Self-Certifying Test Mock
- **What**: The mock setup in `tests/test_transitions.py` uses a hardcoded dictionary response for `ffprobe` duration calls, returning `14.0` for any path containing `'final'`.
- **Where**: `tests/test_transitions.py`, lines 195-205 (`get_mocked_duration`):
  ```python
  def get_mocked_duration(self, path: Path) -> float:
      name = path.name
      if 'shot_01' in name:
          return 5.0
      ...
      elif 'final' in name:
          return 14.0
      return 0.0
  ```
- **Why**: This is a facade implementation that masks bugs in the postproduction pipeline. If the actual duration calculation or filter graph in `produce_short` changes, or if it produces an empty file, the test still passes because the mocked `ffprobe` command always returns `14.0`. There is no inspection of the actual filter graph or compiled command arguments.
- **Suggestion**: Update `tests/test_transitions.py` to compile and assert against the actual ffmpeg filter graph arguments (similar to how `tests/test_postproduction.py` is written), or verify the mock returns values computed dynamically from the shot specifications.

### [Critical] Finding 2 — Incorrect Video Durations in Zoompan Filter (Ken Burns Effect)
- **What**: The `zoompan` filter in `postproduction.py` does not specify the `fps` parameter.
- **Where**: `src/ai_blender_director/postproduction.py`, lines 108-115:
  ```python
  v = v.filter(
      'zoompan',
      z=preset['z'],
      x=preset['x'],
      y=preset['y'],
      d=1,
      s=f"{resolution[0]}x{resolution[1]}"
  )
  ```
- **Why**: In FFmpeg, `zoompan` defaults to an output frame rate of 25 fps. When applied to static shots using `d=1` (mapping 1 input frame to 1 output frame), the frame count is preserved but the frame rate is changed.
  - At **12 fps** (the default claymation frame rate), a 4.0s shot has 48 frames. Zoompan outputs them at 25 fps, meaning the shot duration shrinks to `48 / 25 = 1.92` seconds (a 2.08x speedup). This causes narration/subtitles to drift and will make subsequent `xfade` transitions crash or freeze because the transition `offset` (e.g. at 3.0s) will exceed the actual video duration.
  - At **30 fps**, a 5.0s shot has 150 frames. Zoompan outputs them at 25 fps, meaning the duration stretches to `150 / 25 = 6.0` seconds (a 20% slowdown). The subsequent `xfade` transition will cut off the final 1.0s of the shot.
- **Suggestion**: Explicitly pass `fps=fps` to the `zoompan` filter parameters. Additionally, apply the `fps` filter (`v = v.filter('fps', fps=fps)`) to all standardized streams to prevent mismatched frame rates during concatenation.

### [Major] Finding 3 — Audio-Video Truncation via `-shortest` Global Argument
- **What**: The final output in `mix_audio_track` is muxed using `-shortest`.
- **Where**: `src/ai_blender_director/sfx.py`, line 126:
  ```python
  stream = ffmpeg.output(video_input.video, aout, str(output), vcodec='copy', acodec='aac').global_args('-shortest').overwrite_output()
  ```
- **Why**: When BGM (`MUSIC_BED`) is not present, the longest audio stream is the voice narration (which might be shorter than the total video). Because `-shortest` terminates the output file as soon as the shortest stream ends, the final video will be truncated to the narration length, cutting off the end of the video.
- **Suggestion**: Pad the narration/SFX audio stream to match the total video duration, or remove `-shortest` if the audio streams are guaranteed to be padded.

---

## Verified Claims

- **All tests pass** → Verified via `C:\Python314\python.exe -m unittest discover -s tests` → **PASS** (86 tests passed).
- **pyproject.toml specifies ffmpeg-python** → Verified via file inspection → **PASS** (line 19: `"ffmpeg-python>=0.2.0"`).
- **ShotSpec transition type validation** → Verified via running `tests/test_shot_spec.py` → **PASS** (validation raises `ShotValidationError` for invalid transition names).

---

## Coverage Gaps

- **Real ffmpeg execution** — High Risk — The test suite uses mocks exclusively due to ffmpeg not being installed in the environment path. This hides runtime execution quirks (such as `zoompan` output format issues and `xfade` crash conditions under mismatched durations).
- **`mix_audio_track` execution** — Medium Risk — No test calls `mix_audio_track` with actual SFX/narration enabled without mocking the entire function.

---

## Adversarial Challenge Report

### Assumption Stress-Testing
- **Assumption 1**: The video frame rates of input clips and filter operations automatically match.
  - *Failure Scenario*: Input is 12 fps (claymation style) and `zoompan` is applied. `zoompan` forces 25 fps.
  - *Blast Radius*: Segment plays at double speed, duration drops from 4.0s to 1.92s, subsequent transitions fail to compile or freeze on the final frame.
- **Assumption 2**: `test_transitions.py` validates the correctness of transition durations.
  - *Failure Scenario*: The implementation is broken and returns invalid durations or fails.
  - *Blast Radius*: The mock returns `14.0` regardless, hiding the bug.

### Stress Test results
- Compile 4 static shots at 30 fps using `check_graph.py` → **PASS** (filters like `zoom_in`, `zoom_out`, `pan_left`, `pan_right` compile syntactically, but duration metrics show a 20% mismatch on static segments).
- Compile 4 static shots at 12 fps → **FAIL** (actual stream durations would shrink, causing `xfade` offset mismatches).

---

## 5-Component Handoff

### 1. Observation
- **Test Command**: `C:\Python314\python.exe -m unittest discover -s tests`
- **Result**: `Ran 86 tests in 0.340s; OK`
- **Code Locations**:
  - `src/ai_blender_director/postproduction.py:108-115`: `zoompan` filter has no `fps` argument.
  - `tests/test_transitions.py:195-205`: `get_mocked_duration` returns `14.0` for `'final'`.
  - `src/ai_blender_director/sfx.py:126`: uses `.global_args('-shortest')`.

### 2. Logic Chain
1. We observed that the unit tests run under mock when `ffmpeg` is not in path.
2. In `test_transitions.py`, the mock returns hardcoded durations (`14.0` for output) instead of calculating them from the input streams or testing the filter graph.
3. This creates a self-certifying loop where the assertions pass regardless of the actual filter logic.
4. By inspecting the filter graph compilation in `postproduction.py`, we identified that `zoompan` filter is called without the `fps` option.
5. In FFmpeg, `zoompan` defaults to 25 fps. Setting `d=1` without `fps` alters the playback rate and segment durations, causing catastrophic desynchronization and failure at non-default rates (like 12 fps claymation).

### 3. Caveats
- No actual ffmpeg binary was available on the local path to execute the compiled graph on real files. Verification was performed by mocking, compiling filter graphs via `ffmpeg-python`, and code analysis.

### 4. Conclusion
The implementation is functionally incomplete and lacks robustness because static zoom/pan effects change segment durations and will cause rendering failures at 12 fps (the default claymation rate). The test suite contains an integrity violation by hardcoding expected outcomes in the mock, masking these duration defects.

### 5. Verification Method
1. Run the test suite: `C:\Python314\python.exe -m unittest discover -s tests`.
2. Inspect `tests/test_transitions.py` line 203 to verify `get_mocked_duration` returns hardcoded `14.0`.
3. Check `src/ai_blender_director/postproduction.py` line 108 to verify `zoompan` lacks `fps` configuration.
