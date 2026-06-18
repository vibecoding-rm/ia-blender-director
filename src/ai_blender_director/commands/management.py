import argparse
import json
import shutil
import sys
import urllib.request
from pathlib import Path

from ..assets import AssetRegistry
from ..config import settings
from ..index import find_job_record, latest_job_records
from .render import _resolve_blender_executable

ROOT = Path(__file__).resolve().parents[3]


def register_parsers(subparsers: argparse._SubParsersAction) -> None:
    jobs_parser = subparsers.add_parser("jobs", help="List recent render jobs from SQLite.")
    jobs_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"), help=argparse.SUPPRESS)
    jobs_parser.add_argument("--limit", type=int, default=10)

    show_parser = subparsers.add_parser("show", help="Show details for a render job.")
    show_parser.add_argument("job_id")
    show_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"), help=argparse.SUPPRESS)

    assets_parser = subparsers.add_parser("assets", help="List registered character, environment, and animation assets.")
    assets_parser.add_argument("--root", type=Path, default=Path("assets"))
    assets_parser.add_argument("--type", choices=["character", "environment", "animation"])

    preflight_parser = subparsers.add_parser("preflight", help="Check local runtime dependencies before rendering.")
    preflight_parser.add_argument("--check-comfy", action="store_true", help="Also verify that ComfyUI is reachable.")


def handle_jobs(args: argparse.Namespace) -> int:
    records = latest_job_records(args.index)
    if not records:
        print("no jobs found in SQLite job store")
        return 0

    for record in records[: max(1, args.limit)]:
        print(
            f"{record['job_id']}  {record['status']}  {record['event']}  "
            f"{record['profile']}  {record['timestamp']}"
        )
    return 0


def handle_show(args: argparse.Namespace) -> int:
    record = find_job_record(args.index, args.job_id)
    if record is None:
        print(f"error: job not found: {args.job_id}", file=sys.stderr)
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


def handle_assets(args: argparse.Namespace) -> int:
    assets = AssetRegistry(args.root).list_assets(args.type)
    if not assets:
        print(f"no assets found in {args.root}")
        return 0

    for asset in assets:
        path_status = "placeholder" if asset.path is None else str(asset.path)
        exists = "ready" if asset.exists else "missing-file"
        print(f"{asset.asset_type:11} {asset.asset_id:28} {asset.source:24} {exists:12} {path_status}")
    return 0


def handle_preflight(args: argparse.Namespace) -> int:
    checks = [
        ("Blender", _resolve_blender_executable(), settings.blender_executable),
        ("FFmpeg", shutil.which("ffmpeg"), "ffmpeg"),
        ("FFprobe", shutil.which("ffprobe"), "ffprobe"),
    ]

    failed = False
    for name, resolved, configured in checks:
        if resolved:
            print(f"ok: {name}: {resolved}")
        else:
            print(f"error: {name} not found ({configured})", file=sys.stderr)
            failed = True

    for path, label in [
        (ROOT / "assets", "assets directory"),
        (ROOT / "workflows" / "comfy", "ComfyUI workflows"),
    ]:
        if path.exists():
            print(f"ok: {label}: {path}")
        else:
            print(f"error: {label} not found: {path}", file=sys.stderr)
            failed = True

    if args.check_comfy:
        try:
            urllib.request.urlopen(settings.comfy_url, timeout=3)
            print(f"ok: ComfyUI reachable: {settings.comfy_url}")
        except Exception as exc:
            print(f"error: ComfyUI unreachable at {settings.comfy_url}: {exc}", file=sys.stderr)
            failed = True

    return 2 if failed else 0


def _read_json_if_exists(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)
