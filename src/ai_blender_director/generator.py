"""generator.py — thin wrapper over planner.plan_scene for single-shot generation.

Previously this module duplicated the entire LLM + fallback logic from planner.py.
Now it delegates to planner and only adds the write_generated_shot() convenience
function for the legacy /api/pipeline endpoint.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .planner import plan_scene, _slug as _planner_slug


DEFAULT_RESOLUTION = {"width": 1280, "height": 720}


def generate_shot(
    prompt: str,
    *,
    duration_seconds: int = 4,
    fps: int = 24,
    resolution: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Generate a single ShotSpec dict using the Director planner (1-shot plan)."""
    resolution = resolution or DEFAULT_RESOLUTION
    scene_data = plan_scene(
        prompt, n_shots=1,
        duration_seconds=duration_seconds, fps=fps, resolution=resolution,
    )
    shots = scene_data.get("shots", [])
    if not shots:
        raise RuntimeError(f"plan_scene returned no shots for prompt: {prompt!r}")
    return shots[0]


def write_generated_shot(
    prompt: str,
    output_dir: Path,
    *,
    duration_seconds: int = 4,
    fps: int = 24,
    resolution: dict[str, int] | None = None,
) -> Path:
    """Generate a single shot and persist it as a JSON file. Returns the path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    shot = generate_shot(prompt, duration_seconds=duration_seconds, fps=fps, resolution=resolution)
    filename = f"{_planner_slug(prompt)}.json"
    path = output_dir / filename
    with path.open("w", encoding="utf-8") as f:
        json.dump(shot, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path
