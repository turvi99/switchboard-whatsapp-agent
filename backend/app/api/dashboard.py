"""
Everything the frontend monitoring dashboard (Task 5) talks to:

  GET  /api/tenants                              tenant switcher
  GET  /api/tenants/{tenant_id}                   tenant detail + media library
  GET  /api/tenants/{tenant_id}/stats             header stat chips
  GET  /api/tenants/{tenant_id}/sessions          live chat monitor list
  GET  /api/tenants/{tenant_id}/sessions/{id}/messages   chat thread
  POST /api/tenants/{tenant_id}/broadcast         broadcast campaign drawer

The live WebSocket feed (`/ws`) is wired up in main.py since it sits outside
the `/api` prefix used everywhere else here.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import messages_col, sessions_col, tenants_col
from app.models import MessageDirection, MessageStatus, SessionStatus
from app.realtime import manager
from app.services.whatsapp_client import WhatsAppClient

logger = logging.getLogger("app.dashboard")

router = APIRouter(prefix="/api", tags=["dashboard"])


# ---------------------------------------------------------------------------
# Tenants
# ---------------------------------------------------------------------------
@router.get("/tenants")
async def list_tenants():
    cursor = tenants_col().find({}, {"_id": 0, "prompt_directions": 0})
    return [doc async for doc in cursor]


@router.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str):
    tenant = await tenants_col().find_one({"tenant_id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.get("/tenants/{tenant_id}/stats")
async def get_tenant_stats(tenant_id: str):
    sessions = sessions_col()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    active = await sessions.count_documents({
        "tenant_id": tenant_id,
        "status": {"$in": [SessionStatus.WAITING_FOR_BOT.value, SessionStatus.AGENT_RESPONDING.value]},
    })
    needs_human = await sessions.count_documents({"tenant_id": tenant_id, "status": SessionStatus.NEEDS_HUMAN.value})
    resolved_today = await sessions.count_documents({
        "tenant_id": tenant_id, "status": SessionStatus.RESOLVED.value, "updated_at": {"$gte": today_start},
    })
    total_sessions = await sessions.count_documents({"tenant_id": tenant_id})
    total_messages = await messages_col().count_documents({"tenant_id": tenant_id})

    return {
        "active_sessions": active,
        "needs_human": needs_human,
        "resolved_today": resolved_today,
        "total_sessions": total_sessions,
        "total_messages": total_messages,
    }


# ---------------------------------------------------------------------------
# Live Chat Monitor
# ---------------------------------------------------------------------------
@router.get("/tenants/{tenant_id}/sessions")
async def list_sessions(tenant_id: str, status: Optional[str] = None):
    query: dict = {"tenant_id": tenant_id}
    if status:
        query["status"] = status
    cursor = sessions_col().find(query, {"_id": 0}).sort("updated_at", -1)
    return [doc async for doc in cursor]


@router.get("/tenants/{tenant_id}/sessions/{session_id}/messages")
async def get_session_messages(tenant_id: str, session_id: str):
    cursor = (
        messages_col()
        .find({"tenant_id": tenant_id, "session_id": session_id}, {"_id": 0})
        .sort("timestamp", 1)
    )
    return [doc async for doc in cursor]


# ---------------------------------------------------------------------------
# Broadcast Campaign Drawer
# ---------------------------------------------------------------------------
class BroadcastRequest(BaseModel):
    cohort: Literal["all", "needs_human", "resolved", "custom"] = "all"
    phone_numbers: list[str] = []          # only used when cohort == "custom"
    template_name: str = "catalog_promo"
    preview_text: str = "New arrivals just dropped! Reply *catalog* to see what's new."


@router.post("/tenants/{tenant_id}/broadcast")
async def broadcast_campaign(tenant_id: str, req: BroadcastRequest):
    tenant = await tenants_col().find_one({"tenant_id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if req.cohort == "custom":
        targets = req.phone_numbers
    else:
        query: dict = {"tenant_id": tenant_id}
        if req.cohort == "needs_human":
            query["status"] = SessionStatus.NEEDS_HUMAN.value
        elif req.cohort == "resolved":
            query["status"] = SessionStatus.RESOLVED.value
        targets = [doc["customer_phone"] async for doc in sessions_col().find(query, {"customer_phone": 1})]

    if not targets:
        return {"sent": 0, "targets": [], "note": "No matching customers for this cohort."}

    client = WhatsAppClient(phone_number_id=tenant.get("whatsapp_phone_number_id"))
    sent = 0
    sent_to: list[str] = []
    for phone in targets:
        try:
            await client.send_template(phone, req.template_name)
        except Exception:  # noqa: BLE001 - one bad number shouldn't kill the whole campaign
            logger.exception("Broadcast send failed for %s", phone)
            continue

        session_doc = await sessions_col().find_one({"tenant_id": tenant_id, "customer_phone": phone})
        if not session_doc:
            continue
        await messages_col().insert_one({
            "message_id": uuid.uuid4().hex,
            "wa_message_id": None,
            "tenant_id": tenant_id,
            "session_id": session_doc["session_id"],
            "customer_phone": phone,
            "direction": MessageDirection.OUTBOUND.value,
            "sender": "broadcast",
            "content_type": "text",
            "text": f"[Broadcast: {req.template_name}] {req.preview_text}",
            "status": MessageStatus.SENT.value,
            "timestamp": datetime.now(timezone.utc),
        })
        sent += 1
        sent_to.append(phone)

    await manager.broadcast("broadcast_sent", {"tenant_id": tenant_id, "sent": sent, "targets": sent_to})
    return {"sent": sent, "targets": sent_to}
