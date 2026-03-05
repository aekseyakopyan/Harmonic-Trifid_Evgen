from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.ws_manager import manager

router = APIRouter()


@router.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    if channel not in ("leads", "dialogs", "pipeline"):
        await websocket.close(code=4004)
        return
    await manager.connect(websocket, channel)
    try:
        while True:
            await websocket.receive_text()  # keep alive / ping handling
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
