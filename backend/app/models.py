"""
Pydantic models describing the three collections from Task 1 of the brief:
Tenant, Customer Interaction (ChatSession) and Message Audit Log (Message).

These are intentionally framework-light: plain Pydantic models that are
serialised straight to/from Mongo documents. No ORM, no migrations needed -
Mongo's schemaless nature is exactly why it was offered as the default choice
in the assignment.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class SessionStatus(str, Enum):
    WAITING_FOR_BOT = "WAITING_FOR_BOT"      # inbound received, agent is working
    AGENT_RESPONDING = "AGENT_RESPONDING"    # dispatcher is actively sending
    RESOLVED = "RESOLVED"                    # bot has replied, turn complete
    NEEDS_HUMAN = "NEEDS_HUMAN"              # bonus: sentiment handover triggered


class MessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"


class MessageStatus(str, Enum):
    PENDING_RESPONSE = "PENDING_RESPONSE"
    SENT = "SENT"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------
class MediaAsset(BaseModel):
    """One entry in a tenant's pre-seeded media library."""
    keyword: str                       # e.g. "catalog", "sofa", "invoice"
    type: MessageContentType           # image | document
    url: str
    filename: Optional[str] = None     # required for documents
    description: str = ""              # shown to the LLM so it knows when to use it


class Tenant(BaseModel):
    tenant_id: str = Field(default_factory=_uuid)
    name: str
    brand_color: str = "#3DDC84"
    industry: str = ""
    prompt_directions: str             # system instructions for the LLM
    whatsapp_phone_number_id: str = ""
    media_library: list[MediaAsset] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# Chat session (Customer Interaction)
# ---------------------------------------------------------------------------
class ChatSession(BaseModel):
    session_id: str = Field(default_factory=_uuid)
    tenant_id: str
    customer_phone: str
    status: SessionStatus = SessionStatus.WAITING_FOR_BOT
    context_variables: dict[str, Any] = Field(default_factory=dict)
    last_message_preview: str = ""
    sentiment: str = "neutral"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# Message Audit Log
# ---------------------------------------------------------------------------
class Message(BaseModel):
    message_id: str = Field(default_factory=_uuid)
    wa_message_id: Optional[str] = None
    tenant_id: str
    session_id: str
    customer_phone: str
    direction: MessageDirection
    sender: str                                  # "customer" | "bot" | "system"
    content_type: MessageContentType = MessageContentType.TEXT
    text: Optional[str] = None
    media_url: Optional[str] = None
    media_mime_type: Optional[str] = None
    media_filename: Optional[str] = None
    status: MessageStatus = MessageStatus.SENT
    timestamp: datetime = Field(default_factory=_utcnow)
