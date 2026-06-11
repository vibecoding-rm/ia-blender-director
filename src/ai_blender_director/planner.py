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
    resolution: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Convierte una idea en una lista de dicts ShotSpec listos para guardar."""
    resolution = resolution or DEFAULT_RESOLUTION
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("warning: OPENROUTER_API_KEY no está configurada. Usando generador de respaldo.", file=sys.stderr)
        return _fallback_plan(prompt, n_shots, duration_seconds=duration_seconds, fps=fps, resolution=resolution)

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
            _raw_item_to_shot(item, i, prompt, duration_seconds=duration_seconds, fps=fps, resolution=resolution)
            for i, item in enumerate(raw_shots)
        ]
        for shot in shots:
            ShotSpec.from_dict(shot)
        return shots

    except Exception as exc:
        print(f"error llamando a OpenRouter: {exc}. Usando generador de respaldo.", file=sys.stderr)
        return _fallback_plan(prompt, n_shots, duration_seconds=duration_seconds, fps=fps, resolution=resolution)


def write_shot_plan(
    prompt: str,
    output_dir: Path,
    n_shots: int = 3,
    *,
    duration_seconds: int = 4,
    fps: int = 24,
    resolution: dict[str, int] | None = None,
) -> list[Path]:
    """Genera y guarda todos los planos del plan. Devuelve las rutas guardadas."""
    output_dir.mkdir(parents=True, exist_ok=True)
    shots = plan_shots(prompt, n_shots, duration_seconds=duration_seconds, fps=fps, resolution=resolution)
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
    resolution: dict[str, int] | None = None,
) -> dict[str, Any]:
    return {
        "_shot_role": item.get("shot_role", "action"),
        "scene": item.get("scene", "cinematic stage"),
        "style": item.get("style", "cinematic concept preview"),
        "duration_seconds": duration_seconds,
        "fps": fps,
        "resolution": resolution or DEFAULT_RESOLUTION,
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
    resolution: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Plan de respaldo: establishing → action → close_up."""
    resolution = resolution or DEFAULT_RESOLUTION
    normalized = " ".join(prompt.strip().lower().split())

    if any(w in normalized for w in ["noticia", "noticiero", "news", "estudio de tv"]):
        scene = "news studio"
        style = "claymation broadcast"
        environment = None
        lighting_base = "bright studio broadcast light"
    elif "cyberpunk" in normalized:
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

    if any(w in normalized for w in ["cerdo", "comandante", "portavoz", "pig"]):
        character: str | None = "comandante_cerdo_v1"
    elif any(w in normalized for w in ["cotorra", "mascota", "loro", "parrot"]) or scene == "news studio":
        character = "cotorra_v1"
    elif any(w in normalized for w in ["personaje", "character", "hero", "heroe"]):
        character = "protagonista_v2"
    else:
        character = None

    if any(w in normalized for w in ["habla", "presenta", "anuncia", "noticia"]) or scene == "news studio":
        animation = "talk_v1"
    elif any(w in normalized for w in ["camina", "walk", "walking"]):
        animation = "walk_v1"
    else:
        animation = "idle_v1"

    templates = [
        {
            "_shot_role": "establishing",
            "scene": scene,
            "style": style,
            "duration_seconds": duration_seconds,
            "fps": fps,
            "resolution": resolution,
            "camera": {"movement": "static", "lens_mm": 24},
            "lighting": lighting_base,
            "subject": "cotorra news anchor" if character == "cotorra_v1" else ("distant figure" if character else "empty scene"),
            "action": "presents the news" if animation == "talk_v1" else "stands still in the distance",
            "weather": weather,
            "seed": _seed(prompt, 0),
            "character": character,
            "environment": environment,
            "animation": (animation if animation == "talk_v1" else "idle_v1") if character else None,
        },
        {
            "_shot_role": "action",
            "scene": scene,
            "style": style,
            "duration_seconds": duration_seconds,
            "fps": fps,
            "resolution": resolution,
            "camera": {"movement": "orbit", "lens_mm": 35},
            "lighting": lighting_base,
            "subject": "cotorra news anchor" if character == "cotorra_v1" else ("hero character" if character else "main subject"),
            "action": "presents the news gesturing" if animation == "talk_v1" else "walks forward across the frame",
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
            "resolution": resolution,
            "camera": {"movement": "push_in", "lens_mm": 85},
            "lighting": lighting_base,
            "subject": "cotorra news anchor" if character == "cotorra_v1" else ("hero character" if character else "main subject"),
            "action": "talks directly to camera" if animation == "talk_v1" else "turns toward camera",
            "weather": weather,
            "seed": _seed(prompt, 2),
            "character": character,
            "environment": environment,
            "animation": (animation if animation == "talk_v1" else "idle_v1") if character else None,
        },
    ]

    # Historia de noticiero: el plano intermedio sale del estudio y reporta
    # desde la calle (plaza habanera) para que la secuencia cuente una historia.
    if scene == "news studio" and character == "cotorra_v1" and n_shots >= 3:
        templates[1].update({
            "scene": "havana plaza",
            "camera": {"movement": "dolly", "lens_mm": 35},
            "lighting": "warm caribbean daylight",
            "subject": "cotorra reporting from the street",
            "action": "waddles across the plaza reporting",
            "animation": "walk_v1",
            "environment": None,
        })

    # Ritmo Shorts: con 4+ planos, secuencia de cortes variados (ángulo y
    # escena cambian en cada plano — un "pattern interrupt" por corte).
    if scene == "news studio" and character == "cotorra_v1" and n_shots >= 4:
        variants = [
            ("establishing", "news studio",  "static",  24, "presents the news",                "talk_v1", lighting_base),
            ("close_up",     "news studio",  "push_in", 85, "talks directly to camera",          "talk_v1", lighting_base),
            ("action",       "havana plaza", "dolly",   35, "waddles across the plaza reporting", "walk_v1", "warm caribbean daylight"),
            ("medium",       "news studio",  "orbit",   50, "presents the news gesturing",       "talk_v1", lighting_base),
            ("action",       "havana plaza", "orbit",   35, "looks around the plaza reporting",  "walk_v1", "warm caribbean daylight"),
            ("close_up",     "news studio",  "push_in", 85, "delivers the punchline to camera",  "talk_v1", lighting_base),
        ]
        base = templates[0]
        templates = []
        for i in range(n_shots):
            role, shot_scene, movement, lens, action, anim, light = variants[i % len(variants)]
            shot = dict(base)
            shot.update({
                "_shot_role": role,
                "scene": shot_scene,
                "camera": {"movement": movement, "lens_mm": lens},
                "lighting": light,
                "subject": "cotorra news anchor" if shot_scene == "news studio" else "cotorra reporting from the street",
                "action": action,
                "animation": anim,
                "environment": None,
                "seed": _seed(prompt, i),
            })
            templates.append(shot)

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
