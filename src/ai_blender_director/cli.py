from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from .generator import write_generated_shot
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

    render_parser = subparsers.add_parser("render", help="Create a render job and run Blender.")
    render_parser.add_argument("shot", type=Path)
    render_parser.add_argument("--output-root", type=Path, default=Path("renders/previews"))
    render_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            return _validate(args.shot)
        if args.command == "generate":
            return _generate(args.prompt, args.output_dir, args.duration, args.fps)
        if args.command == "blender-command":
            return _blender_command(args.shot, args.output)
        if args.command == "render":
            return _render(args.shot, args.output_root, args.dry_run)
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


def _blender_command(path: Path, output: Path) -> int:
    load_shot_spec(path)
    print(" ".join(_build_blender_command(path, output)))
    return 0


def _render(path: Path, output_root: Path, dry_run: bool) -> int:
    blender = shutil.which("blender")
    if blender is None:
        print("error: blender was not found in PATH", file=sys.stderr)
        return 2

    job = create_render_job(path, output_root)
    command = _build_blender_command(job.job_shot, job.job_dir, blender=blender)

    print(f"job: {job.job_id}", flush=True)
    print(f"job_dir: {job.job_dir}", flush=True)
    print("command: " + " ".join(command), flush=True)
    if dry_run:
        return 0

    update_render_job_status(job, "running")
    completed = subprocess.run(command, check=False)
    status = "completed" if completed.returncode == 0 else "failed"
    update_render_job_status(job, status, returncode=completed.returncode)
    return completed.returncode


def _build_blender_command(path: Path, output: Path, *, blender: str | None = None) -> list[str]:
    executable = blender or shutil.which("blender") or "blender"
    return [
        executable,
        "--background",
        "--python",
        str(BLENDER_SCRIPT),
        "--",
        str(path),
        str(output),
    ]


if __name__ == "__main__":
    raise SystemExit(main())
