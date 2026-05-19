import argparse
from pathlib import Path

from ..generator import write_generated_shot
from ..io import load_shot_spec


def register_parsers(subparsers: argparse._SubParsersAction) -> None:
    validate_parser = subparsers.add_parser("validate", help="Validate a shot JSON file.")
    validate_parser.add_argument("shot", type=Path)

    generate_parser = subparsers.add_parser("generate", help="Generate a shot JSON from a text prompt.")
    generate_parser.add_argument("prompt")
    generate_parser.add_argument("--output-dir", type=Path, default=Path("generated/shots"))
    generate_parser.add_argument("--duration", type=int, default=4)
    generate_parser.add_argument("--fps", type=int, default=24)

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


def handle_validate(args: argparse.Namespace) -> int:
    spec = load_shot_spec(args.shot)
    print("valid shot")
    print(f"scene: {spec.scene}")
    print(f"duration: {spec.duration_seconds}s at {spec.fps} fps ({spec.frame_count} frames)")
    print(f"resolution: {spec.resolution.width}x{spec.resolution.height}")
    return 0


def handle_generate(args: argparse.Namespace) -> int:
    path = write_generated_shot(
        args.prompt,
        args.output_dir,
        duration_seconds=args.duration,
        fps=args.fps,
    )
    spec = load_shot_spec(path)
    print(path)
    print(f"scene: {spec.scene}")
    print(f"camera: {spec.camera.movement}")
    print(f"weather: {spec.weather or 'none'}")
    return 0


def handle_create(args: argparse.Namespace) -> int:
    shot_path = write_generated_shot(
        args.prompt,
        args.shot_output_dir,
        duration_seconds=args.duration,
        fps=args.fps,
    )
    spec = load_shot_spec(shot_path)
    print(f"shot: {shot_path}", flush=True)
    print(f"scene: {spec.scene}", flush=True)
    print(f"camera: {spec.camera.movement}", flush=True)
    print(f"weather: {spec.weather or 'none'}", flush=True)

    if not args.render:
        return 0

    # Inline import to avoid circular dependency
    from .render import run_render_shot
    return run_render_shot(shot_path, args.output_root, args.profile, args.index, args.dry_run)
