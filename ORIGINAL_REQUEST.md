# Original User Request

## Initial Request — 2026-06-17T14:51:12Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview

Implement expert video editing features in the AI Blender Director project, specifically Dynamic Transitions (xfade) and Ken Burns (Post-camera zoom) effects. You must use `ffmpeg-python` to construct the complex filtergraphs instead of raw subprocess string arrays.

Working directory: C:\Users\Computops\Desktop\ia-blender-director
Integrity mode: development

## Requirements

### R1. `ffmpeg-python` Integration
Refactor the assembly phase (currently using raw FFmpeg `concat` in `postproduction.py` and `video.py`) to use the `ffmpeg-python` library. Add it to the project's dependencies if missing.

### R2. ShotSpec Updates
Update the `ShotSpec` model to support a `transition` field. Pass this transition data to the post-production assembly logic.

### R3. Transitions and Zoom
Use `ffmpeg-python` to apply `xfade` transitions between clips based on the `ShotSpec`. Apply a `zoompan` (Ken Burns effect) to any shot where the camera movement is defined as `static`.

## Acceptance Criteria

### Verification Script
- [ ] You must create an automated test script (`tests/test_transitions.py`).
- [ ] The script must generate 3 dummy solid-color video files.
- [ ] The script must assemble them using the new `ffmpeg-python` logic with at least one transition and one static zoom.
- [ ] The script must programmatically verify (using `ffprobe`) that the output video duration is correct (sum of durations minus overlapping transition times).
- [ ] The script must return exit code 0 if successful.
