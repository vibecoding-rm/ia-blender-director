from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ShotValidationError(ValueError):
    """Raised when a shot specification cannot be executed safely."""


@dataclass(frozen=True)
class Resolution:
    width: int
    height: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Resolution":
        width = _required_int(data, "width", minimum=320, maximum=7680)
        height = _required_int(data, "height", minimum=240, maximum=4320)
        return cls(width=width, height=height)


@dataclass(frozen=True)
class CameraSpec:
    movement: str
    lens_mm: int = 35

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CameraSpec":
        movement = _required_str(data, "movement", max_length=80)
        lens_mm = _optional_int(data, "lens_mm", default=35, minimum=12, maximum=200)
        return cls(movement=movement, lens_mm=lens_mm)


@dataclass(frozen=True)
class AssetRefs:
    character: str | None = None
    environment: str | None = None
    animation: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssetRefs":
        return cls(
            character=_optional_str(data, "character", max_length=80),
            environment=_optional_str(data, "environment", max_length=80),
            animation=_optional_str(data, "animation", max_length=80),
        )


@dataclass(frozen=True)
class ShotSpec:
    scene: str
    style: str
    duration_seconds: int
    fps: int
    resolution: Resolution
    camera: CameraSpec
    lighting: str
    subject: str
    action: str
    weather: str | None
    seed: int
    assets: AssetRefs

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShotSpec":
        if not isinstance(data, dict):
            raise ShotValidationError("Shot spec must be a JSON object.")

        resolution_data = _required_object(data, "resolution")
        camera_data = _required_object(data, "camera")

        return cls(
            scene=_required_str(data, "scene", max_length=140),
            style=_required_str(data, "style", max_length=120),
            duration_seconds=_required_int(data, "duration_seconds", minimum=1, maximum=60),
            fps=_required_int(data, "fps", minimum=1, maximum=60),
            resolution=Resolution.from_dict(resolution_data),
            camera=CameraSpec.from_dict(camera_data),
            lighting=_required_str(data, "lighting", max_length=120),
            subject=_required_str(data, "subject", max_length=120),
            action=_required_str(data, "action", max_length=160),
            weather=_optional_str(data, "weather", max_length=80),
            seed=_required_int(data, "seed", minimum=0, maximum=2_147_483_647),
            assets=AssetRefs.from_dict(data),
        )

    @property
    def frame_count(self) -> int:
        return self.duration_seconds * self.fps


def _required_object(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ShotValidationError(f"'{key}' must be an object.")
    return value


def _required_str(data: dict[str, Any], key: str, *, max_length: int) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ShotValidationError(f"'{key}' must be a non-empty string.")
    value = value.strip()
    if len(value) > max_length:
        raise ShotValidationError(f"'{key}' must be {max_length} characters or fewer.")
    return value


def _optional_str(data: dict[str, Any], key: str, *, max_length: int) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ShotValidationError(f"'{key}' must be a string or null.")
    value = value.strip()
    if not value:
        return None
    if len(value) > max_length:
        raise ShotValidationError(f"'{key}' must be {max_length} characters or fewer.")
    return value


def _required_int(
    data: dict[str, Any],
    key: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ShotValidationError(f"'{key}' must be an integer.")
    if value < minimum or value > maximum:
        raise ShotValidationError(f"'{key}' must be between {minimum} and {maximum}.")
    return value


def _optional_int(
    data: dict[str, Any],
    key: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = data.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ShotValidationError(f"'{key}' must be an integer.")
    if value < minimum or value > maximum:
        raise ShotValidationError(f"'{key}' must be between {minimum} and {maximum}.")
    return value
