"""
A minimal pub/sub layer so the dashboard updates in real time as the
LangGraph pipeline progresses (typing indicator on, message dispatched,
session status changed) without the frontend having to poll.

Deliberately simple: every connected dashboard client receives every event
and decides locally whether it cares (filtering by tenant_id client-side).
For the scale of this assignment that's the right amount of complexity -
a full pub/sub broker would be over-engineering a prototype.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("app.realtime")


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)
        logger.info("Dashboard client connected (%d active)", len(self.active))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)
        logger.info("Dashboard client disconnected (%d active)", len(self.active))

    async def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        message = json.dumps({"event": event_type, "data": payload}, default=str)
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:  # noqa: BLE001 - connection probably dropped
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
