"""
Producer: reads video frames at a configurable rate and puts them on a queue.

If the consumer is slow and the queue is full, frames are dropped to maintain
real-time playback — the producer never blocks waiting for consumers.
"""

import asyncio
import base64
import json
import time

import cv2

TARGET_FPS: float = 24.0
QUEUE_SIZE: int = 2  # small bound — excess frames are dropped


def encode_frame(frame, frame_number: int, fps: float) -> str:
    """Encode a BGR frame as a JPEG and wrap it in a JSON payload."""
    _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    b64 = base64.b64encode(jpeg.tobytes()).decode()
    payload = {
        "image": b64,
        "meta": {
            "frame": frame_number,
            "timestamp": round(frame_number / fps, 3),
            "fps": fps,
            "width": frame.shape[1],
            "height": frame.shape[0],
        },
    }
    return json.dumps(payload)


async def producer_task(queue: asyncio.Queue, video_path: str, fps: float = TARGET_FPS) -> None:
    """
    Continuously read frames from *video_path* and push them onto *queue*.

    The video loops when it reaches the end.  Frames are dropped (not queued)
    when the queue is full so that real-time pacing is preserved.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    frame_interval = 1.0 / fps
    frame_number = 0

    try:
        while True:
            t0 = time.monotonic()

            ret, frame = cap.read()
            if not ret:
                # Loop: rewind to the beginning
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_number = 0
                continue

            payload = encode_frame(frame, frame_number, fps)
            frame_number += 1

            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass  # consumer is slow — drop this frame

            elapsed = time.monotonic() - t0
            await asyncio.sleep(max(0.0, frame_interval - elapsed))
    finally:
        cap.release()
