from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .assets import AssetRegistry, AssetValidationError
from .generator import write_generated_shot
from .index import append_index_event, find_job_record, latest_job_records
from .io import load_shot_spec
from .jobs import create_render_job, update_render_job_status
from .models import ShotValidationError


ROOT = Path(__file__).resolve().parents[2]
BLENDER_SCRIPT = ROOT / "scripts" / "blender" / "render_shot.py"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-blender-director")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a shot JSON file.")
    validate_parser.add_argument("shot", type=Path)

    generate_parser = subparsers.add_parser("generate", help="Generate a shot JSON from a text prompt.")
    generate_parser.add_argument("prompt")
    generate_parser.add_argument("--output-dir", type=Path, default=Path("generated/shots"))
    generate_parser.add_argument("--duration", type=int, default=4)
    generate_parser.add_argument("--fps", type=int, default=24)

    command_parser = subparsers.add_parser(
        "blender-command",
        help="Print the Blender command for rendering a shot.",
    )
    command_parser.add_argument("shot", type=Path)
    command_parser.add_argument("--output", type=Path, default=Path("renders/previews"))
    command_parser.add_argument("--profile", choices=["preview", "final"], default="preview")

    render_parser = subparsers.add_parser("render", help="Create a render job and run Blender.")
    render_parser.add_argument("shot", type=Path)
    render_parser.add_argument("--output-root", type=Path, default=Path("renders/previews"))
    render_parser.add_argument("--profile", choices=["preview", "final"], default="preview")
    render_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"))
    render_parser.add_argument("--dry-run", action="store_true")

    create_parser = subparsers.add_parser("create", help="Generate a shot from a prompt and optionally render it.")
    create_parser.add_argument("prompt")
    create_parser.add_argument("--shot-output-dir", type=Path, default=Path("generated/shots"))
    create_parser.add_argument("--output-root", type=Path, default=Path("renders/previews"))
    create_parser.add_argument("--duration", type=int, default=4)
    create_parser.add_argument("--fps", type=int, default=24)
    create_parser.add_argument("--profile", choices=["preview", "final"], default="preview")
    create_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"))
    create_parser.add_argument("--render", action="store_true")
    create_parser.add_argument("--dry-run", action="store_true")

    jobs_parser = subparsers.add_parser("jobs", help="List recent render jobs from the index.")
    jobs_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"))
    jobs_parser.add_argument("--limit", type=int, default=10)

    show_parser = subparsers.add_parser("show", help="Show details for a render job.")
    show_parser.add_argument("job_id")
    show_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"))

    assets_parser = subparsers.add_parser("assets", help="List registered character, environment, and animation assets.")
    assets_parser.add_argument("--root", type=Path, default=Path("assets"))
    assets_parser.add_argument("--type", choices=["character", "environment", "animation"])

    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            return _validate(args.shot)
        if args.command == "generate":
            return _generate(args.prompt, args.output_dir, args.duration, args.fps)
        if args.command == "blender-command":
            return _blender_command(args.shot, args.output, args.profile)
        if args.command == "render":
            return _render(args.shot, args.output_root, args.profile, args.index, args.dry_run)
        if args.command == "create":
            return _create(
                args.prompt,
                args.shot_output_dir,
                args.output_root,
                args.duration,
                args.fps,
                args.profile,
                args.index,
                args.render,
                args.dry_run,
            )
        if args.command == "jobs":
            return _jobs(args.index, args.limit)
        if args.command == "show":
            return _show(args.index, args.job_id)
        if args.command == "assets":
            return _assets(args.root, args.type)
    except AssetValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ShotValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"Unknown command: {args.command}")
    return 2


def _validate(path: Path) -> int:
    spec = load_shot_spec(path)
    print("valid shot")
    print(f"scene: {spec.scene}")
    print(f"duration: {spec.duration_seconds}s at {spec.fps} fps ({spec.frame_count} frames)")
    print(f"resolution: {spec.resolution.width}x{spec.resolution.height}")
    return 0


def _generate(prompt: str, output_dir: Path, duration_seconds: int, fps: int) -> int:
    path = write_generated_shot(
        prompt,
        output_dir,
        duration_seconds=duration_seconds,
        fps=fps,
    )
    spec = load_shot_spec(path)
    print(path)
    print(f"scene: {spec.scene}")
    print(f"camera: {spec.camera.movement}")
    print(f"weather: {spec.weather or 'none'}")
    return 0


def _blender_command(path: Path, output: Path, profile: str) -> int:
    load_shot_spec(path)
    print(" ".join(_build_blender_command(path, output, profile=profile)))
    return 0


