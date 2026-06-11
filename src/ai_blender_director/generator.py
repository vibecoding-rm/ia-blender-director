from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from .models import ShotSpec

DEFAULT_RESOLUTION = {"width": 1280, "height": 720}
_OPENROUTER_MODEL = "google/gemini-2.0-flash-001"
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_SHOT_SCHEMA = {
    "scene": "short scene/environment name (e.g. 'cyberpunk street', 'dark forest')",
    "style": "cinematic style (e.g. 'anime cinematic', 'realistic neon noir', 'dark horror')",
    "camera_movement": "one of: orbit, dolly, push_in, static",
    "camera_lens_mm": "integer focal length in mm: 24, 35, 50, or 85",
    "lighting": "lighting description (e.g. 'red and cyan neon with soft volumetric ambience')",
    "subject": "main subject (e.g. 'prototype hero character')",
    "action": "what the subject is doing (e.g. 'walks forward and turns toward camera')",
    "weather": "one of: rain, fog, snow — or null if none",
    "character_asset": "'protagonista_v2' for humans, null otherwise",
    "environment_asset": "'cyberpunk_street_v1', 'forest_v1', or null",
    "animation_asset": "'walk_v1', 'run_v1', 'idle_v1', or null",
}


def generate_shot(
    prompt: str,
    *,
    duration_seconds: int = 4,
    fps: int = 24,
    resolution: dict[str, int] | None = None,
) -> dict[str, Any]:
    resolution = resolution or DEFAULT_RESOLUTION
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("warning: OPENROUTER_API_KEY is not set. Using basic fallback generator.", file=sys.stderr)
        return _fallback_generate_shot(prompt, duration_seconds=duration_seconds, fps=fps, resolution=resolution)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=_OPENROUTER_BASE_URL)
        system = (
            "You are an AI Blender Director. Reply ONLY with a valid JSON object — no markdown, no explanation.\n"
            f"Required fields and their meaning:\n{json.dumps(_SHOT_SCHEMA, indent=2)}"
        )
        response = client.chat.completions.create(
            model=_OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Generate a cinematic shot for: {prompt}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        data = json.loads(response.choices[0].message.content)
        shot = {
            "scene": data["scene"],
            "style": data["style"],
            "duration_seconds": duration_seconds,
            "fps": fps,
            "resolution": resolution,
            "camera": {
                "movement": data.get("camera_movement", "orbit"),
                "lens_mm": int(data.get("camera_lens_mm", 35)),
            },
            "lighting": data["lighting"],
            "subject": data["subject"],
            "action": data["action"],
            "weather": data.get("weather"),
            "seed": _seed_from_prompt(prompt),
            "character": data.get("character_asset"),
            "environment": data.get("environment_asset"),
            "animation": data.get("animation_asset"),
        }
        ShotSpec.from_dict(shot)
        return shot

    except Exception as exc:
        print(f"error calling OpenRouter API: {exc}. Using fallback generator.", file=sys.stderr)
        return _fallback_generate_shot(prompt, duration_seconds=duration_seconds, fps=fps, resolution=resolution)


def _fallback_generate_shot(
    prompt: str,
    *,
    duration_seconds: int = 4,
    fps: int = 24,
    resolution: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Procedural fallback for testing without API keys."""
    resolution = resolution or DEFAULT_RESOLUTION
    normalized = " ".join(prompt.strip().lower().split())

    if any(w in normalized for w in ["noticia", "noticiero", "news", "estudio de tv"]):
        scene = "news studio"
        style = "claymation broadcast"
        environment = None
    elif "cyberpunk" in normalized:
        scene = "cyberpunk street"
        style = "cinematic neon noir"
        environment = "cyberpunk_street_v1"
    elif "bosque" in normalized or "forest" in normalized:
        scene = "procedural forest"
        style = "cinematic concept preview"
        environment = "forest_v1"
    else:
        scene = "minimal cinematic stage"
        style = "cinematic concept preview"
        environment = None

    if any(w in normalized for w in ["plastilina", "claymation", "clay", "stop motion", "stop-motion"]):
        style = f"claymation stop motion, {style}"

    if "lluvia" in normalized or "rain" in normalized:
        weather: str | None = "rain"
    elif "niebla" in normalized or "fog" in normalized:
        weather = "fog"
    elif "nieve" in normalized or "snow" in normalized:
        weather = "snow"
    else:
        weather = None

    if "orbit" in normalized or "orbitando" in normalized:
        movement = "orbit"
    elif "dolly" in normalized:
        movement = "dolly"
    elif "fija" in normalized or "fijo" in normalized or "static" in normalized:
        movement = "static"
    else:
        movement = "orbit"

    if any(w in normalized for w in ["cotorra", "mascota", "loro", "parrot"]):
        character: str | None = "cotorra_v1"
    elif any(w in normalized for w in ["personaje", "character", "hero", "heroe", "héroe", "persona", "hombre", "mujer", "soldado"]):
        character = "protagonista_v2"
    elif scene == "news studio":
        character = "cotorra_v1"
    else:
        character = None

    if any(w in normalized for w in ["habla", "presenta", "anuncia", "talk", "noticia"]):
        animation: str | None = "talk_v1"
    elif "camina" in normalized or "walk" in normalized:
        animation = "walk_v1"
    else:
        animation = None

    shot = {
        "scene": scene,
        "style": style,
        "duration_seconds": duration_seconds,
        "fps": fps,
        "resolution": resolution,
        "camera": {"movement": movement, "lens_mm": 35},
        "lighting": "bright studio broadcast light" if scene == "news studio" else "soft cinematic studio light",
        "subject": "cotorra news anchor" if character == "cotorra_v1" else "test subject",
        "action": "talks to camera" if animation == "talk_v1" else "moves across the frame",
        "weather": weather,
        "seed": _seed_from_prompt(normalized),
        "character": character,
        "environment": environment,
        "animation": animation,
    }
    return shot


def write_generated_shot(
    prompt: str,
    output_dir: Path,
    *,
    duration_seconds: int = 4,
    fps: int = 24,
    resolution: dict[str, int] | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    shot = generate_shot(prompt, duration_seconds=duration_seconds, fps=fps, resolution=resolution)
    filename = f"{_slug(prompt)}.json"
    path = output_dir / filename
    with path.open("w", encoding="utf-8") as file:
        json.dump(shot, file, indent=2, ensure_ascii=False)
        file.write("\n")
    return path


def _seed_from_prompt(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2_147_483_648


def _slug(value: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "_" for char in " ".join(value.strip().lower().split()))
    slug = "_".join(part for part in slug.split("_") if part)
    return slug[:80] or "generated_shot"
