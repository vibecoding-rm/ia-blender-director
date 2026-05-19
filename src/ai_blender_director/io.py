from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ShotSpec, ShotValidationError


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as exc:
        raise ShotValidationError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ShotValidationError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ShotValidationError("Top-level JSON must be an object.")
    return data


def load_shot_spec(path: Path) -> ShotSpec:
    return ShotSpec.from_dict(load_json(path))
