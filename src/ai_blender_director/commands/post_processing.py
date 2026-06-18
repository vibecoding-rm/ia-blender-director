import argparse
import json
import sys
import time
from pathlib import Path

from ..index import find_job_record
from ..critic import VisionCritic, CriticConfig
from ..comfy.client import ComfyClient
from ..config import settings

ROOT = Path(__file__).resolve().parents[3]

def register_parsers(subparsers: argparse._SubParsersAction) -> None:
    comfy_parser = subparsers.add_parser("comfy-render", help="Stylize a rendered job using ComfyUI.")
    comfy_parser.add_argument("job_id")
    comfy_parser.add_argument("--workflow", default="stylization_v1")
    comfy_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"), help=argparse.SUPPRESS)

    critic_parser = subparsers.add_parser("critic", help="Analyze a rendered job using VisionCritic rules.")
    critic_parser.add_argument("job_id")
    critic_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"), help=argparse.SUPPRESS)

def handle_comfy_render(args: argparse.Namespace) -> int:
    return run_comfy_render(args.index, args.job_id, args.workflow)

def handle_critic(args: argparse.Namespace) -> int:
    return run_critic(args.index, args.job_id)

def run_comfy_render(index_path: Path, job_id: str, workflow_name: str, comfy_url: str | None = None) -> int:
    if not comfy_url:
        comfy_url = settings.comfy_url
        
    record = find_job_record(index_path, job_id)
    if record is None:
        print(f"error: job not found: {job_id}", file=sys.stderr)
        return 2

    job_dir = Path(record["job_dir"])
    manifest = _read_json_if_exists(job_dir / "manifest.json")
    if not manifest:
        print(f"error: manifest.json not found in {job_dir}", file=sys.stderr)
        return 2

    passes = manifest.get("passes", {})
    beauty_pass = passes.get("beauty")
    if not beauty_pass:
        print(f"error: beauty pass not found in manifest for job {job_id}", file=sys.stderr)
        return 2

    beauty_path = Path(beauty_pass)
    if not beauty_path.exists():
        print(f"error: beauty pass file not found at {beauty_path}", file=sys.stderr)
        return 2

    workflow_path = ROOT / "workflows" / "comfy" / workflow_name / "workflow_api.json"
    workflow = _read_json_if_exists(workflow_path)
    if not workflow:
        print(f"error: workflow not found at {workflow_path}", file=sys.stderr)
        return 2

    shot_path = job_dir / "shot.json"
    shot_spec = _read_json_if_exists(shot_path) or {}
    
    positive_prompt = "masterpiece, highly detailed, photorealistic, cinematic lighting"
    if shot_spec:
        style = shot_spec.get("style", "")
        lighting = shot_spec.get("lighting", "")
        subject = shot_spec.get("subject", "")
        action = shot_spec.get("action", "")
        scene = shot_spec.get("scene", "")
        weather = shot_spec.get("weather", "") or ""
        parts = [p for p in [style, scene, subject, action, lighting, weather] if p]
        if parts:
            positive_prompt = f"masterpiece, highly detailed, photorealistic, {', '.join(parts)}"

    depth_pass = passes.get("depth_proxy")
    depth_path = Path(depth_pass) if depth_pass else None

    print(f"uploading {beauty_path.name} to ComfyUI at {comfy_url}...")
    client = ComfyClient(comfy_url)
    subfolder = f"ai_director_{job_id}"

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            beauty_res = client.upload_image(beauty_path, subfolder=subfolder)
            beauty_remote = f"{beauty_res.get('subfolder', subfolder)}/{beauty_res.get('name')}"

            depth_remote = None
            if depth_path and depth_path.exists():
                depth_res = client.upload_image(depth_path, subfolder=subfolder)
                depth_remote = f"{depth_res.get('subfolder', subfolder)}/{depth_res.get('name')}"

            for node_data in workflow.values():
                class_type = node_data.get("class_type")
                title = node_data.get("_meta", {}).get("title", "")
                
                if class_type == "LoadImage":
                    if "Depth" in title and depth_remote:
                        node_data["inputs"]["image"] = depth_remote
                    else:
                        node_data["inputs"]["image"] = beauty_remote
                elif class_type == "CLIPTextEncode":
                    if "(Positive)" in title:
                        node_data["inputs"]["text"] = positive_prompt

            print("queuing prompt...")
            prompt_res = client.queue_prompt(workflow)
            prompt_id = prompt_res.get("prompt_id")
            print(f"prompt queued, id: {prompt_id}. waiting for completion...")

            output_dir = job_dir / "comfy_output"
            downloaded = client.process_and_download(prompt_id, output_dir)
            print(f"downloaded {len(downloaded)} images to {output_dir}")
            for p in downloaded:
                print(f"  {p}")
            return 0

        except Exception as exc:
            print(f"attempt {attempt}/{max_retries} failed interacting with ComfyUI: {exc}", file=sys.stderr)
            if attempt < max_retries:
                time.sleep(5)
            else:
                return 2


def run_critic(index_path: Path, job_id: str) -> int:
    record = find_job_record(index_path, job_id)
    if record is None:
        print(f"error: job not found: {job_id}", file=sys.stderr)
        return 2

    job_dir = Path(record["job_dir"])
    manifest = _read_json_if_exists(job_dir / "manifest.json")
    if not manifest:
        print(f"error: manifest.json not found in {job_dir}", file=sys.stderr)
        return 2

    passes = manifest.get("passes", {})
    beauty_pass = passes.get("beauty")
    mask_pass = passes.get("subject_mask")
    
    if not beauty_pass or not mask_pass:
        print(f"error: beauty or subject_mask pass not found in manifest for job {job_id}", file=sys.stderr)
        return 2

    beauty_path = Path(beauty_pass)
    mask_path = Path(mask_pass)

    if not beauty_path.exists() or not mask_path.exists():
        print("error: missing pass files", file=sys.stderr)
        return 2

    critic = VisionCritic(beauty_path, mask_path)
    feedbacks = critic.analyze()
    
    if not feedbacks:
        print("VisionCritic: OK. No issues detected.")
        return 0
        
    print(f"VisionCritic found {len(feedbacks)} issues:")
    for fb in feedbacks:
        print(f"[{fb.level}] {fb.category}: {fb.message}")
        
    return 0


def _read_json_if_exists(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)
