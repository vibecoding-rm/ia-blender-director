import argparse
import json
import sys
from pathlib import Path

from ..generator import write_generated_shot
from ..io import load_shot_spec
from .render import render_shot_to_job
from ..critic import VisionCritic
from .post_processing import run_comfy_render


def register_parsers(subparsers: argparse._SubParsersAction) -> None:
    pipeline_parser = subparsers.add_parser(
        "auto-director",
        help="Run the full automated pipeline: Generate -> Render -> Critic -> ComfyUI",
    )
    pipeline_parser.add_argument("prompt")
    pipeline_parser.add_argument("--shot-output-dir", type=Path, default=Path("generated/shots"))
    pipeline_parser.add_argument("--output-root", type=Path, default=Path("renders/previews"))
    pipeline_parser.add_argument("--duration", type=int, default=4)
    pipeline_parser.add_argument("--fps", type=int, default=24)
    pipeline_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"))
    pipeline_parser.add_argument("--workflow", default="stylization_v1")
    pipeline_parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    pipeline_parser.add_argument(
        "--shots", type=int, default=1,
        help="Number of shots; >1 uses the Director Agent to generate a multi-shot plan.",
    )
    pipeline_parser.add_argument("--output-video", type=Path, default=None)
    pipeline_parser.add_argument(
        "--no-comfy", action="store_true",
        help="Skip the ComfyUI stylization step (e.g. when no ComfyUI server is available).",
    )
    pipeline_parser.add_argument("--vertical", action="store_true", help="Formato vertical 9:16 (Shorts/TikTok).")
    pipeline_parser.add_argument(
        "--narration", default=None,
        help="Texto de narración: se sintetiza con piper-tts y se mezcla sobre el video final.",
    )
    pipeline_parser.add_argument("--voice", type=Path, default=None, help="Ruta a un modelo de voz piper (.onnx).")


def handle_auto_director(args: argparse.Namespace) -> int:
    if args.shots > 1:
        return _handle_multi_shot(args)
    return _handle_single_shot(args)


def _handle_single_shot(args: argparse.Namespace) -> int:
    print("=== [1/4] GENERATING SPEC ===")
    shot_path = write_generated_shot(
        args.prompt,
        args.shot_output_dir,
        duration_seconds=args.duration,
        fps=args.fps,
    )
    spec = load_shot_spec(shot_path)
    print(f"Created shot: {shot_path.name}")
    print(f"Scene: {spec.scene}")

    print("\n=== [2/4] RENDERING IN BLENDER ===")
    render_code, job = render_shot_to_job(shot_path, args.output_root, "preview", args.index, False)
    if render_code != 0:
        print("Render failed. Stopping pipeline.")
        return render_code

    print(f"Render completed. Job ID: {job.job_id}")

    print("\n=== [3/4] VISION CRITIC ANALYSIS ===")
    manifest_path = job.job_dir / "manifest.json"
    if not manifest_path.exists():
        print("No manifest found after render. Stopping pipeline.")
        return 2

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    passes = manifest.get("passes", {})
    beauty_pass = passes.get("beauty")
    mask_pass = passes.get("subject_mask")

    if beauty_pass and mask_pass:
        critic = VisionCritic(job.job_dir / beauty_pass, job.job_dir / mask_pass)
        feedbacks = critic.analyze()

        has_critical_issues = any(fb.level == "WARNING" for fb in feedbacks)
        if feedbacks:
            print(f"VisionCritic found {len(feedbacks)} issues:")
            for fb in feedbacks:
                print(f"  [{fb.level}] {fb.category}: {fb.message}")
        else:
            print("VisionCritic: OK. No issues detected.")

        if has_critical_issues:
            print("Critical warnings detected. Attempting auto-correction (1 retry).")
            corrected = _auto_correct_and_rerender(
                job.job_dir / "shot.json", feedbacks,
                args.output_root, args.index,
            )
            if corrected is None:
                print("Auto-correction failed or not applicable. Stopping.")
                return 2
            job = corrected
    else:
        print("Warning: Missing passes for VisionCritic. Skipping analysis.")

    print("\n=== [4/4] COMFYUI STYLIZATION ===")
    return run_comfy_render(args.index, job.job_id, args.workflow, args.comfy_url)


def _auto_correct_and_rerender(
    shot_path: Path,
    feedbacks: list,
    output_root: Path,
    index_path: Path,
):
    """Apply critic corrections and re-render once. Returns the new RenderJob or None on failure."""
    from ..corrector import apply_corrections

    corrected_path = apply_corrections(shot_path, feedbacks)
    print(f"  corrected spec: {corrected_path.name}")

    code, job = render_shot_to_job(corrected_path, output_root, "preview", index_path, dry_run=False)
    if code != 0:
        return None
    print(f"  re-render completed: {job.job_id}")
    return job


