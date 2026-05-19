from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import ShotSpec


DEFAULT_RESOLUTION = {"width": 1280, "height": 720}


def generate_shot(prompt: str, *, duration_seconds: int = 4, fps: int = 24) -> dict[str, Any]:
    normalized = _normalize(prompt)
    scene = _detect_scene(normalized)
    camera = _detect_camera(normalized)
    weather = _detect_weather(normalized)

    shot = {
        "scene": scene,
        "style": _detect_style(normalized),
        "duration_seconds": duration_seconds,
        "fps": fps,
        "resolution": DEFAULT_RESOLUTION,
        "camera": {
            "movement": camera,
            "lens_mm": _detect_lens(normalized),
        },
        "lighting": _detect_lighting(normalized),
        "subject": _detect_subject(normalized),
        "action": _detect_action(normalized),
        "weather": weather,
        "seed": _seed_from_prompt(normalized),
    }
    ShotSpec.from_dict(shot)
    return shot


def write_generated_shot(
    prompt: str,
    output_dir: Path,
    *,
    duration_seconds: int = 4,
    fps: int = 24,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    shot = generate_shot(prompt, duration_seconds=duration_seconds, fps=fps)
    filename = f"{_slug(prompt)}.json"
    path = output_dir / filename
    with path.open("w", encoding="utf-8") as file:
        json.dump(shot, file, indent=2, ensure_ascii=False)
        file.write("\n")
    return path


def _detect_scene(prompt: str) -> str:
    if _contains(prompt, "cyberpunk", "neon", "calle", "ciudad", "street", "city"):
        return "cyberpunk street"
    if _contains(prompt, "bosque", "forest", "arbol", "árbol", "nature", "selva"):
        return "procedural forest"
    if _contains(prompt, "habitacion", "habitación", "room", "interior", "oficina", "studio"):
        return "interior room"
    if _contains(prompt, "desierto", "desert", "arena"):
        return "desert stage"
    return "minimal cinematic stage"


def _detect_style(prompt: str) -> str:
    if _contains(prompt, "anime", "manga"):
        return "anime cinematic"
    if _contains(prompt, "realista", "realistic", "photoreal", "fotorealista"):
        return "realistic cinematic"
    if _contains(prompt, "terror", "horror", "oscuro"):
        return "dark horror cinematic"
    if _contains(prompt, "cyberpunk", "neon"):
        return "cinematic neon noir"
    return "cinematic concept preview"


def _detect_camera(prompt: str) -> str:
    if _contains(prompt, "orbita", "órbita", "orbit", "rodeando"):
        return "orbit"
    if _contains(prompt, "dolly", "lateral", "travelling"):
        return "dolly"
    if _contains(prompt, "push", "acerc", "zoom"):
        return "push_in"
    if _contains(prompt, "estatica", "estática", "static", "fija"):
        return "static"
    return "slow orbit"


def _detect_lens(prompt: str) -> int:
    if _contains(prompt, "teleobjetivo", "telephoto", "retrato"):
        return 70
    if _contains(prompt, "gran angular", "wide", "wide angle"):
        return 24
    return 35


def _detect_lighting(prompt: str) -> str:
    if _contains(prompt, "neon", "cyberpunk"):
        return "red and cyan neon with soft volumetric ambience"
    if _contains(prompt, "noche", "night", "oscuro", "terror"):
        return "low key moonlight with strong rim light"
    if _contains(prompt, "atardecer", "sunset"):
        return "warm sunset key light"
    return "soft cinematic studio light"


def _detect_subject(prompt: str) -> str:
    if _contains(prompt, "personaje", "character", "humano", "hero", "protagonista"):
        return "prototype hero character"
    if _contains(prompt, "robot", "androide"):
        return "prototype robot character"
    if _contains(prompt, "auto", "car", "vehiculo", "vehículo"):
        return "placeholder vehicle"
    return "test subject"


def _detect_action(prompt: str) -> str:
    if _contains(prompt, "camina", "walk", "walking"):
        return "walks forward and turns toward camera"
    if _contains(prompt, "corre", "run", "running"):
        return "runs across the frame"
    if _contains(prompt, "mira", "look", "observa"):
        return "stands still and looks toward camera"
    return "moves across the frame"


def _detect_weather(prompt: str) -> str | None:
    if _contains(prompt, "lluvia", "rain", "lloviendo"):
        return "rain"
    if _contains(prompt, "niebla", "fog", "mist", "humo"):
        return "fog"
    if _contains(prompt, "nieve", "snow"):
        return "snow"
    return None


def _contains(value: str, *needles: str) -> bool:
    return any(needle in value for needle in needles)


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _seed_from_prompt(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2_147_483_648


def _slug(value: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "_" for char in _normalize(value))
    slug = "_".join(part for part in slug.split("_") if part)
    return slug[:80] or "generated_shot"
