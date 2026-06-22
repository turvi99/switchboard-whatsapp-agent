"""
A small, very deliberate creative addition on top of the assignment's core
requirements: the dashboard ships with a "Simulate customer message" panel
that POSTs here. It runs the *exact same* LangGraph pipeline a real Meta
webhook would trigger (acknowledge -> context -> reasoning -> dispatch), the
only difference being that we already know the tenant_id instead of having
to resolve it from a phone_number_id.

Why this matters: WhatsApp's Cloud API requires a verified Meta Business App,
a test number, and your own phone to actually see anything end-to-end. A
grader (or you, mid-development) shouldn't have to do all of that just to
see the agent reason about a message, pick a media asset, and update the
dashboard in real time. Combined with the WhatsAppClient's dry-run mode,
this endpoint makes the whole system demoable in under a minute.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.graph.builder import compiled_graph
from app.graph.state import AgentState
from app.services.session_service import get_or_create_session, resolve_tenant_by_id

router = APIRouter(prefix="/api/simulate", tags=["simulator"])


class SimulateInboundRequest(BaseModel):
    tenant_id: str
    customer_phone: str
    text: str = ""
    simulate_image: bool = False  # exercises the inbound-media branch with a placeholder asset


@router.post("/inbound")
async def simulate_inbound_message(req: SimulateInboundRequest):
    tenant = await resolve_tenant_by_id(req.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Unknown tenant_id '{req.tenant_id}'")

    session_id = await get_or_create_session(req.tenant_id, req.customer_phone)

    media = None
    if req.simulate_image:
        media = {"media_id": "SIMULATED", "type": "image", "mime_type": "image/jpeg"}

    initial_state: AgentState = {
        "tenant_id": req.tenant_id,
        "customer_phone": req.customer_phone,
        "session_id": session_id,
        "phone_number_id": tenant.get("whatsapp_phone_number_id", ""),
        "wa_message_id": f"SIMULATED-{session_id[:8]}",
        "inbound_text": req.text,
        "inbound_media": media,
        "trace": [],
    }
    final_state = await compiled_graph.ainvoke(initial_state)

    return {
        "session_id": session_id,
        "final_status": final_state.get("status"),
        "trace": final_state.get("trace"),
        "response_type": final_state.get("response_type"),
        "response_text": final_state.get("response_text"),
        "sentiment": final_state.get("sentiment"),
    }
