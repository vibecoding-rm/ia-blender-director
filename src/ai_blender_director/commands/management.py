import argparse
import json
import sys
from pathlib import Path

from ..assets import AssetRegistry
from ..index import find_job_record, latest_job_records


def register_parsers(subparsers: argparse._SubParsersAction) -> None:
    jobs_parser = subparsers.add_parser("jobs", help="List recent render jobs from the index.")
    jobs_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"))
    jobs_parser.add_argument("--limit", type=int, default=10)

    show_parser = subparsers.add_parser("show", help="Show details for a render job.")
    show_parser.add_argument("job_id")
    show_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"))

    assets_parser = subparsers.add_parser("assets", help="List registered character, environment, and animation assets.")
    assets_parser.add_argument("--root", type=Path, default=Path("assets"))
    assets_parser.add_argument("--type", choices=["character", "environment", "animation"])


def handle_jobs(args: argparse.Namespace) -> int:
    records = latest_job_records(args.index)
    if not records:
        print(f"no jobs found in {args.index}")
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


def _read_json_if_exists(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)
