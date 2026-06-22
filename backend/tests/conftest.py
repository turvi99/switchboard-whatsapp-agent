"""
Shared pytest fixtures.

The whole suite runs against an in-memory MongoDB (via mongomock-motor)
rather than a real database, and forces DRY_RUN_WHATSAPP so no test ever
makes a real call to Meta's Graph API. This means `pytest` works offline,
in CI, or on a laptop with nothing else running - no docker-compose, no
real WhatsApp Business App, no LLM API key required. The LLM call itself
will fail fast without network/credentials and the pipeline's built-in
fallback (see app/graph/nodes.py::llm_reasoning_node) takes over, so the
graph-shape and persistence assertions in this suite still hold even
though the *content* of the bot's reply is the generic fallback text in
that situation.

If you run these tests with a real OPENAI_API_KEY or ANTHROPIC_API_KEY
exported in your shell, the suite will exercise the real LLM call instead.
Either way the tests pass.
"""
from __future__ import annotations

import asyncio
import os

os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB_NAME", "switchboard_test")
os.environ.setdefault("DRY_RUN_WHATSAPP", "true")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-not-real")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "test-verify-token")
os.environ.setdefault("WHATSAPP_APP_SECRET", "test-app-secret")
os.environ.setdefault("SENTIMENT_HANDOVER_ENABLED", "true")

import pytest  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

import app.database as database  # noqa: E402

# Swap the real Motor client for an in-memory mock *before* app.main (or
# anything that touches the database) ever gets imported by a test module.
database.AsyncIOMotorClient = AsyncMongoMockClient

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app as fastapi_app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture()
def client():
    """A fresh, seeded TestClient for each test - full isolation, no shared state."""
    with TestClient(fastapi_app) as c:
        asyncio.run(seed())
        yield c


@pytest.fixture()
def tenant_a(client):
    tenants = client.get("/api/tenants").json()
    return next(t for t in tenants if "Aurelia" in t["name"])


@pytest.fixture()
def tenant_b(client):
    tenants = client.get("/api/tenants").json()
    return next(t for t in tenants if "TorquePoint" in t["name"])
