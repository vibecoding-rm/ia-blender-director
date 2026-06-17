# Handoff Report

## 1. Observation
While running the test suite with the command:
```powershell
$env:PYTHONPATH="src"; C:\Python314\python.exe -m unittest discover -v -s tests
```
The integration test `test_transitions.py` failed with the following traceback:
```
test_transitions_and_zoom_e2e (test_transitions.TestTransitionsE2E.test_transitions_and_zoom_e2e) ... error: video assembly falló: ating thread with return code -22 (Invalid argument)
[out#0/mp4 @ 0000019334117a80] Nothing was written into output file, because at least one of its streams received no packets.
frame=    0 fps=0.0 q=0.0 Lsize=       0KiB time=N/A bitrate=N/A speed=N/A elapsed=0:00:00.06    
Conversion failed!

FAIL
...
AssertionError: unexpectedly None
```

By reproducing the failure and outputting the full `ffmpeg` stderr stream, we observed that:
- When a shot has a camera movement of `'static'`, the `zoompan` filter is applied:
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
- The `zoompan` filter defaults its output framerate to 25 fps if not specified.
- The adjacent shots that have camera movements other than `'static'` do not go through the `zoompan` filter and keep their original framerate (e.g., 24 fps).
- The transition filter (`xfade`) fails to execute because the input links have mismatched frame rates:
```
[Parsed_xfade_9 @ 000002c791635940] First input link main frame rate (25/1) do not match the corresponding second input link xfade frame rate (24/1)
[Parsed_xfade_9 @ 000002c791635940] Failed to configure output pad on Parsed_xfade_9
[fc#0 @ 000002c78d074600] Error reinitializing filters!
[fc#0 @ 000002c78d074600] Task finished with error code: -22 (Invalid argument)
```

## 2. Logic Chain
1. The E2E test `test_transitions_and_zoom_e2e` generates input videos with 24 fps (`fps = 24`).
2. Shot 1 has `camera.movement = "static"`, which triggers the zoompan filter. Since no `fps` parameter is specified in the zoompan filter call, it defaults to 25 fps.
3. Shot 2 has `camera.movement = "orbit"`, which does not trigger the zoompan filter, keeping its original rate of 24 fps.
4. `postproduction.py` builds the xfade graph using `ffmpeg.filter((current_v, v_next), 'xfade', transition=t_type, ...)` between Shot 1 (25 fps) and Shot 2 (24 fps).
5. FFmpeg throws an invalid argument (-22) error because the xfade filter expects all inputs to have the same frame rate.
6. The video assembly fails, `produce_short` catches the error, returns `None`, and the test fails.

## 3. Caveats
- The issue only occurs when combining static camera shots (which get zoomed/panned) and non-static shots in the same output video, which is a standard usage scenario.
- Test suites using mocks for `ffmpeg.run` (such as `test_postproduction.py`) do not execute the FFmpeg binary and did not catch this issue. The E2E test `test_transitions.py` actually runs FFmpeg and therefore caught it.

## 4. Conclusion
The implementation has a critical bug in `src/ai_blender_director/postproduction.py` due to the lack of an explicit `fps` parameter in the `zoompan` filter. 
The verdict is **REQUEST_CHANGES**.

---

# Quality Review Report

## Review Summary

**Verdict**: REQUEST_CHANGES

## Findings

### Critical Finding 1

- **What**: Frame rate mismatch in xfade filter caused by zoompan filter defaulting to 25 fps.
- **Where**: `src/ai_blender_director/postproduction.py` lines 108–115.
- **Why**: When applying the `zoompan` filter to static shots, omitting `fps` causes FFmpeg to default its output frame rate to 25. If other shots in the sequence are at 24 or 30 fps, the xfade filter crashes due to mismatched frame rates on its inputs.
- **Suggestion**: Modify the zoompan filter application to explicitly pass `fps=fps`:
  ```python
  v = v.filter(
      'zoompan',
      z=preset['z'],
      x=preset['x'],
      y=preset['y'],
      d=1,
      s=f"{resolution[0]}x{resolution[1]}",
      fps=fps
  )
  ```

## Verified Claims

- `pyproject.toml` correctly contains `ffmpeg-python>=0.2.0` dependency → verified via `view_file` → PASS
- `ShotSpec` models support transitions and default to `TransitionSpec` → verified via `view_file` of `models.py` → PASS
- The test suite has a transition verification test → verified via `view_file` of `tests/test_transitions.py` → PASS
- The verification test script passes when run → verified via `run_command` → FAIL (due to the `zoompan` bug)

## Coverage Gaps

- **Integration test coverage** - The current integration test is excellent because it runs actual FFmpeg commands on dummy videos. However, it should have been run/verified on the CI/development pipeline earlier, which would have caught this bug.

---

# Adversarial Review Report

## Challenge Summary

**Overall risk assessment**: HIGH

## Challenges

### High Challenge 1

- **Assumption challenged**: The filter graphs built using `ffmpeg-python` are automatically compatible with inputs of any duration and frame rate.
- **Attack scenario**: Mixing static cameras (zoomed/panned at default 25 fps) with moving cameras (unfiltered at native 24 or 30 fps) and blending them using xfade.
- **Blast radius**: Complete crash of the video postproduction step, outputting a `None` path, which renders the entire pipeline broken for any videos containing mixed static/moving cameras.
- **Mitigation**: Add the explicit `fps=fps` option to the zoompan filter to force consistent frame rate propagation.

## Stress Test Results

- **Mix of static (zoompan) and orbit camera shots** → expected to compile and transition smoothly → failed with return code -22 in `xfade` → FAIL

## Unchallenged Areas

- **Audio track length alignment** → not thoroughly stress-tested with mismatched narration lengths exceeding 100 seconds, but basic padding handling is present.

---

## 5. Verification Method
To verify that this issue is fixed:
1. Run the transition tests using:
```powershell
$env:PYTHONPATH="src"; C:\Python314\python.exe -m unittest tests.test_transitions
```
2. Verify that the command exits successfully (exit code 0) and outputs `OK`.
