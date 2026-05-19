from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .jobs import RenderJob


def append_index_event(
    index_path: Path,
    job: RenderJob,
    event: str,
    *,
    status: str,
    returncode: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": event,
        "status": status,
        "job_id": job.job_id,
        "job_dir": str(job.job_dir),
        "source_shot": str(job.source_shot),
        "job_shot": str(job.job_shot),
        "profile": job.profile,
    }
    if returncode is not None:
        record["returncode"] = returncode
    if extra:
        record.update(extra)

    with index_path.open("a", encoding="utf-8") as file:
        json.dump(record, file, ensure_ascii=False)
        file.write("\n")


def read_index(index_path: Path) -> list[dict[str, Any]]:
    if not index_path.exists():
        return []
    records: list[dict[str, Any]] = []
    with index_path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))
    return records