def _render(path: Path, output_root: Path, profile: str, index_path: Path, dry_run: bool) -> int:
    return _render_shot(path, output_root, profile, index_path, dry_run)


def _create(
    prompt: str,
    shot_output_dir: Path,
    output_root: Path,
    duration_seconds: int,
    fps: int,
    profile: str,
    index_path: Path,
    should_render: bool,
    dry_run: bool,
) -> int:
    shot_path = write_generated_shot(
        prompt,
        shot_output_dir,
        duration_seconds=duration_seconds,
        fps=fps,
    )
    spec = load_shot_spec(shot_path)
    print(f"shot: {shot_path}", flush=True)
    print(f"scene: {spec.scene}", flush=True)
    print(f"camera: {spec.camera.movement}", flush=True)
    print(f"weather: {spec.weather or 'none'}", flush=True)

    if not should_render:
        return 0

    return _render_shot(shot_path, output_root, profile, index_path, dry_run)


def _render_shot(path: Path, output_root: Path, profile: str, index_path: Path, dry_run: bool) -> int:
    blender = shutil.which("blender")
    if blender is None:
        print("error: blender was not found in PATH", file=sys.stderr)
        return 2

    job = create_render_job(path, output_root, profile=profile)
    command = _build_blender_command(job.job_shot, job.job_dir, profile=profile, blender=blender)
    append_index_event(index_path, job, "created", status="created")

    print(f"job: {job.job_id}", flush=True)
    print(f"job_dir: {job.job_dir}", flush=True)
    print(f"profile: {job.profile}", flush=True)
    print("command: " + " ".join(command), flush=True)
    if dry_run:
        append_index_event(index_path, job, "dry_run", status="created")
        return 0

    update_render_job_status(job, "running")
    append_index_event(index_path, job, "started", status="running")
    completed = subprocess.run(command, check=False)
    status = "completed" if completed.returncode == 0 else "failed"
    update_render_job_status(job, status, returncode=completed.returncode)
    append_index_event(
        index_path,
        job,
        "finished",
        status=status,
        returncode=completed.returncode,
    )
    return completed.returncode


def _jobs(index_path: Path, limit: int) -> int:
    records = latest_job_records(index_path)
    if not records:
        print(f"no jobs found in {index_path}")
        return 0

    for record in records[: max(1, limit)]:
        print(
            f"{record['job_id']}  {record['status']}  {record['event']}  "
            f"{record['profile']}  {record['timestamp']}"
        )
    return 0


def _show(index_path: Path, job_id: str) -> int:
    record = find_job_record(index_path, job_id)
    if record is None:
        print(f"error: job not found: {job_id}", file=sys.stderr)
        return 2

    job_dir = Path(record["job_dir"])
    job_manifest = _read_json_if_exists(job_dir / "job.json")
    render_manifest = _read_json_if_exists(job_dir / "manifest.json")

    print(f"job: {record['job_id']}")
    print(f"status: {record['status']}")
    print(f"event: {record['event']}")
    print(f"profile: {record['profile']}")
    print(f"job_dir: {job_dir}")
    print(f"source_shot: {record['source_shot']}")
    if "returncode" in record:
        print(f"returncode: {record['returncode']}")

    if job_manifest:
        shot = job_manifest.get("shot", {})
        print(f"scene: {shot.get('scene', 'unknown')}")
        print(f"duration: {shot.get('duration_seconds', 'unknown')}s")

    if render_manifest:
        print(f"video: {render_manifest.get('video', 'unknown')}")
        print(f"blend_file: {render_manifest.get('blend_file', 'unknown')}")
        passes = render_manifest.get("passes", {})
        if passes:
            print("passes:")
            for name, path in sorted(passes.items()):
                print(f"  {name}: {path}")
    return 0


def _assets(root: Path, asset_type: str | None) -> int:
    assets = AssetRegistry(root).list_assets(asset_type)
    if not assets:
        print(f"no assets found in {root}")
        return 0

    for asset in assets:
        path_status = "placeholder" if asset.path is None else str(asset.path)
        exists = "ready" if asset.exists else "missing-file"
        print(f"{asset.asset_type:11} {asset.asset_id:28} {asset.source:24} {exists:12} {path_status}")
    return 0


def _read_json_if_exists(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _build_blender_command(
    path: Path,
    output: Path,
    *,
    profile: str,
    blender: str | None = None,
) -> list[str]:
    executable = blender or shutil.which("blender") or "blender"
    return [
        executable,
        "--background",
        "--python",
        str(BLENDER_SCRIPT),
        "--",
        str(path),
        str(output),
        profile,
    ]


if __name__ == "__main__":
    raise SystemExit(main())
