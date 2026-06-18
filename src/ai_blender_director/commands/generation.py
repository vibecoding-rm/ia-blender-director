import argparse
from pathlib import Path

from ..generator import write_generated_shot
from ..io import load_shot_spec
from ..planner import write_shot_plan

VERTICAL_RESOLUTION = {"width": 720, "height": 1280}


def resolution_for(args: argparse.Namespace) -> dict[str, int] | None:
    """9:16 vertical resolution for Shorts/TikTok/Reels when --vertical is set."""
    return VERTICAL_RESOLUTION if getattr(args, "vertical", False) else None


def register_parsers(subparsers: argparse._SubParsersAction) -> None:
    validate_parser = subparsers.add_parser("validate", help="Validate a shot JSON file.")
    validate_parser.add_argument("shot", type=Path)

    generate_parser = subparsers.add_parser("generate", help="Generate a shot JSON from a text prompt.")
    generate_parser.add_argument("prompt")
    generate_parser.add_argument("--output-dir", type=Path, default=Path("generated/shots"))
    generate_parser.add_argument("--duration", type=int, default=4)
    generate_parser.add_argument("--fps", type=int, default=24)
    generate_parser.add_argument("--vertical", action="store_true", help="Formato vertical 9:16 (Shorts/TikTok).")

    create_parser = subparsers.add_parser("create", help="Generate a shot from a prompt and optionally render it.")
    create_parser.add_argument("prompt")
    create_parser.add_argument("--shot-output-dir", type=Path, default=Path("generated/shots"))
    create_parser.add_argument("--output-root", type=Path, default=Path("renders/previews"))
    create_parser.add_argument("--duration", type=int, default=4)
    create_parser.add_argument("--fps", type=int, default=24)
    create_parser.add_argument("--profile", choices=["preview", "final"], default="preview")
    create_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"), help=argparse.SUPPRESS)
    create_parser.add_argument("--render", action="store_true")
    create_parser.add_argument("--dry-run", action="store_true")
    create_parser.add_argument("--vertical", action="store_true", help="Formato vertical 9:16 (Shorts/TikTok).")

    plan_parser = subparsers.add_parser(
        "plan",
        help="Director Agent: genera un plan de varios planos desde una idea.",
    )
    plan_parser.add_argument("prompt", help="Idea o descripción del video.")
    plan_parser.add_argument("--shots", type=int, default=3, help="Número de planos a generar (default: 3).")
    plan_parser.add_argument("--output-dir", type=Path, default=Path("generated/shots"))
    plan_parser.add_argument("--duration", type=int, default=4, help="Duración de cada plano en segundos.")
    plan_parser.add_argument("--fps", type=int, default=24)
    plan_parser.add_argument("--render", action="store_true", help="Renderizar todos los planos después de generarlos.")
    plan_parser.add_argument("--output-root", type=Path, default=Path("renders/previews"))
    plan_parser.add_argument("--profile", choices=["preview", "final"], default="preview")
    plan_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"), help=argparse.SUPPRESS)
    plan_parser.add_argument("--output-video", type=Path, default=None, help="Path for the final concatenated MP4.")
    plan_parser.add_argument("--vertical", action="store_true", help="Formato vertical 9:16 (Shorts/TikTok).")


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
        resolution=resolution_for(args),
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
        resolution=resolution_for(args),
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


def handle_plan(args: argparse.Namespace) -> int:
    paths = write_shot_plan(
        args.prompt,
        args.output_dir,
        n_shots=args.shots,
        duration_seconds=args.duration,
        fps=args.fps,
        resolution=resolution_for(args),
    )

    print(f"plan: {len(paths)} plano(s) generado(s)", flush=True)
    for path in paths:
        spec = load_shot_spec(path)
        print(f"  {path.name}  [{spec.camera.movement}]  {spec.scene}", flush=True)

    if not args.render:
        return 0

    from .render import render_shot_to_job
    from .video import assemble_frames_sync, concat_videos_sync
    from ..planner import slug_for_prompt

    job_dirs = []
    for path in paths:
        print(f"\nrenderizando: {path.name}", flush=True)
        code, job = render_shot_to_job(path, args.output_root, args.profile, args.index, dry_run=False)
        if code != 0:
            print(f"  fallo al renderizar {path.name}", flush=True)
        elif job:
            job_dirs.append(job.job_dir)

    if not job_dirs:
        return 1

    output_video = args.output_video
    if output_video is None:
        slug = slug_for_prompt(args.prompt)[:40]
        output_video = Path("renders") / f"plan_{slug}.mp4"

    shot_videos = []
    for jd in job_dirs:
        spec = load_shot_spec(jd / "shot.json")
        comfy_dir = jd / "comfy_output"
        if comfy_dir.exists() and any(comfy_dir.glob("*.png")):
            shot_video = jd / "shot_video.mp4"
            if assemble_frames_sync(comfy_dir, shot_video, fps=spec.fps, pattern="*.png"):
                shot_videos.append(shot_video)
                print(f"  ensamblado (estilizado): {shot_video}", flush=True)
            continue
        # Sin estilización: usar directamente el video renderizado por Blender.
        rendered = sorted(jd.glob("shot_*.mp4"))
        if rendered:
            shot_videos.append(rendered[0])
            print(f"  video: {rendered[0]}", flush=True)

    if shot_videos:
        output_video.parent.mkdir(parents=True, exist_ok=True)
        if concat_videos_sync(shot_videos, output_video):
            print(f"video: {output_video}", flush=True)
        else:
            print("warning: falló la concatenación de videos", flush=True)
    else:
        print("warning: no se generaron videos de planos", flush=True)

    return 0
