from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .io import load_json, load_shot_spec


@dataclass(frozen=True)
class RenderJob:
    job_id: str
    job_dir: Path
    source_shot: Path
    job_shot: Path
    output_root: Path

    @property
    def manifest_path(self) -> Path:
        return self.job_dir / "job.json"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {key: str(value) if isinstance(value, Path) else value for key, value in data.items()}


def create_render_job(shot_path: Path, output_root: Path) -> RenderJob:
    spec = load_shot_spec(shot_path)
    source_shot = shot_path.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    job_id = f"{timestamp}_{_slug(spec.scene)}_{_slug(source_shot.stem)}"
    job_dir = _unique_dir(output_root / job_id)
    job_dir.mkdir(parents=True)

    job_shot = job_dir / "shot.json"
    shutil.copy2(source_shot, job_shot)

    job = RenderJob(
        job_id=job_dir.name,
        job_dir=job_dir.resolve(),
        source_shot=source_shot,
        job_shot=job_shot.resolve(),
        output_root=output_root.resolve(),
    )
    _write_job_manifest(job, load_json(job_shot))
    return job


def update_render_job_status(job: RenderJob, status: str, *, returncode: int | None = None) -> None:
    data = json.loads(job.manifest_path.read_text(encoding="utf-8"))
    data["status"] = status
    data["updated_at"] = datetime.now(UTC).isoformat()
    if returncode is not None:
        data["returncode"] = returncode
    with job.manifest_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def _write_job_manifest(job: RenderJob, shot: dict[str, Any]) -> None:
    manifest = {
        **job.to_dict(),
        "status": "created",
        "created_at": datetime.now(UTC).isoformat(),
        "shot": shot,
    }
    with job.manifest_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2, ensure_ascii=False)
        file.write("\n")


def _unique_dir(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 10_000):
        candidate = path.with_name(f"{path.name}_{index:02d}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not create unique render job directory for {path}")


def _slug(value: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "_" for char in value.strip().lower())
    slug = "_".join(part for part in slug.split("_") if part)
    return slug[:48] or "shot"
