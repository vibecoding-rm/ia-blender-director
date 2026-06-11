import asyncio
import os
import subprocess
import sys
import tempfile
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

    command = [
        "ffmpeg",
        "-y",
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


async def concat_videos_async(
    video_files: list[Path],
    output_file: Path,
    broadcaster=None,
    job_id: str = "",
) -> bool:
    """Concatenate MP4 files via FFmpeg concat demuxer (async)."""
    if not video_files:
        return False

    concat_path = output_file.parent / "concat_list.txt"
    concat_path.write_text("\n".join(f"file '{v.resolve()}'" for v in video_files))

    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_path),
        "-c", "copy",
        str(output_file),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        decoded = line.decode("utf-8", errors="replace")
        if broadcaster:
            broadcaster.add_log(job_id, decoded)
    await proc.wait()

    if proc.returncode == 0:
        if broadcaster:
            broadcaster.add_log(job_id, f"Concatenated {len(video_files)} video(s) -> {output_file.name}\n")
        return True
    else:
        if broadcaster:
            broadcaster.add_log(job_id, f"FFmpeg concat failed (code {proc.returncode})\n")
        return False


def assemble_frames_sync(
    frames_dir: Path,
    output_file: Path,
    fps: int = 24,
    pattern: str = "*.png",
) -> bool:
    """Assemble PNG frames from a directory into an MP4 (synchronous, for CLI)."""
    if not sorted(frames_dir.glob(pattern)):
        print(f"No frames matching '{pattern}' in {frames_dir}", file=sys.stderr)
        return False

    args = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-pattern_type", "glob",
        "-i", str(frames_dir / pattern),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output_file),
    ]
    result = subprocess.run(args, capture_output=True)  # noqa: S603 — list args, no shell injection
    if result.returncode != 0:
        print(result.stderr.decode(errors="replace"), file=sys.stderr)
    return result.returncode == 0


def concat_videos_sync(video_files: list[Path], output_file: Path) -> bool:
    """Concatenate MP4 files via FFmpeg concat demuxer (synchronous, for CLI)."""
    if not video_files:
        return False

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    try:
        for v in video_files:
            tmp.write(f"file '{v.resolve()}'\n")
        tmp.close()

        args = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", tmp.name,
            "-c", "copy",
            str(output_file),
        ]
        result = subprocess.run(args, capture_output=True)  # noqa: S603 — list args, no shell injection
        if result.returncode != 0:
            print(result.stderr.decode(errors="replace"), file=sys.stderr)
        return result.returncode == 0
    finally:
        os.unlink(tmp.name)
