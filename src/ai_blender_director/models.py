from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

class ShotValidationError(ValueError):
    """Raised when a shot specification cannot be executed safely."""

class Resolution(BaseModel):
    width: int = Field(..., ge=320, le=7680)
    height: int = Field(..., ge=240, le=4320)

class CameraSpec(BaseModel):
    movement: str = Field(..., max_length=80)
    lens_mm: int = Field(35, ge=12, le=200)

class AssetRefs(BaseModel):
    character: str | None = Field(None, max_length=80)
    environment: str | None = Field(None, max_length=80)
    animation: str | None = Field(None, max_length=80)

class TransitionSpec(BaseModel):
    type: Literal[
        'none', 'fade', 'wipeleft', 'wiperight', 'wipeup', 'wipedown', 
        'slideleft', 'slideright', 'slideup', 'slidedown', 'circlecrop', 
        'rectcrop', 'distance', 'fadeblack', 'fadewhite', 'radial', 
        'smoothleft', 'smoothright', 'smoothup', 'smoothdown', 'circleopen', 
        'circleclose', 'vertopen', 'vertclose', 'horzopen', 'horzclose', 
        'dissolve', 'pixelize', 'diagonalleft', 'diagonalright', 'hslice', 
        'vslice', 'zoomin'
    ] = 'none'
    duration: float = 0.5

class ShotSpec(BaseModel):
    model_config = {"frozen": True}

    scene: str = Field(..., max_length=140)
    style: str = Field(..., max_length=120)
    duration_seconds: int = Field(..., ge=1, le=60)
    fps: int = Field(..., ge=1, le=60)
    resolution: Resolution
    camera: CameraSpec
    lighting: str = Field(..., max_length=120)
    subject: str = Field(..., max_length=120)
    action: str = Field(..., max_length=160)
    weather: str | None = Field(None, max_length=80)
    seed: int = Field(..., ge=0, le=2_147_483_647)
    assets: AssetRefs = Field(default_factory=AssetRefs)
    transition: TransitionSpec = Field(default_factory=TransitionSpec)

    @classmethod
    def from_dict(cls, data: dict) -> "ShotSpec":
        try:
            if not isinstance(data, dict):
                raise ShotValidationError("Shot spec must be a JSON object.")
            # Map top level keys to assets for backwards compatibility
            if "assets" not in data:
                data["assets"] = {
                    "character": data.get("character"),
                    "environment": data.get("environment"),
                    "animation": data.get("animation")
                }
            return cls.model_validate(data)
        except Exception as e:
            raise ShotValidationError(str(e))

    @property
    def frame_count(self) -> int:
        return self.duration_seconds * self.fps
