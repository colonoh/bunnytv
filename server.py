"""
Consumer: FastAPI WebSocket server that streams video frames to browser clients.

Start with:
    uv run python main.py
Then open http://localhost:8000/static/index.html
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from producer import QUEUE_SIZE, TARGET_FPS, producer_task

VIDEO_PATH = "BigBuckBunny_640x360.mp4"


class ConnectionManager:
    """Tracks active WebSocket connections and broadcasts to all of them."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.remove(ws)

    async def broadcast(self, message: str) -> None:
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)


manager = ConnectionManager()


async def broadcaster_task(queue: asyncio.Queue) -> None:
    """Pull frames off the queue and broadcast to every connected client."""
    while True:
        payload = await queue.get()
        await manager.broadcast(payload)
        queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
    asyncio.create_task(producer_task(queue, VIDEO_PATH, TARGET_FPS))
    asyncio.create_task(broadcaster_task(queue))
    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        # Keep the connection open; the broadcaster pushes frames to the client.
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
