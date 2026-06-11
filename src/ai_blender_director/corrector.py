"""Apply critic feedback to a shot spec JSON to produce a corrected version."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .critic import CriticFeedback


def apply_corrections(shot_path: Path, feedbacks: list[CriticFeedback]) -> Path:
    """
    Read shot_path, apply heuristic corrections based on critic feedbacks,
    write a new *_corrected.json next to the original, return its path.
    """
    with shot_path.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    for fb in feedbacks:
        _apply_single(data, fb)

    corrected_path = shot_path.with_stem(shot_path.stem + "_corrected")
    with corrected_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return corrected_path


def _apply_single(data: dict[str, Any], fb: CriticFeedback) -> None:
    category = fb.category
    message = fb.message.lower()

    if category == "Distance" and "too far" in message:
        # Move camera closer: reduce lens (wider) or switch to push_in
        cam = data.setdefault("camera", {})
        lens = cam.get("lens_mm", 35)
        cam["lens_mm"] = max(24, int(lens * 0.75))
        if cam.get("movement") == "static":
            cam["movement"] = "push_in"

    elif category == "Distance" and "missing" in message:
        # Subject missing entirely — widen lens to 24mm and switch to static
        cam = data.setdefault("camera", {})
        cam["lens_mm"] = 24
        cam["movement"] = "static"

    elif category == "Lighting" and "too dark" in message:
        existing = data.get("lighting", "")
        if "dim" in existing or "low key" in existing:
            data["lighting"] = existing.replace("dim", "bright").replace("low key", "soft")
        else:
            data["lighting"] = existing + " with boosted ambient fill"

    elif category == "Lighting" and "overexposed" in message:
        existing = data.get("lighting", "")
        data["lighting"] = existing + " (reduced intensity, -1 EV)"

    elif category == "Framing" and ("left" in message or "right" in message or
                                     "high" in message or "low" in message):
        # Centroid off-center — switch to a more forgiving movement
        cam = data.setdefault("camera", {})
        if cam.get("movement") not in ("orbit", "dolly"):
            cam["movement"] = "orbit"

    elif category == "Framing" and "cropped" in message:
        # Subject being cut — widen the lens
        cam = data.setdefault("camera", {})
        lens = cam.get("lens_mm", 35)
        cam["lens_mm"] = max(24, int(lens * 0.8))

    elif category == "Contrast" and "low" in message:
        existing = data.get("lighting", "")
        data["lighting"] = existing + " with increased key/fill ratio"
