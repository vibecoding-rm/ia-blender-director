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
    pipeline_parser.add_argument(
        "--profile", choices=["preview", "final"], default="preview",
        help="Calidad de render. 'final' = máxima calidad (resolución completa, "
             "128 samples, raytracing) — para correr en GPU.",
    )
    pipeline_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"), help=argparse.SUPPRESS)
    pipeline_parser.add_argument("--workflow", default="stylization_v1")
    pipeline_parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    pipeline_parser.add_argument(
        "--shots", type=int, default=4,
        help="Number of shots (default 4 = secuencia multi-shot dirigida). "
             "Usa --shots 1 solo para un preview rápido de un encuadre.",
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
    pipeline_parser.add_argument(
        "--voice-character",
        default=None,
        help="asset_id del personaje narrador para elegir voz via TTS_CHARACTER_VOICES.",
    )
    pipeline_parser.add_argument(
        "--hook", default=None,
        help="Titular del gancho: tarjeta de apertura de 1.4s con texto gigante y sting.",
    )
    pipeline_parser.add_argument("--no-subtitles", action="store_true", help="No quemar subtítulos de la narración.")
    pipeline_parser.add_argument("--no-sfx", action="store_true", help="No mezclar efectos de sonido.")


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
    render_code, job = render_shot_to_job(shot_path, args.output_root, args.profile, args.index, False)
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
                args.output_root, args.index, args.profile,
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
    profile: str = "preview",
):
    """Apply critic corrections and re-render once. Returns the new RenderJob or None on failure."""
    from ..corrector import apply_corrections

    corrected_path = apply_corrections(shot_path, feedbacks)
    print(f"  corrected spec: {corrected_path.name}")

    code, job = render_shot_to_job(corrected_path, output_root, profile, index_path, dry_run=False)
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

    # Lip-sync de punta a punta: sintetiza la narración ANTES de renderizar,
    # genera la timeline de visemas (Rhubarb) y la inyecta en cada plano para
    # que Blender mueva el pico de La Cotorra al hablar.
    narration_voice = _voice_for_narration(args, paths)
    narration_wav = _prepare_lipsync(
        args, paths, slug_for_prompt(args.prompt)[:40], voice=narration_voice
    )

    job_dirs: list[Path] = []

    for i, path in enumerate(paths, 1):
        print(f"\n=== SHOT {i}/{len(paths)}: {path.name} ===")

        print("\n--- [RENDER] ---")
        code, job = render_shot_to_job(path, args.output_root, args.profile, args.index, False)
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
                            args.output_root, args.index, args.profile,
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
    shot_durations: list[float] = []
    first_spec = None
    for jd in job_dirs:
        spec = load_shot_spec(jd / "shot.json")
        comfy_dir = jd / "comfy_output"
        if comfy_dir.exists() and any(comfy_dir.glob("*.png")):
            shot_video = jd / "shot_video.mp4"
            if assemble_frames_sync(comfy_dir, shot_video, fps=spec.fps, pattern="*.png"):
                shot_videos.append(shot_video)
                shot_durations.append(float(spec.duration_seconds))
                first_spec = first_spec or spec
                print(f"  {shot_video.name} (estilizado)")
            continue
        # Sin estilización: usar directamente el video renderizado por Blender.
        rendered = sorted(jd.glob("shot_*.mp4"))
        if rendered:
            shot_videos.append(rendered[0])
            shot_durations.append(float(spec.duration_seconds))
            first_spec = first_spec or spec
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

    print("\n=== [5/5] POSTPRODUCCIÓN (gancho + audio + subtítulos) ===")
    from ..postproduction import produce_short

    # Gráficos de broadcast: se activan solos cuando la escena es un noticiero.
    lower_third = ticker_text = corner_bug = None
    scene_text = (first_spec.scene + " " + first_spec.subject).lower()
    is_news = any(w in scene_text for w in ("news", "studio", "noticier", "cotorra", "anchor", "plaza"))
    if is_news:
        lower_third = ("La Cotorra", "Corresponsal Oficial")
        ticker_text = args.narration or args.hook or "Noticias 100% oficiales del régimen"
        corner_bug = "Última Hora" if args.hook else "En Vivo"

    final = produce_short(
        shot_videos,
        shot_durations,
        output_video,
        resolution=(first_spec.resolution.width, first_spec.resolution.height),
        fps=int(first_spec.fps),
        hook_title=args.hook,
        narration_text=args.narration,
        voice=narration_voice,
        subtitles=not args.no_subtitles,
        sfx=not args.no_sfx,
        narration_wav=narration_wav,
        lower_third=lower_third,
        ticker_text=ticker_text,
        corner_bug=corner_bug,
    )
    if final is None:
        print("error: falló la postproducción", file=sys.stderr)
        return 1
    print(f"video final: {final}")
    return 0


def _prepare_lipsync(
    args: argparse.Namespace,
    paths: list[Path],
    slug: str,
    *,
    voice: Path | None = None,
) -> Path | None:
    """Sintetiza la narración e inyecta visemas en cada plano. Devuelve el WAV.

    Devuelve None (sin lip-sync, sin reutilizar WAV) si no hay narración o si
    falla la síntesis. Si Rhubarb no está instalado, igualmente devuelve el WAV
    (para reutilizarlo en postproducción) pero no inyecta visemas.
    """
    if not args.narration:
        return None

    from ..tts import synthesize
    from ..lipsync import generate_visemes

    work_root = args.output_root
    work_root.mkdir(parents=True, exist_ok=True)
    narration_wav = (work_root / f"_narration_{slug}.wav").resolve()

    print("\n=== [PRE] NARRACIÓN + LIP-SYNC ===")
    narration_voice = voice or _voice_for_narration(args, paths)
    if not synthesize(args.narration, narration_wav, voice=narration_voice):
        print("  warning: falló la síntesis de voz; sin lip-sync", file=sys.stderr)
        return None
    print(f"  narración: {narration_wav.name}")

    viseme_json = (work_root / f"_visemes_{slug}.json").resolve()
    if generate_visemes(narration_wav, viseme_json) is None:
        print("  rhubarb no disponible: se usa la animación Talk embebida")
        return narration_wav

    injected = 0
    for i, path in enumerate(paths):
        if _inject_lipsync(path, viseme_json, offset=i * float(args.duration)):
            injected += 1
    print(f"  visemas inyectados en {injected}/{len(paths)} plano(s)")
    return narration_wav


def _voice_for_narration(args: argparse.Namespace, paths: list[Path]) -> Path | None:
    """Devuelve la voz explicita o la voz mapeada para el personaje narrador."""
    explicit_voice = getattr(args, "voice", None)
    requested_character = getattr(args, "voice_character", None)
    character = requested_character or _first_character(paths)

    from ..tts import voice_for_character

    return voice_for_character(character, explicit_voice=explicit_voice)


def _first_character(paths: list[Path]) -> str | None:
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        assets = data.get("assets") or {}
        character = data.get("character") or assets.get("character")
        if character:
            return str(character)
    return None


def _inject_lipsync(shot_path: Path, viseme_json: Path, *, offset: float) -> bool:
    """Añade visemes_path + narration_offset al shot.json si tiene personaje."""
    data = json.loads(shot_path.read_text(encoding="utf-8"))
    has_character = data.get("character") or (data.get("assets") or {}).get("character")
    if not has_character:
        return False
    data["visemes_path"] = str(viseme_json)
    data["narration_offset"] = offset
    shot_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return True
