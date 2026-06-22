"""
The shared state object every LangGraph node reads from and writes to.

This is intentionally a flat TypedDict (the LangGraph-idiomatic way to model
state) rather than nested objects, so it's trivial to log/inspect at every
step - which matters for the assignment's emphasis on "how state flows
through your agent". The dashboard's pipeline strip and the /api/simulate
endpoint both return a snapshot of this dict after each run.
"""
from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict


class InboundMedia(TypedDict, total=False):
    media_id: str
    type: str  # WhatsApp's own type: image | document | audio | video | sticker
    mime_type: str
    url: str
    description: str  # populated by the bonus vision-parsing step


class AgentState(TypedDict, total=False):
    # --- identity -------------------------------------------------------
    tenant_id: str
    customer_phone: str
    session_id: str
    phone_number_id: str

    # --- inbound ----------------------------------------------------------
    wa_message_id: str
    inbound_text: str
    inbound_media: Optional[InboundMedia]

    # --- pulled by the context retriever node ------------------------------
    tenant: dict[str, Any]
    chat_history: list[dict[str, Any]]

    # --- produced by the reasoning node -------------------------------------
    response_type: Literal["text", "image", "document"]
    response_text: str
    response_media_url: Optional[str]
    response_media_filename: Optional[str]
    sentiment: Literal["neutral", "frustrated"]
    needs_human: bool

    # --- pipeline bookkeeping (surfaced to the dashboard) -------------------
    status: str
    trace: list[str]  # ordered list of node names that have run, for the UI
