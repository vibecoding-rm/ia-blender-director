from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .io import load_shot_spec
from .models import ShotValidationError


ROOT = Path(__file__).resolve().parents[2]
BLENDER_SCRIPT = ROOT / "scripts" / "blender" / "render_shot.py"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-blender-director")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a shot JSON file.")
    validate_parser.add_argument("shot", type=Path)

    command_parser = subparsers.add_parser(
        "blender-command",
        help="Print the Blender command for rendering a shot.",
    )
    command_parser.add_argument("shot", type=Path)
    command_parser.add_argument("--output", type=Path, default=Path("renders/previews"))

    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            return _validate(args.shot)
        if args.command == "blender-command":
            return _blender_command(args.shot, args.output)
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


def _blender_command(path: Path, output: Path) -> int:
    load_shot_spec(path)
    blender = shutil.which("blender") or "blender"
    print(f"{blender} --background --python {BLENDER_SCRIPT} -- {path} {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
