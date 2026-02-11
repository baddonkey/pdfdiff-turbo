import asyncio
from typing import Dict, Set

from fastapi import WebSocket


class ReportWebSocketManager:
    def __init__(self) -> None:
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.setdefault(user_id, set()).add(websocket)

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id].discard(websocket)
                if not self._connections[user_id]:
                    self._connections.pop(user_id, None)

    async def broadcast_to_user(self, user_id: str, payload: dict) -> None:
        async with self._lock:
            sockets = list(self._connections.get(user_id, set()))
        for websocket in sockets:
            try:
                await websocket.send_json(payload)
            except Exception:
                await self.disconnect(user_id, websocket)


report_ws_manager = ReportWebSocketManager()
