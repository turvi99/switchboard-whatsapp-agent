"""
Populates MongoDB with the two demo tenants from the assignment's business
scenario, plus a handful of realistic sample conversations so the dashboard
has something to show the moment you open it - no need to message a live
WhatsApp sandbox number just to see the UI come alive.

Run with:  python -m app.seed
(safe to run multiple times - tenants are upserted by tenant_id, demo
sessions/messages are only inserted if the tenant has none yet)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.database import close_mongo_connection, connect_to_mongo, messages_col, sessions_col, tenants_col
from app.models import ChatSession, Message, MessageDirection, MessageStatus, SessionStatus, Tenant

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app.seed")

TENANT_A = Tenant(
    tenant_id="tenant-aurelia-oak",
    name="Aurelia & Oak",
    brand_color="#C8A24A",
    industry="Luxury Furniture",
    whatsapp_phone_number_id="REPLACE_WITH_TENANT_A_PHONE_NUMBER_ID",
    prompt_directions=(
        "You are the concierge for Aurelia & Oak, a luxury furniture boutique. Speak in a warm, "
        "refined, unhurried tone - think five-star hotel concierge, not a call center script. "
        "Customers usually ask about our handcrafted sofas, showroom hours, or want to see the "
        "catalog. Always offer to send the catalog or a showroom photo when it's relevant. Never "
        "discuss pricing in specific numbers - invite them to the showroom or to request the catalog."
    ),
    media_library=[
        {
            "keyword": "catalog",
            "type": "document",
            "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            "filename": "Aurelia-and-Oak-Catalog.pdf",
            "description": "Full seasonal product catalog with pricing and finishes",
        },
        {
            "keyword": "sofa",
            "type": "image",
            "url": "https://picsum.photos/seed/aurelia-sofa/900/700",
            "description": "Photo of our signature Belmore hand-stitched leather sofa",
        },
        {
            "keyword": "showroom",
            "type": "image",
            "url": "https://picsum.photos/seed/aurelia-showroom/900/700",
            "description": "Photo of the Aurelia & Oak flagship showroom interior",
        },
    ],
)

TENANT_B = Tenant(
    tenant_id="tenant-torquepoint",
    name="TorquePoint Automotive Care",
    brand_color="#3E7CB1",
    industry="Automotive Service",
    whatsapp_phone_number_id="REPLACE_WITH_TENANT_B_PHONE_NUMBER_ID",
    prompt_directions=(
        "You are the service desk assistant for TorquePoint Automotive Care. Be direct, efficient "
        "and reassuring - customers are often stressed about car trouble or cost. Help them book "
        "service appointments, answer basic questions about common repairs, and send the invoice "
        "sheet or a repair diagram when asked. If a customer describes a safety issue (brakes, "
        "steering, smoke), prioritize urgency in your tone and recommend they bring the vehicle in "
        "immediately."
    ),
    media_library=[
        {
            "keyword": "invoice",
            "type": "document",
            "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            "filename": "TorquePoint-Service-Invoice.pdf",
            "description": "Sample itemized service invoice sheet",
        },
        {
            "keyword": "diagram",
            "type": "image",
            "url": "https://picsum.photos/seed/torquepoint-diagram/900/700",
            "description": "Repair diagram showing the brake pad replacement procedure",
        },
        {
            "keyword": "brakes",
            "type": "image",
            "url": "https://picsum.photos/seed/torquepoint-brakes/900/700",
            "description": "Close-up diagram of brake pad wear indicators",
        },
    ],
)


async def _seed_conversation(tenant_id: str, phone: str, status: SessionStatus, sentiment: str,
                              exchanges: list[tuple[str, str]], minutes_ago_start: int) -> None:
    """exchanges: list of (customer_text, bot_text) tuples, oldest first."""
    existing = await sessions_col().find_one({"tenant_id": tenant_id, "customer_phone": phone})
    if existing:
        return  # demo data already present, don't duplicate on re-seed

    session = ChatSession(
        tenant_id=tenant_id,
        customer_phone=phone,
        status=status,
        sentiment=sentiment,
        last_message_preview=exchanges[-1][1][:120],
    )
    await sessions_col().insert_one(session.model_dump())

    t = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago_start)
    for customer_text, bot_text in exchanges:
        in_msg = Message(
            tenant_id=tenant_id, session_id=session.session_id, customer_phone=phone,
            direction=MessageDirection.INBOUND, sender="customer", text=customer_text,
            status=MessageStatus.PENDING_RESPONSE, timestamp=t,
        )
        await messages_col().insert_one(in_msg.model_dump())
        t += timedelta(seconds=20)
        out_msg = Message(
            tenant_id=tenant_id, session_id=session.session_id, customer_phone=phone,
            direction=MessageDirection.OUTBOUND, sender="bot", text=bot_text,
            status=MessageStatus.SENT, timestamp=t,
        )
        await messages_col().insert_one(out_msg.model_dump())
        t += timedelta(minutes=4)


async def seed() -> None:
    await connect_to_mongo()

    for tenant in (TENANT_A, TENANT_B):
        await tenants_col().update_one(
            {"tenant_id": tenant.tenant_id}, {"$set": tenant.model_dump()}, upsert=True
        )
        logger.info("Upserted tenant '%s' (%s)", tenant.name, tenant.tenant_id)

    await _seed_conversation(
        TENANT_A.tenant_id, "+15550101001", SessionStatus.RESOLVED, "neutral",
        [
            ("Hi! Do you have any leather sofas in stock?",
             "Hello and welcome to Aurelia & Oak! Yes - our signature *Belmore* sofa is hand-stitched "
             "in full-grain leather. Would you like to see a photo or our full catalog?"),
            ("A photo would be great, thanks!",
             "Of course - here's the Belmore in our showroom. It's even more striking in person!"),
        ],
        minutes_ago_start=42,
    )
    await _seed_conversation(
        TENANT_A.tenant_id, "+15550101002", SessionStatus.NEEDS_HUMAN, "frustrated",
        [
            ("I ordered a dining table 3 weeks ago and it still hasn't shipped, this is ridiculous",
             "I'm really sorry to hear about the delay - that's not the experience we want for you. "
             "Let me connect you with a member of our team who can look into your order directly."),
        ],
        minutes_ago_start=12,
    )

    await _seed_conversation(
        TENANT_B.tenant_id, "+15550202001", SessionStatus.RESOLVED, "neutral",
        [
            ("Can I get a copy of my last service invoice?",
             "Sure thing! Here's your most recent invoice from TorquePoint."),
        ],
        minutes_ago_start=30,
    )
    await _seed_conversation(
        TENANT_B.tenant_id, "+15550202002", SessionStatus.WAITING_FOR_BOT, "neutral",
        [
            ("My brakes have been squeaking for a few days, should I be worried?",
             "Squeaking brakes are usually worn pads - here's a quick diagram showing what to look "
             "for. I'd recommend bringing it in this week so we can take a look before it affects "
             "your rotors."),
        ],
        minutes_ago_start=5,
    )

    logger.info("Seed complete.")
    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(seed())
