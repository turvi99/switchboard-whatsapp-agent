"""
Application entrypoint.

Run locally with:   uvicorn app.main:app --reload --port 8000
Run in production:  uvicorn app.main:app --host 0.0.0.0 --port $PORT
(see the root Dockerfile, which does exactly that after building the React
dashboard into ./static)
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.dashboard import router as dashboard_router
from app.api.simulator import router as simulator_router
from app.api.webhooks import router as webhooks_router
from app.config import get_settings
from app.database import close_mongo_connection, connect_to_mongo
from app.realtime import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    logger.info("%s started in '%s' mode", get_settings().app_name, get_settings().environment)
    yield
    await close_mongo_connection()


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.cors_origins == "*" else settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks_router)
app.include_router(dashboard_router)
app.include_router(simulator_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "environment": settings.environment}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Powers the dashboard's live updates: pipeline progress, new
    messages, broadcast results. The frontend just listens and refetches
    the relevant slice of data on each event."""
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect inbound traffic from the client, but reading
            # keeps the connection alive and lets us detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Serve the built React dashboard as static files in production.
#
# Locally you'll typically run `npm run dev` (Vite) separately for hot
# reload, so this block is a no-op until `frontend/dist` actually exists -
# which only happens after the Docker build step (see root Dockerfile) runs
# `npm run build`.
# ---------------------------------------------------------------------------
_static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="dashboard")
    logger.info("Serving built dashboard from %s", _static_dir)
else:
    logger.info("No built frontend found at %s - run the Vite dev server separately for local UI work", _static_dir)
