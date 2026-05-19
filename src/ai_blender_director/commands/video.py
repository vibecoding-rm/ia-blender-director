import asyncio
import sys
from pathlib import Path

async def assemble_video(input_dir: Path, output_file: Path, fps: int = 24, broadcaster=None, job_id: str = "") -> bool:
    """Assembles an image sequence into an MP4 video using ffmpeg."""
    if not input_dir.exists():
        msg = f"error: input directory {input_dir} not found."
        if broadcaster:
            broadcaster.add_log(job_id, msg + "\n")
        else:
            print(msg, file=sys.stderr)
        return False
        
    # We assume images are named somewhat sequentially, e.g., output_0001.png
    # But ComfyUI output names might vary. A robust way is glob pattern.
    
    command = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-framerate", str(fps),
        "-pattern_type", "glob",
        "-i", f"{input_dir}/*.png",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output_file)
    ]
    
    msg = f"Running: {' '.join(command)}\n"
    if broadcaster:
        broadcaster.add_log(job_id, msg)
    else:
        print(msg)
        
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        decoded = line.decode('utf-8', errors='replace')
        if broadcaster:
            broadcaster.add_log(job_id, decoded)
        else:
            print(decoded, end="")
            
    await process.wait()
    
    if process.returncode == 0:
        if broadcaster:
            broadcaster.add_log(job_id, f"Video assembled successfully: {output_file.name}\n")
        return True
    else:
        if broadcaster:
            broadcaster.add_log(job_id, f"FFmpeg failed with code {process.returncode}\n")
        return False
