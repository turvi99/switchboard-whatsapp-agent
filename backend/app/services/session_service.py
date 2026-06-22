"""
Small helpers shared by the real Meta webhook handler and the built-in
dashboard simulator: resolving which tenant a message belongs to, and
getting-or-creating the chat session it lives in.
"""
from __future__ import annotations

from app.database import sessions_col, tenants_col
from app.models import ChatSession


async def resolve_tenant_by_phone_number_id(phone_number_id: str) -> dict | None:
    return await tenants_col().find_one({"whatsapp_phone_number_id": phone_number_id}, {"_id": 0})


async def resolve_tenant_by_id(tenant_id: str) -> dict | None:
    return await tenants_col().find_one({"tenant_id": tenant_id}, {"_id": 0})


async def get_or_create_session(tenant_id: str, customer_phone: str) -> str:
    existing = await sessions_col().find_one({"tenant_id": tenant_id, "customer_phone": customer_phone})
    if existing:
        return existing["session_id"]

    session = ChatSession(tenant_id=tenant_id, customer_phone=customer_phone)
    await sessions_col().insert_one(session.model_dump())
    return session.session_id
