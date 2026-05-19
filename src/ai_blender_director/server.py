import asyncio
import json
import sys
from pathlib import Path
import shutil

import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .index import find_job_record, latest_job_records, append_index_event
from .generator import write_generated_shot
from .jobs import create_render_job
from .commands.render import _build_blender_command
from .commands.post_processing import run_comfy_render
from .commands.video import assemble_video
from .critic import VisionCritic
from .config import settings

# Setup paths
ROOT = Path(__file__).resolve().parents[2]
RENDERS_DIR = ROOT / "renders"
WEB_DIR = ROOT / "web"
INDEX_PATH = RENDERS_DIR / "index.jsonl" # Kept for compat
SHOTS_DIR = ROOT / "generated" / "shots"

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

class LogBroadcaster:
    def __init__(self):
        self.logs: dict[str, list[str]] = {}
        self.clients: dict[str, list[WebSocket]] = {}

    def add_log(self, job_id: str, message: str):
        if job_id not in self.logs:
            self.logs[job_id] = []
        self.logs[job_id].append(message)
        
        if job_id in self.clients:
            for ws in self.clients[job_id]:
                asyncio.create_task(self._safe_send(ws, message))

    async def _safe_send(self, ws: WebSocket, message: str):
        try:
            await ws.send_text(message)
        except:
            pass

    async def connect(self, ws: WebSocket, job_id: str):
        await ws.accept()
        if job_id not in self.clients:
            self.clients[job_id] = []
        self.clients[job_id].append(ws)
        if job_id in self.logs:
            for msg in self.logs[job_id]:
                await self._safe_send(ws, msg)

    def disconnect(self, ws: WebSocket, job_id: str):
        if job_id in self.clients and ws in self.clients[job_id]:
            self.clients[job_id].remove(ws)

broadcaster = LogBroadcaster()


async def run_pipeline_async(job, workflow: str, fps: int):
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
        stderr=asyncio.subprocess.STDOUT
    )
    
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        decoded = line.decode('utf-8')
        broadcaster.add_log(job_id, decoded)
        
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
            
    # 4. Comfy
    broadcaster.add_log(job_id, "\n=== [4/5] COMFYUI STYLIZATION ===\n")
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


@app.post("/api/pipeline")
async def start_pipeline(req: PipelineRequest, background_tasks: BackgroundTasks):
    shot_path = write_generated_shot(req.prompt, SHOTS_DIR, duration_seconds=req.duration, fps=req.fps)
    job = create_render_job(shot_path, RENDERS_DIR / "previews", profile="preview")
    append_index_event(INDEX_PATH, job, "created", status="created")
    
    background_tasks.add_task(run_pipeline_async, job, req.workflow, req.fps)
    return {"job_id": job.job_id}


@app.get("/api/jobs")
async def list_jobs(limit: int = 10):
    records = latest_job_records(INDEX_PATH)
    return records[:limit]


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