def _handle_multi_shot(args: argparse.Namespace) -> int:
    from ..planner import write_shot_plan, slug_for_prompt
    from .video import assemble_frames_sync, concat_videos_sync
    from .generation import resolution_for

    print(f"=== [1/4] DIRECTOR AGENT: GENERANDO {args.shots} PLANOS ===")
    paths = write_shot_plan(
        args.prompt,
        args.shot_output_dir,
        n_shots=args.shots,
        duration_seconds=args.duration,
        fps=args.fps,
        resolution=resolution_for(args),
    )
    print(f"  {len(paths)} plano(s) generado(s)")
    for p in paths:
        spec = load_shot_spec(p)
        print(f"  {p.name}  [{spec.camera.movement}]  {spec.scene}")

    job_dirs: list[Path] = []

    for i, path in enumerate(paths, 1):
        print(f"\n=== SHOT {i}/{len(paths)}: {path.name} ===")

        print("\n--- [RENDER] ---")
        code, job = render_shot_to_job(path, args.output_root, "preview", args.index, False)
        if code != 0 or job is None:
            print(f"  Render fallido para {path.name} — omitiendo")
            continue

        print("\n--- [CRITIC] ---")
        manifest_path = job.job_dir / "manifest.json"
        skip_comfy = False
        if manifest_path.exists():
            with manifest_path.open() as f:
                manifest = json.load(f)
            passes = manifest.get("passes", {})
            beauty_p = passes.get("beauty")
            mask_p = passes.get("subject_mask")
            if beauty_p and mask_p:
                critic = VisionCritic(job.job_dir / beauty_p, job.job_dir / mask_p)
                feedbacks = critic.analyze()
                if feedbacks:
                    print(f"  {len(feedbacks)} issue(s):")
                    for fb in feedbacks:
                        print(f"    [{fb.level}] {fb.category}: {fb.message}")
                    if any(fb.level == "WARNING" for fb in feedbacks):
                        print("  WARNING detectado — aplicando auto-corrección")
                        corrected_job = _auto_correct_and_rerender(
                            job.job_dir / "shot.json", feedbacks,
                            args.output_root, args.index,
                        )
                        if corrected_job:
                            job = corrected_job
                        else:
                            skip_comfy = True
                else:
                    print("  OK")

        if not skip_comfy and not args.no_comfy:
            print("\n--- [COMFY] ---")
            run_comfy_render(args.index, job.job_id, args.workflow, args.comfy_url)

        job_dirs.append(job.job_dir)

    if not job_dirs:
        print("error: todos los renders fallaron", file=sys.stderr)
        return 1

    print(f"\n=== [4/4] ENSAMBLAJE MULTI-SHOT ({len(job_dirs)} plano(s)) ===")
    shot_videos: list[Path] = []
    for jd in job_dirs:
        spec = load_shot_spec(jd / "shot.json")
        comfy_dir = jd / "comfy_output"
        if comfy_dir.exists() and any(comfy_dir.glob("*.png")):
            shot_video = jd / "shot_video.mp4"
            if assemble_frames_sync(comfy_dir, shot_video, fps=spec.fps, pattern="*.png"):
                shot_videos.append(shot_video)
                print(f"  {shot_video.name} (estilizado)")
            continue
        # Sin estilización: usar directamente el video renderizado por Blender.
        rendered = sorted(jd.glob("shot_*.mp4"))
        if rendered:
            shot_videos.append(rendered[0])
            print(f"  {rendered[0].name}")
        else:
            print(f"  warning: no se encontró video renderizado en {jd}", file=sys.stderr)

    if not shot_videos:
        print("warning: no se encontraron frames para ensamblar", file=sys.stderr)
        return 1

    output_video = args.output_video
    if output_video is None:
        slug = slug_for_prompt(args.prompt)[:40]
        output_video = Path("renders") / f"plan_{slug}.mp4"

    output_video.parent.mkdir(parents=True, exist_ok=True)
    if not concat_videos_sync(shot_videos, output_video):
        print("warning: falló la concatenación final", file=sys.stderr)
        return 1
    print(f"video final: {output_video}")

    if args.narration:
        from ..tts import synthesize, mux_narration

        print("\n=== [5/5] NARRACIÓN TTS ===")
        narration_wav = output_video.with_suffix(".narration.wav")
        if synthesize(args.narration, narration_wav, voice=args.voice):
            narrated = output_video.with_stem(output_video.stem + "_narrado")
            if mux_narration(output_video, narration_wav, narrated):
                print(f"video narrado: {narrated}")
            else:
                print("warning: falló la mezcla de narración", file=sys.stderr)
        else:
            print("warning: falló la síntesis de voz", file=sys.stderr)

    return 0
