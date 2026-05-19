from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .jobs import RenderJob
from .db import SessionLocal, JobRecord


def append_index_event(
    index_path: Path,
    job: RenderJob,
    event: str,
    *,
    status: str,
    returncode: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    # index_path is kept for backward compatibility with CLI, but we use SQLite.
    with SessionLocal() as db:
        # Check if job exists
        record = db.query(JobRecord).filter(JobRecord.job_id == job.job_id).first()
        if not record:
            record = JobRecord(
                job_id=job.job_id,
                status=status,
                event=event,
                profile=job.profile,
                job_dir=str(job.job_dir),
                source_shot=str(job.source_shot),
                returncode=returncode
            )
            db.add(record)
        else:
            record.status = status
            record.event = event
            if returncode is not None:
                record.returncode = returncode
        db.commit()


def latest_job_records(index_path: Path) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        records = db.query(JobRecord).order_by(JobRecord.timestamp.desc()).all()
        return [
            {
                "job_id": r.job_id,
                "status": r.status,
                "event": r.event,
                "profile": r.profile,
                "job_dir": r.job_dir,
                "source_shot": r.source_shot,
                "returncode": r.returncode,
                "timestamp": r.timestamp.isoformat() if r.timestamp else ""
            }
            for r in records
        ]


def find_job_record(index_path: Path, job_id: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        record = db.query(JobRecord).filter(JobRecord.job_id.startswith(job_id)).first()
        if not record:
            return None
        return {
            "job_id": record.job_id,
            "status": record.status,
            "event": record.event,
            "profile": record.profile,
            "job_dir": record.job_dir,
            "source_shot": record.source_shot,
            "returncode": record.returncode,
            "timestamp": record.timestamp.isoformat() if record.timestamp else ""
        }
