from fastapi import WebSocket
from typing import Dict, List
import json
import asyncio


class ConnectionManager:
    def __init__(self):
        self.channels: Dict[str, List[WebSocket]] = {
            "leads": [],
            "dialogs": [],
            "pipeline": [],
        }

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        self.channels.setdefault(channel, []).append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        conns = self.channels.get(channel, [])
        if websocket in conns:
            conns.remove(websocket)

    async def broadcast(self, channel: str, data: dict):
        dead = []
        for ws in self.channels.get(channel, []):
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, channel)


manager = ConnectionManager()
