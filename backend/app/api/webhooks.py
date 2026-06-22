"""
Task 4: the async webhook handler.

GET  /api/webhooks/whatsapp  - Meta's one-time verification challenge.
POST /api/webhooks/whatsapp  - inbound message delivery.

The critical requirement here is speed: Meta expects a 200 OK within a few
seconds or it will retry delivery (causing duplicate messages). We satisfy
that by doing only cheap, synchronous JSON parsing on the request path and
deferring every database call and the entire LangGraph run to a
`BackgroundTasks` job - Starlette/FastAPI flushes the HTTP response to Meta
*before* running background tasks, so the webhook returns near-instantly
regardless of how long the LLM takes to think.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, Request, Response

from app.config import get_settings
from app.graph.builder import compiled_graph
from app.graph.state import AgentState
from app.services.security import verify_meta_signature
from app.services.session_service import get_or_create_session, resolve_tenant_by_phone_number_id

logger = logging.getLogger("app.webhooks")

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# ---------------------------------------------------------------------------
# GET - Meta webhook verification handshake
# ---------------------------------------------------------------------------
@router.get("/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
):
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        logger.info("Webhook verification succeeded")
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


# ---------------------------------------------------------------------------
# Payload parsing
# ---------------------------------------------------------------------------
def _extract_inbound_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Flattens Meta's nested entry[].changes[].value structure into a list
    of plain dicts, one per inbound customer message. Non-message changes
    (e.g. delivery/read status callbacks for our own outbound messages) are
    ignored here."""
    events: list[dict[str, Any]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id", "")
            for msg in value.get("messages", []):
                event: dict[str, Any] = {
                    "phone_number_id": phone_number_id,
                    "customer_phone": msg.get("from"),
                    "wa_message_id": msg.get("id"),
                    "msg_type": msg.get("type"),
                    "text": None,
                    "media": None,
                }
                if msg.get("type") == "text":
                    event["text"] = msg.get("text", {}).get("body", "")
                elif msg.get("type") in ("image", "document", "audio", "video", "sticker"):
                    media_block = msg.get(msg["type"], {})
                    event["media"] = {
                        "media_id": media_block.get("id"),
                        "type": msg["type"],
                        "mime_type": media_block.get("mime_type", ""),
                    }
                    event["text"] = media_block.get("caption", "")
                else:
                    event["text"] = f"[unsupported message type: {msg.get('type')}]"
                events.append(event)
    return events


# ---------------------------------------------------------------------------
# Background processing
# ---------------------------------------------------------------------------
async def process_inbound_event(event: dict[str, Any]) -> None:
    """Runs entirely off the request/response path: resolves the tenant,
    gets/creates the chat session, then drives the LangGraph pipeline."""
    try:
        tenant = await resolve_tenant_by_phone_number_id(event["phone_number_id"])
        if not tenant:
            logger.warning("No tenant configured for phone_number_id=%s - dropping message",
                            event["phone_number_id"])
            return

        session_id = await get_or_create_session(tenant["tenant_id"], event["customer_phone"])

        initial_state: AgentState = {
            "tenant_id": tenant["tenant_id"],
            "customer_phone": event["customer_phone"],
            "session_id": session_id,
            "phone_number_id": event["phone_number_id"],
            "wa_message_id": event["wa_message_id"],
            "inbound_text": event.get("text") or "",
            "inbound_media": event.get("media"),
            "trace": [],
        }
        await compiled_graph.ainvoke(initial_state)
    except Exception:  # noqa: BLE001 - background task, must never raise into the void silently
        logger.exception("LangGraph pipeline failed for event %s", event.get("wa_message_id"))


# ---------------------------------------------------------------------------
# POST - inbound message delivery
# ---------------------------------------------------------------------------
@router.post("/whatsapp")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks,
                           x_hub_signature_256: str | None = Header(default=None)):
    raw_body = await request.body()

    if not verify_meta_signature(raw_body, x_hub_signature_256):
        # Still return 200 so Meta doesn't hammer retries on a payload we'll
        # never accept, but never schedule processing for unverified bodies.
        logger.warning("Rejected webhook payload with invalid X-Hub-Signature-256")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = json.loads(raw_body or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Malformed JSON")

    events = _extract_inbound_events(payload)
    for event in events:
        background_tasks.add_task(process_inbound_event, event)

    # Returned immediately - background_tasks run only after this response
    # has been sent, satisfying the "respond within 3 seconds" requirement.
    return {"status": "received", "queued_events": len(events)}
