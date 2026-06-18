from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from .config import settings
from .models import ShotSpec

logger = logging.getLogger(__name__)

DEFAULT_RESOLUTION = {"width": 1280, "height": 720}
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_SCENE_SCHEMA = {
    "title": "short title for the video concept (3-6 words)",
    "hook_title": "catchy on-screen text for the first 1.5 seconds (3-5 words) or null",
    "narration_text": "voiceover script for the entire video to be read by TTS (30-50 words) or null",
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
            "character_asset": "cotorra_v1 (presentadora), comandante_cerdo_v1 (vocero), humbrete_v1 (fiscal sabueso), michelito_v1 (gallito Con Filo), randy_v1 (tortuga Mesa Redonda), guerrero_v1 (armadura anónima), ciberclarias_v1 (troll/enjambre), protagonista_v2 (humano genérico), or null",
            "environment_asset": "cyberpunk_street_v1, forest_v1, or null",
            "animation_asset": "walk_v1, run_v1, idle_v1, or null",
            "transition": {
                "type": "one of: none, fade, wipeleft, wiperight, slideleft, slideright, dissolve",
                "duration": "float: transition duration in seconds (default: 0.5)"
            }
        }
    ],
}


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def plan_scene(
    prompt: str,
    n_shots: int = 3,
    *,
    duration_seconds: int = 4,
    fps: int = 24,
    resolution: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Convierte una idea en un dict con título, narración y planos (SceneSpec)."""
    resolution = resolution or DEFAULT_RESOLUTION
    api_key = settings.openrouter_api_key
    if not api_key:
        logger.warning("OPENROUTER_API_KEY no está configurada. Usando generador de respaldo para la escena.")
        shots = _fallback_plan(prompt, n_shots, duration_seconds=duration_seconds, fps=fps, resolution=resolution)
        return {
            "title": prompt[:30],
            "hook_title": "NOTICIA URGENTE" if "noticia" in prompt.lower() else None,
            "narration_text": None,
            "shots": shots
        }

    # Ruta opt-in: Instructor (Pydantic + reintentos). Solo con modelos fuertes
    # en structured outputs; si no, el JSON-mode clásico de abajo es más robusto.
    if settings.director_use_instructor:
        instructor_result = _plan_via_instructor(
            prompt, n_shots, api_key,
            duration_seconds=duration_seconds, fps=fps, resolution=resolution,
        )
        if instructor_result is not None:
            return instructor_result

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=_OPENROUTER_BASE_URL)
        system = (
            "Eres un AI Director cinematográfico. Responde SOLO con un JSON válido — sin markdown ni explicaciones.\n"
            f"El JSON debe seguir exactamente este esquema:\n{json.dumps(_SCENE_SCHEMA, indent=2, ensure_ascii=False)}\n"
            f"El campo 'shots' debe tener exactamente {n_shots} elementos."
        )
        user_msg = (
            f"Idea del usuario: \"{prompt}\"\n\n"
            f"Genera un plan de {n_shots} planos cinematográficos coherentes. "
            f"Usa roles: 'establishing' (plano general), 'action' (plano medio en movimiento), 'close_up' (primer plano)."
        )
        response = client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
        )
        try:
            data = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON del LLM: {e}. Usando generador de respaldo.")
            shots = _fallback_plan(prompt, n_shots, duration_seconds=duration_seconds, fps=fps, resolution=resolution)
            return {"title": "Fallback", "hook_title": None, "narration_text": None, "shots": shots}
            
        raw_shots = data.get("shots", [])[:n_shots]
        shots = [
            _raw_item_to_shot(item, i, prompt, duration_seconds=duration_seconds, fps=fps, resolution=resolution)
            for i, item in enumerate(raw_shots)
        ]
        
        # Validate each shot
        for shot in shots:
            ShotSpec.from_dict(shot)
            
        return {
            "title": data.get("title", prompt[:30]),
            "hook_title": data.get("hook_title"),
            "narration_text": data.get("narration_text"),
            "shots": shots
        }

    except Exception as exc:
        logger.error(f"Error llamando a OpenRouter en plan_scene: {exc}. Usando generador de respaldo.")
        shots = _fallback_plan(prompt, n_shots, duration_seconds=duration_seconds, fps=fps, resolution=resolution)
        return {"title": "Fallback", "hook_title": None, "narration_text": None, "shots": shots}


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
    scene_data = plan_scene(prompt, n_shots, duration_seconds=duration_seconds, fps=fps, resolution=resolution)
    return scene_data["shots"]


def write_shot_plan(
    prompt: str,
    output_dir: Path,
    n_shots: int = 3,
    *,
    duration_seconds: int = 4,
    fps: int = 24,
    resolution: dict[str, int] | None = None,
    precomputed_shots: list[dict] | None = None,
) -> list[Path]:
    """Genera y guarda todos los planos del plan. Devuelve las rutas guardadas."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if precomputed_shots:
        shots = precomputed_shots
    else:
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
# Director Agent vía Instructor (structured outputs con reintentos)
# ---------------------------------------------------------------------------

def _plan_via_instructor(
    prompt: str,
    n_shots: int,
    api_key: str,
    *,
    duration_seconds: int,
    fps: int,
    resolution: dict[str, int] | None,
) -> dict[str, Any] | None:
    """Genera el SceneSpec con Instructor. Devuelve None si no está disponible."""
    try:
        import instructor
        from openai import OpenAI
        from pydantic import BaseModel, Field
        from typing import Literal
    except ImportError:
        return None

    class LLMTransition(BaseModel):
        type: Literal[
            "none", "fade", "wipeleft", "wiperight", "slideleft", "slideright", "dissolve"
        ] = "none"
        duration: float = 0.5

    class LLMShot(BaseModel):
        shot_role: Literal["establishing", "action", "close_up", "medium"] = "action"
        scene: str
        style: str
        camera_movement: Literal["static", "orbit", "dolly", "push_in"] = "orbit"
        camera_lens_mm: int = Field(35, ge=12, le=200)
        lighting: str
        subject: str
        action: str
        weather: Literal["rain", "fog", "snow"] | None = None
        character_asset: str | None = None
        environment_asset: str | None = None
        animation_asset: str | None = None
        transition: LLMTransition = Field(default_factory=LLMTransition)

    class LLMScene(BaseModel):
        title: str
        hook_title: str | None = None
        narration_text: str | None = None
        shots: list[LLMShot]

    try:
        client = instructor.from_openai(OpenAI(api_key=api_key, base_url=_OPENROUTER_BASE_URL))
        scene: LLMScene = client.chat.completions.create(
            model=settings.openrouter_model,
            response_model=LLMScene,
            max_retries=1,
            temperature=0.8,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un AI Director cinematográfico para un noticiero satírico en "
                        "claymation. Genera un plan coherente que cuente una historia."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f'Idea del usuario: "{prompt}"\n'
                        f"Genera exactamente {n_shots} planos con roles variados "
                        f"(establishing, action, close_up)."
                    ),
                },
            ],
        )
    except Exception as exc:  # noqa: BLE001 — cualquier fallo cae a JSON-mode
        logger.warning("Instructor falló (%s); usando JSON-mode clásico.", exc)
        return None

    raw_shots = [s.model_dump() for s in scene.shots[:n_shots]]
    shots = [
        _raw_item_to_shot(item, i, prompt, duration_seconds=duration_seconds, fps=fps, resolution=resolution)
        for i, item in enumerate(raw_shots)
    ]
    for shot in shots:
        ShotSpec.from_dict(shot)  # valida; lanza si el LLM produjo algo inválido
    return {
        "title": scene.title,
        "hook_title": scene.hook_title,
        "narration_text": scene.narration_text,
        "shots": shots,
    }


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
    raw_transition = item.get("transition") or {}
    transition_type = raw_transition.get("type", "none") if isinstance(raw_transition, dict) else "none"
    transition_duration = raw_transition.get("duration", 0.5) if isinstance(raw_transition, dict) else 0.5

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
        "transition": {
            "type": transition_type,
            "duration": transition_duration
        }
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

    # 1. Escena, Estilo, Entorno e Iluminación
    themes = [
        (["noticia", "noticiero", "news", "estudio de tv"], ("news studio", "claymation broadcast", None, "bright studio broadcast light")),
        (["cyberpunk"], ("cyberpunk street", "cinematic neon noir", "cyberpunk_street_v1", "red and cyan neon with soft volumetric ambience")),
        (["bosque", "forest"], ("procedural forest", "cinematic concept preview", "forest_v1", "soft natural backlight with god rays")),
    ]
    scene, style, environment, lighting_base = "minimal cinematic stage", "cinematic concept preview", None, "soft cinematic studio light"
    for keywords, theme_values in themes:
        if any(w in normalized for w in keywords):
            scene, style, environment, lighting_base = theme_values
            break

    if any(w in normalized for w in ["plastilina", "claymation", "clay", "stop motion", "stop-motion"]):
        style = f"claymation stop motion, {style}"

    # 2. Clima
    weather = "rain" if any(w in normalized for w in ["lluvia", "rain"]) else "fog" if any(w in normalized for w in ["niebla", "fog"]) else None

    # 3. Personaje
    character_mappings = [
        (["humbrete", "humbertico", "humberto", "sabueso", "fiscal", "bulldog"], "humbrete_v1"),
        (["michelito", "michel", "con filo", "gallito", "gallo", "navaja"], "michelito_v1"),
        (["randy", "mesa redonda", "tortuga", "redondo", "decano"], "randy_v1"),
        (["guerrero", "lata", "anonimo", "anónimo", "casco", "armadura", "caballero"], "guerrero_v1"),
        (["ciberclaria", "ciberclarias", "troll", "enjambre", "claria", "bagre"], "ciberclarias_v1"),
        (["cerdo", "comandante", "portavoz", "pig"], "comandante_cerdo_v1"),
        (["cotorra", "mascota", "loro", "parrot"], "cotorra_v1"),
        (["personaje", "character", "hero", "heroe"], "protagonista_v2")
    ]
    character = "cotorra_v1" if scene == "news studio" else None
    if not character:
        for keywords, char_id in character_mappings:
            if any(w in normalized for w in keywords):
                character = char_id
                break

    # 4. Animación
    animation = "idle_v1"
    if any(w in normalized for w in ["habla", "presenta", "anuncia", "noticia"]) or scene == "news studio":
        animation = "talk_v1"
    elif any(w in normalized for w in ["camina", "walk", "walking"]):
        animation = "walk_v1"

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
            "transition": {"type": "none", "duration": 0.5}
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
            "transition": {"type": "fade", "duration": 0.5}
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
            "transition": {"type": "fade", "duration": 0.5}
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
