import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from ..index import append_index_event
from ..io import load_shot_spec
from ..jobs import create_render_job, update_render_job_status

ROOT = Path(__file__).resolve().parents[3]
BLENDER_SCRIPT = ROOT / "scripts" / "blender" / "render_shot.py"


def register_parsers(subparsers: argparse._SubParsersAction) -> None:
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


def handle_blender_command(args: argparse.Namespace) -> int:
    load_shot_spec(args.shot)
    print(" ".join(_build_blender_command(args.shot, args.output, profile=args.profile)))
    return 0


def handle_render(args: argparse.Namespace) -> int:
    return run_render_shot(args.shot, args.output_root, args.profile, args.index, args.dry_run)


def run_render_shot(path: Path, output_root: Path, profile: str, index_path: Path, dry_run: bool) -> int:
    blender = shutil.which("blender")
    if blender is None:
        print("error: blender was not found in PATH", file=sys.stderr)
        return 2

    _warn_missing_asset_paths(path)
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


def _read_json_if_exists(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _warn_missing_asset_paths(shot_path: Path) -> None:
    data = _read_json_if_exists(shot_path)
    if not data:
        return
    assets_root = ROOT / "assets"
    type_dirs = {
        "character": "characters",
        "environment": "environments",
        "animation": "animations",
    }
    for ref_key, asset_dir in type_dirs.items():
        asset_id = data.get(ref_key)
        if not asset_id:
            continue
        manifest = assets_root / asset_dir / asset_id / "asset.json"
        if not manifest.exists():
            continue
        manifest_data = _read_json_if_exists(manifest)
        if not manifest_data:
            continue
        raw_path = manifest_data.get("path")
        if raw_path:
            resolved = (manifest.parent / raw_path).resolve()
            if not resolved.exists():
                print(
                    f"warning: asset '{asset_id}' path not found: {resolved}",
                    file=sys.stderr,
                )
