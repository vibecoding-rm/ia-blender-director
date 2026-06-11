"""Director Agent: convierte una idea en un plan de varios planos (shots)."""

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

_PLAN_SCHEMA = {
    "title": "short title for the video concept (3-6 words)",
    "shots": [
        {
            "shot_role": "one of: establishing, action, close_up",
            "scene": "short scene/environment name",
            "style": "cinematic style",
            "camera_movement": "one of: static, orbit, dolly, push_in",
            "camera_lens_mm": "integer: 24, 35, 50, or 85",
            "lighting": "lighting description",
            "subject": "main subject of the shot",
            "action": "what the subject is doing",
            "weather": "rain, fog, snow, or null",
            "character_asset": "protagonista_v2 for humans, null otherwise",
            "environment_asset": "cyberpunk_street_v1, forest_v1, or null",
            "animation_asset": "walk_v1, run_v1, idle_v1, or null",
        }
    ],
}


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def plan_shots(
    prompt: str,
    n_shots: int = 3,
    *,
    duration_seconds: int = 4,
    fps: int = 24,
) -> list[dict[str, Any]]:
    """Convierte una idea en una lista de dicts ShotSpec listos para guardar."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("warning: OPENROUTER_API_KEY no está configurada. Usando generador de respaldo.", file=sys.stderr)
        return _fallback_plan(prompt, n_shots, duration_seconds=duration_seconds, fps=fps)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=_OPENROUTER_BASE_URL)
        system = (
            "Eres un AI Director cinematográfico. Responde SOLO con un JSON válido — sin markdown ni explicaciones.\n"
            f"El JSON debe seguir exactamente este esquema:\n{json.dumps(_PLAN_SCHEMA, indent=2, ensure_ascii=False)}\n"
            f"El campo 'shots' debe tener exactamente {n_shots} elementos."
        )
        user_msg = (
            f"Idea del usuario: \"{prompt}\"\n\n"
            f"Genera un plan de {n_shots} planos cinematográficos coherentes. "
            f"Usa roles: 'establishing' (plano general), 'action' (plano medio en movimiento), 'close_up' (primer plano)."
        )
        response = client.chat.completions.create(
            model=_OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
        )
        data = json.loads(response.choices[0].message.content)
        raw_shots = data.get("shots", [])[:n_shots]
        shots = [
            _raw_item_to_shot(item, i, prompt, duration_seconds=duration_seconds, fps=fps)
            for i, item in enumerate(raw_shots)
        ]
        for shot in shots:
            ShotSpec.from_dict(shot)
        return shots

    except Exception as exc:
        print(f"error llamando a OpenRouter: {exc}. Usando generador de respaldo.", file=sys.stderr)
        return _fallback_plan(prompt, n_shots, duration_seconds=duration_seconds, fps=fps)


def write_shot_plan(
    prompt: str,
    output_dir: Path,
    n_shots: int = 3,
    *,
    duration_seconds: int = 4,
    fps: int = 24,
) -> list[Path]:
    """Genera y guarda todos los planos del plan. Devuelve las rutas guardadas."""
    output_dir.mkdir(parents=True, exist_ok=True)
    shots = plan_shots(prompt, n_shots, duration_seconds=duration_seconds, fps=fps)
    base_slug = _slug(prompt)
    paths: list[Path] = []
    for i, shot in enumerate(shots, start=1):
        role = shot.get("_shot_role", f"shot_{i:02d}")
        filename = f"{base_slug}_{role}_{i:02d}.json"
        shot_data = {k: v for k, v in shot.items() if not k.startswith("_")}
        path = output_dir / filename
        with path.open("w", encoding="utf-8") as f:
            json.dump(shot_data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        paths.append(path)
    return paths


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _raw_item_to_shot(
    item: dict,
    index: int,
    base_prompt: str,
    *,
    duration_seconds: int,
    fps: int,
) -> dict[str, Any]:
    return {
        "_shot_role": item.get("shot_role", "action"),
        "scene": item.get("scene", "cinematic stage"),
        "style": item.get("style", "cinematic concept preview"),
        "duration_seconds": duration_seconds,
        "fps": fps,
        "resolution": DEFAULT_RESOLUTION,
        "camera": {
            "movement": item.get("camera_movement", "orbit"),
            "lens_mm": int(item.get("camera_lens_mm", 35)),
        },
        "lighting": item.get("lighting", "soft cinematic studio light"),
        "subject": item.get("subject", "main subject"),
        "action": item.get("action", "moves across the frame"),
        "weather": item.get("weather"),
        "seed": _seed(base_prompt, index),
        "character": item.get("character_asset"),
        "environment": item.get("environment_asset"),
        "animation": item.get("animation_asset"),
    }


def _fallback_plan(
    prompt: str,
    n_shots: int,
    *,
    duration_seconds: int,
    fps: int,
) -> list[dict[str, Any]]:
    """Plan de respaldo: establishing → action → close_up."""
    normalized = " ".join(prompt.strip().lower().split())

    if "cyberpunk" in normalized:
        scene = "cyberpunk street"
        style = "cinematic neon noir"
        environment = "cyberpunk_street_v1"
        lighting_base = "red and cyan neon with soft volumetric ambience"
    elif "bosque" in normalized or "forest" in normalized:
        scene = "procedural forest"
        style = "cinematic concept preview"
        environment = "forest_v1"
        lighting_base = "soft natural backlight with god rays"
    else:
        scene = "minimal cinematic stage"
        style = "cinematic concept preview"
        environment = None
        lighting_base = "soft cinematic studio light"

    if any(w in normalized for w in ["plastilina", "claymation", "clay", "stop motion", "stop-motion"]):
        style = f"claymation stop motion, {style}"

    weather: str | None = None
    if "lluvia" in normalized or "rain" in normalized:
        weather = "rain"
    elif "niebla" in normalized or "fog" in normalized:
        weather = "fog"

    has_character = any(w in normalized for w in ["personaje", "character", "hero", "heroe"])
    character = "protagonista_v2" if has_character else None
    animation = "walk_v1" if any(w in normalized for w in ["camina", "walk", "walking"]) else "idle_v1"

    templates = [
        {
            "_shot_role": "establishing",
            "scene": scene,
            "style": style,
            "duration_seconds": duration_seconds,
            "fps": fps,
            "resolution": DEFAULT_RESOLUTION,
            "camera": {"movement": "static", "lens_mm": 24},
            "lighting": lighting_base,
            "subject": "empty scene" if not character else "distant figure",
            "action": "stands still in the distance",
            "weather": weather,
            "seed": _seed(prompt, 0),
            "character": character,
            "environment": environment,
            "animation": "idle_v1" if character else None,
        },
        {
            "_shot_role": "action",
            "scene": scene,
            "style": style,
            "duration_seconds": duration_seconds,
            "fps": fps,
            "resolution": DEFAULT_RESOLUTION,
            "camera": {"movement": "orbit", "lens_mm": 35},
            "lighting": lighting_base,
            "subject": "hero character" if character else "main subject",
            "action": "walks forward across the frame",
            "weather": weather,
            "seed": _seed(prompt, 1),
            "character": character,
            "environment": environment,
            "animation": animation,
        },
        {
            "_shot_role": "close_up",
            "scene": scene,
            "style": style,
            "duration_seconds": duration_seconds,
            "fps": fps,
            "resolution": DEFAULT_RESOLUTION,
            "camera": {"movement": "push_in", "lens_mm": 85},
            "lighting": lighting_base,
            "subject": "hero character" if character else "main subject",
            "action": "turns toward camera",
            "weather": weather,
            "seed": _seed(prompt, 2),
            "character": character,
            "environment": environment,
            "animation": "idle_v1" if character else None,
        },
    ]

    return templates[:n_shots]


def _seed(prompt: str, index: int) -> int:
    value = f"{prompt}__shot_{index}"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2_147_483_648


def slug_for_prompt(value: str) -> str:
    return _slug(value)


def _slug(value: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "_" for c in value.strip())
    slug = "_".join(p for p in slug.split("_") if p)
    return slug[:60] or "plan"
