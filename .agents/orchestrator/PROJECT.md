# Project: ia-blender-director

## Architecture
- Blender-driven video generation tool that renders individual shots and then compiles/assembles them into a final video.
- Assembly logic uses FFmpeg currently invoked via subprocesses.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Codebase Analysis | Explore codebase and document postproduction/video/models | none | DONE |
| 2 | ShotSpec Updates | Update ShotSpec model to support transition | M1 | IN_PROGRESS |
| 3 | ffmpeg-python Assembly Refactor | Refactor assembly logic to use ffmpeg-python | M1, M2 | IN_PROGRESS |
| 4 | Transitions and Zoom | Implement xfade transitions and Ken Burns zoom pan | M3 | IN_PROGRESS |
| 5 | Verification Script | Implement tests/test_transitions.py and run it | M4 | IN_PROGRESS |

## Interface Contracts
- TBD (will be defined by Explorer)
