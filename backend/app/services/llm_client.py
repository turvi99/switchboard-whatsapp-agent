"""
LLM access layer. Kept separate from the LangGraph nodes so the rest of the
graph never has to care whether we're talking to OpenAI or Anthropic.

`AgentDecision` is the structured-output schema the reasoning node forces the
model into - this is how the "Agentic Decision-Making" requirement
(plain text vs. attach an image/document from the tenant's library) is
implemented: instead of brittle string parsing or manual tool-call plumbing,
we ask the model to return one well-typed object and branch on it.
"""
from __future__ import annotations

import base64
import logging
from typing import Literal, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from app.config import get_settings

logger = logging.getLogger("app.llm")


class AgentDecision(BaseModel):
    """What the LLM Reasoning Node decides to do with an inbound message."""

    reply_text: str = Field(
        description="The conversational reply to send the customer. Always populate this, "
        "even when also attaching media (use it as the caption / lead-in text)."
    )
    action: Literal["text", "send_media"] = Field(
        description="'text' for a plain reply, 'send_media' if the tenant's media library "
        "contains an asset (catalog, image, invoice, diagram, etc.) the customer is asking for."
    )
    media_keyword: Optional[str] = Field(
        default=None,
        description="When action is 'send_media', the single keyword from the tenant's media "
        "library that best matches what the customer wants (e.g. 'catalog', 'sofa').",
    )
    sentiment: Literal["neutral", "frustrated"] = Field(
        default="neutral",
        description="'frustrated' if the customer shows clear signs of anger, repeated "
        "complaints, or explicitly asks for a human - triggers handover.",
    )


def get_chat_model(structured: bool = False):
    """Returns a LangChain chat model configured from env, optionally bound
    to the AgentDecision structured-output schema."""
    settings = get_settings()

    model: BaseChatModel
    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        model = ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key or None,
            temperature=0.4,
        )
    else:
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key or None,
            temperature=0.4,
        )

    if structured:
        return model.with_structured_output(AgentDecision)
    return model


async def describe_inbound_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """
    Bonus: multimodal parsing of inbound customer images. Takes the raw
    bytes already downloaded via WhatsAppClient.download_media_bytes() (Meta
    media URLs are Bearer-auth-gated and short-lived, so resolution happens
    one layer up) and asks a vision-capable model to describe it in one or
    two sentences so it can be folded into the chat history / context the
    reasoning node sees next.
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    model = get_chat_model(structured=False)
    try:
        result = await model.ainvoke(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image in one short sentence, "
                         "focused on anything relevant to a retail/customer-support context "
                         "(product shown, visible damage, document type, etc.)."},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                    ],
                }
            ]
        )
        return result.content if isinstance(result.content, str) else str(result.content)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Vision description failed: %s", exc)
        return "[customer sent an image]"
