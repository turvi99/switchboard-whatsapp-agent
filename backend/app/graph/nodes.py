"""
The four nodes from Task 3 of the brief, plus one bonus node
(`human_handover_node`) for the sentiment-based fallback.

    [Webhook Inbound]
            |
            v
    acknowledge_node            -> read receipt + typing indicator ON, log inbound msg
            |
            v
    context_retriever_node      -> pull tenant rules + last 5 messages
            |
            v
    llm_reasoning_node          -> decide: text reply, or attach media? sentiment?
            |
       (conditional edge)
        /        \\
       v          v
  human_handover  dispatcher_node -> build + send WhatsApp payload, persist, broadcast

Every node returns only the keys of AgentState it actually changed -
LangGraph merges that into the running state for us.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from app.config import get_settings
from app.database import messages_col, sessions_col, tenants_col
from app.graph.state import AgentState
from app.graph.tools import describe_media_library, find_media_asset
from app.models import MessageContentType, MessageDirection, MessageStatus, SessionStatus
from app.realtime import manager
from app.services.llm_client import AgentDecision, describe_inbound_image, get_chat_model
from app.services.whatsapp_client import WhatsAppClient

logger = logging.getLogger("app.graph.nodes")


def _now():
    return datetime.now(timezone.utc)


async def _touch_session(tenant_id: str, session_id: str, **fields) -> None:
    fields["updated_at"] = _now()
    await sessions_col().update_one({"tenant_id": tenant_id, "session_id": session_id}, {"$set": fields})


async def _broadcast_state(state: AgentState, node_name: str) -> None:
    """Push a lightweight snapshot to every connected dashboard client so the
    'Agent Pipeline' strip and chat thread can animate in real time."""
    await manager.broadcast(
        "pipeline_update",
        {
            "tenant_id": state.get("tenant_id"),
            "session_id": state.get("session_id"),
            "customer_phone": state.get("customer_phone"),
            "node": node_name,
            "status": state.get("status"),
            "trace": state.get("trace", []),
        },
    )


# ---------------------------------------------------------------------------
# 1. Acknowledge Node
# ---------------------------------------------------------------------------
async def acknowledge_node(state: AgentState) -> dict:
    """Fires the read receipt + typing indicator immediately, then persists
    the inbound message as PENDING_RESPONSE before any LLM latency occurs -
    this is what keeps the audit log accurate even if the agent crashes
    mid-pipeline."""
    tenant_id = state["tenant_id"]
    session_id = state["session_id"]

    client = WhatsAppClient(phone_number_id=state.get("phone_number_id"))
    if state.get("wa_message_id"):
        # Two separate API calls: (1) mark message read, (2) start typing indicator
        await client.mark_read_and_start_typing(state["wa_message_id"], state["customer_phone"])

    media = state.get("inbound_media")
    await messages_col().insert_one({
        "message_id": uuid.uuid4().hex,
        "wa_message_id": state.get("wa_message_id"),
        "tenant_id": tenant_id,
        "session_id": session_id,
        "customer_phone": state["customer_phone"],
        "direction": MessageDirection.INBOUND.value,
        "sender": "customer",
        "content_type": (media or {}).get("type", MessageContentType.TEXT.value),
        "text": state.get("inbound_text") or (f"[media: {media.get('mime_type')}]" if media else ""),
        "media_url": (media or {}).get("url"),
        "media_mime_type": (media or {}).get("mime_type"),
        "status": MessageStatus.PENDING_RESPONSE.value,
        "timestamp": _now(),
    })

    await _touch_session(tenant_id, session_id, status=SessionStatus.WAITING_FOR_BOT.value,
                          last_message_preview=(state.get("inbound_text") or "[media]")[:120])

    trace = state.get("trace", []) + ["acknowledge"]
    new_state = {**state, "status": SessionStatus.WAITING_FOR_BOT.value, "trace": trace}
    await _broadcast_state(new_state, "acknowledge")
    return {"status": SessionStatus.WAITING_FOR_BOT.value, "trace": trace}


# ---------------------------------------------------------------------------
# 2. Context Retriever Node
# ---------------------------------------------------------------------------
async def context_retriever_node(state: AgentState) -> dict:
    """Pulls the tenant's prompt directions + media catalog and the last 5
    messages of chat history so the reasoning node has everything it needs
    in one shot."""
    tenant_doc = await tenants_col().find_one({"tenant_id": state["tenant_id"]}, {"_id": 0})
    history_cursor = (
        messages_col()
        .find({"tenant_id": state["tenant_id"], "session_id": state["session_id"]}, {"_id": 0})
        .sort("timestamp", -1)
        .limit(5)
    )
    history = [doc async for doc in history_cursor]
    history.reverse()  # chronological order for the prompt

    # Bonus: if the inbound message was an image, resolve the (Bearer-auth
    # gated) media id to bytes and describe it with a vision model, folding
    # the description into both the state and the just-logged message so it
    # shows up in chat history from now on.
    media = state.get("inbound_media")
    if media and media.get("media_id") and not media.get("description"):
        client = WhatsAppClient(phone_number_id=state.get("phone_number_id"))
        try:
            temp_url = await client.fetch_media_url(media["media_id"])
            description = "[customer sent an image]"
            if temp_url:
                media["url"] = temp_url
                image_bytes = await client.download_media_bytes(temp_url)
                description = await describe_inbound_image(image_bytes, media.get("mime_type", "image/jpeg"))
            media["description"] = description
            await messages_col().update_one(
                {"tenant_id": state["tenant_id"], "session_id": state["session_id"], "wa_message_id": state.get("wa_message_id")},
                {"$set": {"text": f"[image] {description}", "media_url": media.get("url")}},
            )
        except Exception as exc:  # noqa: BLE001 - bonus feature, never block the pipeline
            logger.warning("Inbound media resolution failed: %s", exc)
            media["description"] = "[customer sent an image]"

    trace = state.get("trace", []) + ["context_retriever"]
    new_state = {**state, "tenant": tenant_doc or {}, "chat_history": history, "trace": trace}
    await _broadcast_state(new_state, "context_retriever")
    return {"tenant": tenant_doc or {}, "chat_history": history, "inbound_media": media, "trace": trace}


# ---------------------------------------------------------------------------
# 3. LLM Reasoning Node
# ---------------------------------------------------------------------------
def _build_system_prompt(tenant: dict) -> str:
    media_block = describe_media_library(tenant.get("media_library", []))
    return f"""You are the AI sales & support agent for "{tenant.get('name', 'this business')}" \
