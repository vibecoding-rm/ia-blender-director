import asyncio
import json
import os
import shutil
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .index import find_job_record, latest_job_records, append_index_event
from .generator import write_generated_shot
from .jobs import create_render_job, RenderJob
from .commands.render import _build_blender_command
from .commands.post_processing import run_comfy_render
from .commands.video import assemble_video, concat_videos_async
from .critic import VisionCritic
from .config import settings

ROOT = Path(__file__).resolve().parents[2]
RENDERS_DIR = ROOT / "renders"
PLANS_DIR = RENDERS_DIR / "plans"
WEB_DIR = ROOT / "web"
INDEX_PATH = RENDERS_DIR / "index.jsonl"
SHOTS_DIR = ROOT / "generated" / "shots"

_PLANS_STATE_FILE = RENDERS_DIR / "plans" / "state.json"

plans_state: dict[str, dict] = {}
plans_state_lock = asyncio.Lock()


def _load_plans_state() -> None:
    if _PLANS_STATE_FILE.exists():
        try:
            data = json.loads(_PLANS_STATE_FILE.read_text(encoding="utf-8"))
            plans_state.update(data)
        except Exception:
            pass


async def _save_plans_state() -> None:
    async with plans_state_lock:
        _PLANS_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(
            _PLANS_STATE_FILE.write_text,
            json.dumps(plans_state, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


_load_plans_state()

app = FastAPI(title="AI Blender Director API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RENDERS_DIR.mkdir(exist_ok=True)
app.mount("/renders", StaticFiles(directory=str(RENDERS_DIR)), name="renders")
app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")


class PipelineRequest(BaseModel):
    prompt: str
    duration: int = 4
    fps: int = 24
    workflow: str = "stylization_v1"


class DirectorPlanRequest(BaseModel):
    prompt: str
    n_shots: int = 3
    duration: int = 4
    fps: int = 24


class DirectorRenderRequest(BaseModel):
    prompt: str
    n_shots: int = 3
    duration: int = 4
    fps: int = 24
    workflow: str = "stylization_v1"
    shots: list[dict] | None = None
    hook_title: str | None = None
    narration_text: str | None = None


class LogBroadcaster:
    def __init__(self):
        self.logs: dict[str, list[str]] = {}
        self.clients: dict[str, list[WebSocket]] = {}
        self._parents: dict[str, str] = {}

    def set_parent(self, child_id: str, parent_id: str) -> None:
        self._parents[child_id] = parent_id

    def clear_parent(self, child_id: str) -> None:
        self._parents.pop(child_id, None)

    def add_log(self, job_id: str, message: str):
        self._do_add(job_id, message)
        parent = self._parents.get(job_id)
        if parent:
            self._do_add(parent, message)

    def _do_add(self, job_id: str, message: str):
        self.logs.setdefault(job_id, []).append(message)
        for ws in self.clients.get(job_id, []):
            asyncio.create_task(self._safe_send(ws, message))

    async def _safe_send(self, ws: WebSocket, message: str):
        try:
            await ws.send_text(message)
        except Exception:
            pass

    async def connect(self, ws: WebSocket, job_id: str):
        await ws.accept()
        self.clients.setdefault(job_id, []).append(ws)
        for msg in self.logs.get(job_id, []):
            await self._safe_send(ws, msg)

    def disconnect(self, ws: WebSocket, job_id: str):
        if job_id in self.clients and ws in self.clients[job_id]:
            self.clients[job_id].remove(ws)

    def schedule_cleanup(self, job_id: str, delay: int = 300) -> None:
        async def _cleanup():
            await asyncio.sleep(delay)
            self.logs.pop(job_id, None)
            self.clients.pop(job_id, None)
            self._parents.pop(job_id, None)
        asyncio.create_task(_cleanup())

broadcaster = LogBroadcaster()


def _blender_env() -> dict[str, str]:
    """Strip the active venv from PATH so Blender's Python finds system numpy."""
    env = os.environ.copy()
    venv_bin = os.environ.get("VIRTUAL_ENV", "")
    if venv_bin:
        venv_bin_dir = os.path.join(venv_bin, "bin")
        parts = env.get("PATH", "").split(os.pathsep)
        env["PATH"] = os.pathsep.join(p for p in parts if p != venv_bin_dir)
    return env


def _comfy_reachable() -> bool:
    try:
        urllib.request.urlopen(settings.comfy_url, timeout=3)
        return True
    except Exception:
        return False


async def run_pipeline_async(job: RenderJob, workflow: str, fps: int):
    try:
        await _run_pipeline_inner(job, workflow, fps)
    except Exception as exc:
        broadcaster.add_log(job.job_id, f"Pipeline error: {exc}\n")
        append_index_event(INDEX_PATH, job, "finished", status="failed")
    finally:
        broadcaster.schedule_cleanup(job.job_id)


async def _run_pipeline_inner(job: RenderJob, workflow: str, fps: int):
    job_id = job.job_id
    broadcaster.add_log(job_id, f"=== [1/5] Starting Pipeline for {job_id} ===\n")

    # 2. Render
    blender = shutil.which(settings.blender_executable) or settings.blender_executable
    command = _build_blender_command(job.job_shot, job.job_dir, profile=job.profile, blender=blender)
    broadcaster.add_log(job_id, f"Running: {' '.join(command)}\n")
    append_index_event(INDEX_PATH, job, "started", status="running")

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=_blender_env(),
    )
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        broadcaster.add_log(job_id, line.decode("utf-8"))
    await process.wait()

    if process.returncode != 0:
        broadcaster.add_log(job_id, f"Blender render failed with code {process.returncode}\n")
        append_index_event(INDEX_PATH, job, "finished", status="failed", returncode=process.returncode)
        return

    # 3. Critic
    broadcaster.add_log(job_id, "\n=== [3/5] VISION CRITIC ANALYSIS ===\n")
    manifest_path = job.job_dir / "manifest.json"
    if not manifest_path.exists():
        broadcaster.add_log(job_id, "No manifest found after render.\n")
        append_index_event(INDEX_PATH, job, "finished", status="failed")
        return

    with manifest_path.open() as f:
        manifest = json.load(f)

    beauty_pass = manifest.get("passes", {}).get("beauty")
    mask_pass = manifest.get("passes", {}).get("subject_mask")

    if beauty_pass and mask_pass:
        critic = VisionCritic(job.job_dir / beauty_pass, job.job_dir / mask_pass)
        feedbacks = critic.analyze()
        if feedbacks:
            broadcaster.add_log(job_id, f"Found {len(feedbacks)} issues:\n")
            has_crit = False
            for fb in feedbacks:
                broadcaster.add_log(job_id, f"[{fb.level}] {fb.category}: {fb.message}\n")
                if fb.level == "WARNING":
                    has_crit = True
            if has_crit:
                broadcaster.add_log(job_id, "Stopping pipeline due to WARNING.\n")
                append_index_event(INDEX_PATH, job, "finished", status="failed")
                return
        else:
            broadcaster.add_log(job_id, "VisionCritic: OK.\n")

    # 4. Comfy (optional — skipped gracefully if ComfyUI is unreachable)
    broadcaster.add_log(job_id, "\n=== [4/5] COMFYUI STYLIZATION ===\n")
    comfy_ok = await asyncio.to_thread(_comfy_reachable)
    if not comfy_ok:
        broadcaster.add_log(job_id, "ComfyUI not reachable — skipping stylization, assembling from beauty pass.\n")
        beauty_dir = job.job_dir / "passes"
        comfy_out = job.job_dir / "comfy_output"
        comfy_out.mkdir(exist_ok=True)
        for img in sorted(beauty_dir.glob("beauty_frame_*.png")):
            shutil.copy(img, comfy_out / img.name)
    else:
        broadcaster.add_log(job_id, "Uploading to ComfyUI and waiting for images...\n")
        comfy_res = await asyncio.to_thread(run_comfy_render, INDEX_PATH, job_id, workflow, settings.comfy_url)
        if comfy_res != 0:
            broadcaster.add_log(job_id, "ComfyUI processing failed.\n")
            append_index_event(INDEX_PATH, job, "finished", status="failed", returncode=comfy_res)
            return
        broadcaster.add_log(job_id, "ComfyUI processing finished.\n")

    # 5. Video Assembly
    broadcaster.add_log(job_id, "\n=== [5/5] VIDEO ASSEMBLY ===\n")
    output_dir = job.job_dir / "comfy_output"
    final_video = output_dir / "final_render.mp4"
    video_res = await assemble_video(output_dir, final_video, fps=fps, broadcaster=broadcaster, job_id=job_id)

    if video_res:
        append_index_event(INDEX_PATH, job, "finished", status="completed", returncode=0)
    else:
        append_index_event(INDEX_PATH, job, "finished", status="failed")


async def run_plan_pipeline_async(plan_id: str, jobs: list[RenderJob], workflow: str, fps: int, hook_title: str | None = None, narration_text: str | None = None) -> None:
    try:
        broadcaster.add_log(plan_id, f"=== DIRECTOR PLAN — {len(jobs)} shot(s) ===\n")

        for i, job in enumerate(jobs, 1):
            broadcaster.add_log(plan_id, f"\n--- Shot {i}/{len(jobs)}: {job.job_id} ---\n")
            broadcaster.set_parent(job.job_id, plan_id)
            try:
                await _run_pipeline_inner(job, workflow, fps)
            except Exception as exc:
                broadcaster.add_log(plan_id, f"Shot {i} error: {exc}\n")
            finally:
                broadcaster.clear_parent(job.job_id)

        shot_videos = [
            job.job_dir / "comfy_output" / "final_render.mp4"
            for job in jobs
            if (job.job_dir / "comfy_output" / "final_render.mp4").exists()
        ]

        broadcaster.add_log(plan_id, f"\n=== POSTPRODUCTION (Hook + TTS + Subtitles + Concat) ===\n")

        if shot_videos:
            plan_dir = PLANS_DIR / plan_id
            plan_dir.mkdir(parents=True, exist_ok=True)
            final_video = plan_dir / "final.mp4"

            from .postproduction import produce_short
            from .io import load_shot_spec
            
            shot_durations = []
            res_tuple = (1280, 720)
            
            for job in jobs:
                if (job.job_dir / "comfy_output" / "final_render.mp4").exists():
                    spec = load_shot_spec(job.job_shot)
                    shot_durations.append(spec.duration_seconds)
                    res_tuple = (spec.resolution.width, spec.resolution.height)

            # Use the pre-synthesized audio from Intelligent Pacing if it exists
            pre_synth_wav = PLANS_DIR / plan_id / "narration.wav"
            voice_path = pre_synth_wav if pre_synth_wav.exists() else None

            result_path = await asyncio.to_thread(
                produce_short,
                shot_videos=shot_videos,
                shot_durations=shot_durations,
                output_video=final_video,
                resolution=res_tuple,
                fps=fps,
                hook_title=hook_title,
                narration_text=req.narration_text if not voice_path else None,  # Skip internal synthesis if we did it
                voice=voice_path,
                subtitles=True,
                sfx=True,
            )

            if result_path and result_path.exists():
                plans_state[plan_id].update({
                    "status": "completed",
                    "video": f"renders/plans/{plan_id}/final.mp4",
                })
                broadcaster.add_log(plan_id, f"Final video: {final_video.name}\n")
            else:
                plans_state[plan_id]["status"] = "failed"
        else:
            plans_state[plan_id]["status"] = "completed"

        broadcaster.add_log(plan_id, "=== PLAN COMPLETE ===\n")

    except Exception as exc:
        broadcaster.add_log(plan_id, f"Plan pipeline error: {exc}\n")
        plans_state[plan_id]["status"] = "failed"
    finally:
        await _save_plans_state()
        broadcaster.schedule_cleanup(plan_id)


@app.post("/api/director/plan")
async def director_plan(req: DirectorPlanRequest):
    from .planner import plan_scene

    scene_data = await asyncio.to_thread(
        plan_scene, req.prompt, req.n_shots,
        duration_seconds=req.duration, fps=req.fps,
    )
    return scene_data


@app.post("/api/director/render")
async def director_render(req: DirectorRenderRequest, background_tasks: BackgroundTasks):
    from .planner import write_shot_plan
    from .tts import synthesize, media_duration

    plan_id = f"plan_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    
    # INTELLIGENT PACING: Calculate voiceover duration to assign perfect shot length
    duration = req.duration
    narration_wav = PLANS_DIR / plan_id / "narration.wav"
    if req.narration_text:
        PLANS_DIR.mkdir(parents=True, exist_ok=True)
        ok = await asyncio.to_thread(synthesize, req.narration_text, narration_wav)
        if ok:
            narration_dur = await asyncio.to_thread(media_duration, narration_wav)
            if narration_dur:
                total_video_time = narration_dur + 0.5  # Add a tiny padding
                duration = max(1, int(total_video_time / req.n_shots) + 1)
                logger.info(f"Intelligent Pacing: Audio is {narration_dur}s. Adjusting {req.n_shots} shots to {duration}s each.")

    paths = await asyncio.to_thread(
        write_shot_plan, req.prompt, SHOTS_DIR,
        n_shots=req.n_shots, duration_seconds=duration, fps=req.fps,
        precomputed_shots=req.shots
    )

    jobs = []
    for p in paths:
        job = create_render_job(p, RENDERS_DIR / "previews", profile="preview")
        append_index_event(INDEX_PATH, job, "created", status="created")
        jobs.append(job)

    async with plans_state_lock:
        plans_state[plan_id] = {
            "plan_id": plan_id,
            "status": "running",
            "job_ids": [j.job_id for j in jobs],
            "video": None,
        }
        PLANS_DIR.mkdir(parents=True, exist_ok=True)
    
    await _save_plans_state()

    background_tasks.add_task(run_plan_pipeline_async, plan_id, jobs, req.workflow, req.fps, req.hook_title, req.narration_text)
    return {"plan_id": plan_id, "job_ids": [j.job_id for j in jobs], "n_shots": len(jobs)}


@app.get("/api/plans/{plan_id}")
async def get_plan_status(plan_id: str):
    state = plans_state.get(plan_id)
    if not state:
        raise HTTPException(status_code=404, detail="Plan not found")
    return state


@app.post("/api/pipeline")
async def start_pipeline(req: PipelineRequest, background_tasks: BackgroundTasks):
    shot_path = await asyncio.to_thread(
        write_generated_shot, req.prompt, SHOTS_DIR, duration_seconds=req.duration, fps=req.fps
    )
    job = create_render_job(shot_path, RENDERS_DIR / "previews", profile="preview")
    append_index_event(INDEX_PATH, job, "created", status="created")
    background_tasks.add_task(run_pipeline_async, job, req.workflow, req.fps)
    return {"job_id": job.job_id}


@app.get("/api/jobs")
async def list_jobs(limit: int = 10):
    records = latest_job_records(INDEX_PATH)
    result = records[:limit]
    for rec in result:
        job_dir = Path(rec.get("job_dir", ""))
        rec["has_video"] = (job_dir / "comfy_output" / "final_render.mp4").exists()
    return result


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    record = find_job_record(INDEX_PATH, job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")

    job_dir = Path(record["job_dir"])
    manifest_path = job_dir / "manifest.json"
    result = {"record": record, "manifest": None, "comfy_outputs": [], "video": None}

    if manifest_path.exists():
        with manifest_path.open() as f:
            result["manifest"] = json.load(f)

    comfy_dir = job_dir / "comfy_output"
    if comfy_dir.exists():
        outputs = [f.name for f in comfy_dir.iterdir() if f.is_file() and f.suffix in (".png", ".jpg")]
        result["comfy_outputs"] = sorted(outputs)
        video_path = comfy_dir / "final_render.mp4"
        if video_path.exists():
            result["video"] = "final_render.mp4"

    return result


@app.websocket("/ws/logs/{job_id}")
async def websocket_logs(websocket: WebSocket, job_id: str):
    await broadcaster.connect(websocket, job_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket, job_id)


@app.get("/")
async def root():
    from fastapi.responses import FileResponse
    index_file = WEB_DIR / "index.html"
    if not index_file.exists():
        return {"error": "Web frontend not found"}
    return FileResponse(index_file)


def run_server():
    uvicorn.run(app, host=settings.server_host, port=settings.server_port)


if __name__ == "__main__":
    run_server()
