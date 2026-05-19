from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from .models import ShotSpec


DEFAULT_RESOLUTION = {"width": 1280, "height": 720}


class LLMShotSpec(BaseModel):
    """Schema for the LLM to generate the shot details."""
    scene: str = Field(description="The name of the scene or environment. Keep it short (e.g. 'cyberpunk street', 'dark forest').")
    style: str = Field(description="The cinematic style (e.g. 'anime cinematic', 'realistic neon noir', 'dark horror').")
    camera_movement: str = Field(description="Camera movement (e.g. 'orbit', 'dolly', 'push_in', 'static').")
    camera_lens_mm: int = Field(description="Camera lens focal length in mm (e.g. 24, 35, 50, 85).")
    lighting: str = Field(description="Lighting setup (e.g. 'red and cyan neon with soft volumetric ambience').")
    subject: str = Field(description="The main subject of the shot (e.g. 'prototype hero character', 'placeholder vehicle').")
    action: str = Field(description="What the subject is doing (e.g. 'walks forward and turns toward camera').")
    weather: str | None = Field(description="Weather condition (e.g. 'rain', 'fog', 'snow') or null if none.")
    character_asset: str | None = Field(description="The asset ID of the character to load. If it's a human character, return 'protagonista_v1'. Otherwise null.")
    environment_asset: str | None = Field(description="The asset ID of the environment. If cyberpunk, return 'cyberpunk_street_v1'. If forest, return 'forest_v1'. Otherwise null.")
    animation_asset: str | None = Field(description="The asset ID of the animation. If walking, return 'walk_v1'. If running, return 'run_v1'. If idle, return 'idle_v1'. Otherwise null.")


def generate_shot(prompt: str, *, duration_seconds: int = 4, fps: int = 24) -> dict[str, Any]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("warning: GEMINI_API_KEY is not set. Using basic fallback generator.", file=sys.stderr)
        return _fallback_generate_shot(prompt, duration_seconds=duration_seconds, fps=fps)
        
    try:
        client = genai.Client()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"You are an AI Blender Director. Given the following user prompt, generate a cinematic shot specification.\nPrompt: {prompt}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=LLMShotSpec,
                temperature=0.7,
            ),
        )
        
        # Parse the pydantic model returned by Gemini
        llm_spec: LLMShotSpec = response.parsed
        
        shot = {
            "scene": llm_spec.scene,
            "style": llm_spec.style,
            "duration_seconds": duration_seconds,
            "fps": fps,
            "resolution": DEFAULT_RESOLUTION,
            "camera": {
                "movement": llm_spec.camera_movement,
                "lens_mm": llm_spec.camera_lens_mm,
            },
            "lighting": llm_spec.lighting,
            "subject": llm_spec.subject,
            "action": llm_spec.action,
            "weather": llm_spec.weather,
            "seed": _seed_from_prompt(prompt),
            "character": llm_spec.character_asset,
            "environment": llm_spec.environment_asset,
            "animation": llm_spec.animation_asset,
        }
        
        # Validate against our actual dataclass models
        ShotSpec.from_dict(shot)
        return shot
        
    except Exception as e:
        print(f"error calling Gemini API: {e}. Using fallback generator.", file=sys.stderr)
        return _fallback_generate_shot(prompt, duration_seconds=duration_seconds, fps=fps)


def _fallback_generate_shot(prompt: str, *, duration_seconds: int = 4, fps: int = 24) -> dict[str, Any]:
    """Procedural fallback for testing without API keys."""
    normalized = " ".join(prompt.strip().lower().split())

    if "cyberpunk" in normalized:
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

    shot = {
        "scene": scene,
        "style": style,
        "duration_seconds": duration_seconds,
        "fps": fps,
        "resolution": DEFAULT_RESOLUTION,
        "camera": {"movement": movement, "lens_mm": 35},
        "lighting": "soft cinematic studio light",
        "subject": "test subject",
        "action": "moves across the frame",
        "weather": weather,
        "seed": _seed_from_prompt(normalized),
        "character": "protagonista_v1" if "personaje" in normalized else None,
        "environment": environment,
        "animation": "walk_v1" if "camina" in normalized else None,
    }
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


def _seed_from_prompt(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2_147_483_648


def _slug(value: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "_" for char in " ".join(value.strip().lower().split()))
    slug = "_".join(part for part in slug.split("_") if part)
    return slug[:80] or "generated_shot"
