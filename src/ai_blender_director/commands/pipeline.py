import argparse
import json
import sys
from pathlib import Path

from ..generator import write_generated_shot
from ..io import load_shot_spec
from .render import run_render_shot
from ..index import latest_job_records
from ..critic import VisionCritic
from .post_processing import run_comfy_render

def register_parsers(subparsers: argparse._SubParsersAction) -> None:
    pipeline_parser = subparsers.add_parser("auto-director", help="Run the full automated pipeline: Generate -> Render -> Critic -> ComfyUI")
    pipeline_parser.add_argument("prompt")
    pipeline_parser.add_argument("--shot-output-dir", type=Path, default=Path("generated/shots"))
    pipeline_parser.add_argument("--output-root", type=Path, default=Path("renders/previews"))
    pipeline_parser.add_argument("--duration", type=int, default=4)
    pipeline_parser.add_argument("--fps", type=int, default=24)
    pipeline_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"))
    pipeline_parser.add_argument("--workflow", default="stylization_v1")
    pipeline_parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")


def handle_auto_director(args: argparse.Namespace) -> int:
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
    render_code = run_render_shot(shot_path, args.output_root, "preview", args.index, False)
    if render_code != 0:
        print("Render failed. Stopping pipeline.")
        return render_code
        
    # Find the job ID that was just created
    records = latest_job_records(args.index)
    if not records:
        print("Could not find job record. Stopping pipeline.")
        return 2
        
    latest_job = records[0]
    job_id = latest_job["job_id"]
    job_dir = Path(latest_job["job_dir"])
    print(f"Render completed. Job ID: {job_id}")
    
    print("\n=== [3/4] VISION CRITIC ANALYSIS ===")
    manifest_path = job_dir / "manifest.json"
    if not manifest_path.exists():
        print("No manifest found after render. Stopping pipeline.")
        return 2
        
    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)
        
    passes = manifest.get("passes", {})
    beauty_pass = passes.get("beauty")
    mask_pass = passes.get("subject_mask")
    
    if beauty_pass and mask_pass:
        beauty_path = job_dir / beauty_pass
        mask_path = job_dir / mask_pass
        critic = VisionCritic(beauty_path, mask_path)
        feedbacks = critic.analyze()
        
        has_critical_issues = False
        if feedbacks:
            print(f"VisionCritic found {len(feedbacks)} issues:")
            for fb in feedbacks:
                print(f"  [{fb.level}] {fb.category}: {fb.message}")
                if fb.level == "WARNING":
                    has_critical_issues = True
        else:
            print("VisionCritic: OK. No issues detected.")
            
        if has_critical_issues:
            print("Critical warnings detected by VisionCritic. Stopping pipeline before ComfyUI.")
            return 2
    else:
        print("Warning: Missing passes for VisionCritic. Skipping analysis.")

    print("\n=== [4/4] COMFYUI STYLIZATION ===")
    return run_comfy_render(args.index, job_id, args.workflow, args.comfy_url)
