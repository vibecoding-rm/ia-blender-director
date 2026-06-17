## 2026-06-17T14:54:28Z
You are teamwork_preview_worker. Your working directory is C:\Users\Computops\Desktop\ia-blender-director\.agents\worker_m2_1.

Your task is to implement the ShotSpec updates, ffmpeg-python assembly refactor, and transitions/zoom requirements in the AI Blender Director project.

Specific requirements:
1. Update dependency: Add 'ffmpeg-python>=0.2.0' to dependencies in pyproject.toml if not present.
2. ShotSpec updates (src/ai_blender_director/models.py):
   - Add a TransitionSpec model with type (Literal of xfade types or 'none', default='none') and duration (float, default=0.5).
   - Add transition: TransitionSpec = Field(default_factory=TransitionSpec) to ShotSpec.
   - Update planner schema if needed to support transitions in src/ai_blender_director/planner.py.
3. ffmpeg-python refactoring in video assembly:
   - Refactor src/ai_blender_director/commands/video.py (specifically assemble_video and other assembly/concat methods) to compile or run using ffmpeg-python.
   - Refactor src/ai_blender_director/postproduction.py (specifically produce_short, _concat_reencode, etc.) to use ffmpeg-python for assembling clips, transitions, padding, subtitles, and mixing audio in a cleaner/efficient manner.
   - Apply 'xfade' transitions between video clips based on the TransitionSpec of ShotSpec. Note: visual transition midpoints shift due to overlapping. The whoosh sound effects in mix_audio_track should be timed correctly matching transition midpoints.
   - Apply 'zoompan' (Ken Burns effect) to shots where the camera movement is 'static'. Define presets like 'zoom_in', 'zoom_out', etc. and ensure resolution is correctly handled (e.g. s='1080x1920' or matching resolution).
4. Verify that existing tests still pass.

Write a handoff report at C:\Users\Computops\Desktop\ia-blender-director\.agents\worker_m2_1\handoff.md detailing the changes made, files modified, and test verification output.
