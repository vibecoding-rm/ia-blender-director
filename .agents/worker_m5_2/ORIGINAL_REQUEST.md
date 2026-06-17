## 2026-06-17T15:10:33Z

You are teamwork_preview_worker. Your working directory is C:\Users\Computops\Desktop\ia-blender-director\.agents\worker_m5_2.

Your task is to fix a frame rate mismatch bug in the `zoompan` filter implementation in `src/ai_blender_director/postproduction.py`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Background:
In `src/ai_blender_director/postproduction.py`, when a shot has camera movement defined as 'static', a `zoompan` filter is applied using `ffmpeg-python`. However, the filter lacks an explicit `fps` parameter, causing it to default to 25 fps. This mismatches the frame rate of other shots in the sequence (e.g. 24 fps), causing the subsequent `xfade` filter to crash with exit code -22 (Invalid argument) during transition assembly.

Specific requirements:
1. Inspect `src/ai_blender_director/postproduction.py` around the `zoompan` filter usage.
2. Modify the `zoompan` filter call to explicitly pass `fps=fps`.
3. Run the E2E verification test using:
   `C:\Python314\python.exe tests/test_transitions.py`
   Ensure that the test passes successfully (exits with 0).
4. Run all unit tests to make sure there are no regressions.
5. Write your handoff report to C:\Users\Computops\Desktop\ia-blender-director\.agents\worker_m5_2\handoff.md.

## 2026-06-17T15:11:15Z

Reviewer 2 has reported a verdict of REQUEST_CHANGES due to three issues:
1. **Integrity Violation (Self-Certifying Mock)**: In `tests/test_transitions.py`, the `ffprobe` duration mock is hardcoded to return `14.0` for the final video output. This must be refactored to compute the expected duration dynamically based on the input shot JSON spec files or the compiled ffmpeg stream filter graph to be a genuine test.
2. **Correctness Bug (Zoompan Frame Rate)**: The `zoompan` filter in `postproduction.py` defaults to 25 fps. Make sure to pass `fps=fps` to the `zoompan` filter call so it matches the project settings and doesn't distort segment durations.
3. **Correctness Bug (Audio Truncation)**: Muxing with `-shortest` in `src/ai_blender_director/sfx.py` cuts the final video short when the narration audio is shorter than the video (and no background music is present). Please fix this behavior.

Please implement fixes for all three of these issues, verify that the E2E verification test and unit tests pass, and document the changes in your handoff report.
