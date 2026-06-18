import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import ffmpeg

H264_OUTPUT_OPTIONS = {
    "vcodec": "libx264",
    "pix_fmt": "yuv420p",
    "crf": 18,
    "preset": "slow",
    "profile:v": "high",
    "movflags": "+faststart",
}


async def assemble_video(input_dir: Path, output_file: Path, fps: int = 24, broadcaster=None, job_id: str = "") -> bool:
    """Assembles an image sequence into an MP4 video using ffmpeg."""
    if not input_dir.exists():
        msg = f"error: input directory {input_dir} not found."
        if broadcaster:
            broadcaster.add_log(job_id, msg + "\n")
        else:
            print(msg, file=sys.stderr)
        return False

    # Compile using ffmpeg-python
    stream = ffmpeg.input(str(input_dir / "*.png"), pattern_type='glob', framerate=fps)
    stream = ffmpeg.output(stream, str(output_file), **H264_OUTPUT_OPTIONS).overwrite_output()
    command = ffmpeg.compile(stream)

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

    stream = ffmpeg.input(str(concat_path), f='concat', safe=0)
    stream = ffmpeg.output(stream, str(output_file), c='copy').overwrite_output()
    command = ffmpeg.compile(stream)

    proc = await asyncio.create_subprocess_exec(
        *command,
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

    stream = ffmpeg.input(str(frames_dir / pattern), pattern_type='glob', framerate=fps)
    stream = ffmpeg.output(stream, str(output_file), **H264_OUTPUT_OPTIONS).overwrite_output()
    args = ffmpeg.compile(stream)

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

        stream = ffmpeg.input(tmp.name, f='concat', safe=0)
        stream = ffmpeg.output(stream, str(output_file), c='copy').overwrite_output()
        args = ffmpeg.compile(stream)

        result = subprocess.run(args, capture_output=True)  # noqa: S603 — list args, no shell injection
        if result.returncode != 0:
            print(result.stderr.decode(errors="replace"), file=sys.stderr)
        return result.returncode == 0
    finally:
        os.unlink(tmp.name)