({tenant.get('industry', 'retail')}), speaking with a customer over WhatsApp.

Brand instructions from the business owner:
{tenant.get('prompt_directions', 'Be helpful, concise and friendly.')}

You have access to this pre-seeded media library. If the customer is asking for a \
catalog, image, invoice, diagram, or any visual/document asset, choose action='send_media' \
and set media_keyword to the single best-matching keyword below. Otherwise use action='text'.
{media_block}

Formatting: WhatsApp renders *bold* and _italics_ - use them sparingly for emphasis. \
Keep replies under ~60 words unless the customer asked a detailed question. \
Always write something natural for reply_text even when attaching media (use it as a caption).

Set sentiment='frustrated' only if the customer is clearly angry, has repeated a complaint, \
or is explicitly asking to speak to a human - this routes them to a real agent."""


async def llm_reasoning_node(state: AgentState) -> dict:
    tenant = state.get("tenant", {})
    history = state.get("chat_history", [])
    inbound_text = state.get("inbound_text") or ""
    media = state.get("inbound_media")
    if media and media.get("description"):
        inbound_text = (inbound_text + f"\n[attached image: {media['description']}]").strip()

    history_lines = []
    for m in history:
        speaker = "Customer" if m.get("direction") == "inbound" else "Agent"
        history_lines.append(f"{speaker}: {m.get('text') or '[media]'}")
    history_block = "\n".join(history_lines) if history_lines else "(no prior messages)"

    settings = get_settings()
    decision: AgentDecision
    try:
        model = get_chat_model(structured=True)
        decision = await model.ainvoke([
            {"role": "system", "content": _build_system_prompt(tenant)},
            {"role": "user", "content": f"Recent conversation:\n{history_block}\n\nNew customer message:\n{inbound_text}"},
        ])
    except Exception as exc:  # noqa: BLE001 - never let a provider outage kill the webhook
        logger.error("LLM reasoning failed, falling back to a safe text reply: %s", exc)
        decision = AgentDecision(
            reply_text="Thanks for your message! Our team will get back to you shortly.",
            action="text",
            sentiment="neutral",
        )

    response_type = "text"
    media_url = None
    media_filename = None
    if decision.action == "send_media":
        asset = find_media_asset(tenant.get("media_library", []), decision.media_keyword)
        if asset:
            response_type = asset["type"]
            media_url = asset["url"]
            media_filename = asset.get("filename")
        # if no asset matched, silently fall back to a text-only reply

    needs_human = bool(settings.sentiment_handover_enabled and decision.sentiment == "frustrated")

    trace = state.get("trace", []) + ["llm_reasoning"]
    new_state = {
        **state,
        "response_type": response_type,
        "response_text": decision.reply_text,
        "response_media_url": media_url,
        "response_media_filename": media_filename,
        "sentiment": decision.sentiment,
        "needs_human": needs_human,
        "trace": trace,
    }
    await _broadcast_state(new_state, "llm_reasoning")
    return {
        "response_type": response_type,
        "response_text": decision.reply_text,
        "response_media_url": media_url,
        "response_media_filename": media_filename,
        "sentiment": decision.sentiment,
        "needs_human": needs_human,
        "trace": trace,
    }


def route_after_reasoning(state: AgentState) -> str:
    """Conditional edge: frustrated customers skip the normal dispatcher and
    go straight to the human handover node."""
    return "human_handover" if state.get("needs_human") else "dispatcher"


# ---------------------------------------------------------------------------
# 4. Dispatcher Node
# ---------------------------------------------------------------------------
async def _log_outbound(state: AgentState, content_type: str, text: str | None,
                         media_url: str | None = None, media_filename: str | None = None,
                         wa_response: dict | None = None) -> None:
    await messages_col().insert_one({
        "message_id": uuid.uuid4().hex,
        "wa_message_id": (wa_response or {}).get("messages", [{}])[0].get("id") if wa_response else None,
        "tenant_id": state["tenant_id"],
        "session_id": state["session_id"],
        "customer_phone": state["customer_phone"],
        "direction": MessageDirection.OUTBOUND.value,
        "sender": "bot",
        "content_type": content_type,
        "text": text,
        "media_url": media_url,
        "media_filename": media_filename,
        "status": MessageStatus.SENT.value,
        "timestamp": _now(),
    })


async def dispatcher_node(state: AgentState) -> dict:
    """Builds and sends the actual WhatsApp payload chosen by the reasoning
    node, persists the outbound message, and flips the session back to
    RESOLVED. Sending any message implicitly clears the typing indicator."""
    client = WhatsAppClient(phone_number_id=state.get("phone_number_id"))
    to = state["customer_phone"]

    await _touch_session(state["tenant_id"], state["session_id"], status=SessionStatus.AGENT_RESPONDING.value)

    response_type = state.get("response_type", "text")
    text = state.get("response_text", "")

    if response_type == "image" and state.get("response_media_url"):
        wa_resp = await client.send_image(to, state["response_media_url"], caption=text)
        await _log_outbound(state, "image", text, state.get("response_media_url"), wa_response=wa_resp)
    elif response_type == "document" and state.get("response_media_url"):
        wa_resp = await client.send_document(
            to, state["response_media_url"], state.get("response_media_filename") or "document.pdf", caption=text
        )
        await _log_outbound(state, "document", text, state.get("response_media_url"),
                             state.get("response_media_filename"), wa_response=wa_resp)
    else:
        wa_resp = await client.send_text(to, text)
        await _log_outbound(state, "text", text, wa_response=wa_resp)

    await _touch_session(state["tenant_id"], state["session_id"], status=SessionStatus.RESOLVED.value,
                          last_message_preview=text[:120])

    trace = state.get("trace", []) + ["dispatcher"]
    new_state = {**state, "status": SessionStatus.RESOLVED.value, "trace": trace}
    await _broadcast_state(new_state, "dispatcher")
    return {"status": SessionStatus.RESOLVED.value, "trace": trace}


# ---------------------------------------------------------------------------
# Bonus: Human Handover Node
# ---------------------------------------------------------------------------
async def human_handover_node(state: AgentState) -> dict:
    """Sentiment-based fallback: sends one short holding message, flips the
    session to NEEDS_HUMAN, and halts further automated replies. The
    dashboard highlights NEEDS_HUMAN sessions in red so a real agent can
    take over."""
    client = WhatsAppClient(phone_number_id=state.get("phone_number_id"))
    holding_message = (
        "Thanks for your patience - I'm connecting you with a member of our team who can "
        "help further. They'll be with you shortly!"
    )
    wa_resp = await client.send_text(state["customer_phone"], holding_message)
    await _log_outbound(state, "text", holding_message, wa_response=wa_resp)

    await _touch_session(state["tenant_id"], state["session_id"], status=SessionStatus.NEEDS_HUMAN.value,
                          sentiment="frustrated", last_message_preview=holding_message[:120])

    trace = state.get("trace", []) + ["human_handover"]
    new_state = {**state, "status": SessionStatus.NEEDS_HUMAN.value, "trace": trace}
    await _broadcast_state(new_state, "human_handover")
    return {"status": SessionStatus.NEEDS_HUMAN.value, "trace": trace}
