"""
Producer: reads video frames via ffmpeg and puts them on a queue.

ffmpeg pipes raw BGR frames; we JPEG-encode and queue them.  If the consumer
is slow and the queue is full, frames are dropped to maintain real-time pacing.
"""

import asyncio
import base64
import json
import re
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np

TARGET_FPS: float = 24.0
QUEUE_SIZE: int = 2

_HERE = Path(__file__).parent
FFMPEG = str(_HERE / "ffmpeg.exe")


def probe_video(video_path: str) -> tuple[int, int]:
    """Return (width, height) by parsing ffmpeg's stderr."""
    result = subprocess.run([FFMPEG, "-i", video_path], capture_output=True, text=True)
    match = re.search(r"Video:.*?(\d{3,4})x(\d{3,4})", result.stderr)
    if not match:
        raise RuntimeError(f"Cannot probe dimensions of {video_path}")
    return int(match.group(1)), int(match.group(2))


def _start_ffmpeg(video_path: str) -> subprocess.Popen:
    return subprocess.Popen(
        [
            FFMPEG,
            "-stream_loop", "-1",       # loop the video indefinitely
            "-i", video_path,
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",        # OpenCV-native colour order
            "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )


async def _read_frame(
    proc: subprocess.Popen, width: int, height: int
) -> np.ndarray | None:
    n = width * height * 3
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, proc.stdout.read, n)
    if len(data) < n:
        return None
    return np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))


def encode_frame(frame: np.ndarray, frame_number: int, fps: float) -> str:
    frame = frame.copy()
    cv2.putText(
        frame,
        f"Frame {frame_number}",
        org=(10, 30),
        fontFace=cv2.FONT_HERSHEY_SIMPLEX,
        fontScale=0.8,
        color=(255, 255, 255),
        thickness=2,
        lineType=cv2.LINE_AA,
    )
    _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    b64 = base64.b64encode(jpeg.tobytes()).decode()
    return json.dumps({
        "image": b64,
        "meta": {
            "frame": frame_number,
            "timestamp": round(frame_number / fps, 3),
            "fps": fps,
            "width": frame.shape[1],
            "height": frame.shape[0],
        },
    })


async def producer_task(
    queue: asyncio.Queue, video_path: str, fps: float = TARGET_FPS
) -> None:
    width, height = probe_video(video_path)
    proc = _start_ffmpeg(video_path)
    frame_interval = 1.0 / fps
    frame_number = 0

    try:
        while True:
            t0 = time.monotonic()

            frame = await _read_frame(proc, width, height)
            if frame is None:
                break  # shouldn't happen with -stream_loop -1

            payload = encode_frame(frame, frame_number, fps)
            frame_number += 1

            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass  # consumer is slow — drop this frame

            elapsed = time.monotonic() - t0
            await asyncio.sleep(max(0.0, frame_interval - elapsed))
    finally:
        proc.terminate()
        proc.wait()
