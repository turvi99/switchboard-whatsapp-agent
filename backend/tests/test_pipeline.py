"""Task 3: the LangGraph agentic pipeline - node sequence and persistence."""


def test_simulated_text_message_runs_full_pipeline_and_resolves(client, tenant_a):
    r = client.post(
        "/api/simulate/inbound",
        json={
            "tenant_id": tenant_a["tenant_id"],
            "customer_phone": "+15557770001",
            "text": "Hi, do you have a sofa catalog you can send me?",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["trace"] == ["acknowledge", "context_retriever", "llm_reasoning", "dispatcher"]
    assert body["final_status"] == "RESOLVED"
    assert body["response_text"]


def test_pipeline_persists_inbound_then_outbound_message(client, tenant_a):
    phone = "+15557770002"
    r = client.post(
        "/api/simulate/inbound",
        json={"tenant_id": tenant_a["tenant_id"], "customer_phone": phone, "text": "What are your hours?"},
    )
    session_id = r.json()["session_id"]

    msgs = client.get(f"/api/tenants/{tenant_a['tenant_id']}/sessions/{session_id}/messages").json()
    assert len(msgs) == 2
    assert msgs[0]["direction"] == "inbound"
    assert msgs[0]["text"] == "What are your hours?"
    assert msgs[1]["direction"] == "outbound"
    assert msgs[1]["status"] == "SENT"


def test_pipeline_session_status_reaches_resolved_in_session_list(client, tenant_a):
    phone = "+15557770003"
    client.post(
        "/api/simulate/inbound",
        json={"tenant_id": tenant_a["tenant_id"], "customer_phone": phone, "text": "Just checking in"},
    )
    sessions = client.get(f"/api/tenants/{tenant_a['tenant_id']}/sessions").json()
    matching = next(s for s in sessions if s["customer_phone"] == phone)
    assert matching["status"] == "RESOLVED"
    assert matching["last_message_preview"]


def test_simulate_inbound_unknown_tenant_returns_404(client):
    r = client.post(
        "/api/simulate/inbound",
        json={"tenant_id": "does-not-exist", "customer_phone": "+15550000000", "text": "hi"},
    )
    assert r.status_code == 404


def test_simulated_image_message_exercises_media_branch(client, tenant_a):
    """simulate_image=True attaches a placeholder inbound media block, exercising
    the same code path a real inbound photo would (Task 3's bonus multimodal
    parsing tries to describe it; on failure it degrades gracefully per
    app/graph/nodes.py::context_retriever_node, so the pipeline still completes)."""
    r = client.post(
        "/api/simulate/inbound",
        json={
            "tenant_id": tenant_a["tenant_id"],
            "customer_phone": "+15557770004",
            "text": "What do you think of this?",
            "simulate_image": True,
        },
    )
    assert r.status_code == 200
    assert r.json()["trace"][0] == "acknowledge"


def test_seeded_demo_conversation_is_pre_flagged_needs_human(client, tenant_a):
    """The seed data includes one deliberately frustrated conversation so the
    NEEDS_HUMAN / red-highlight bonus path is visible without triggering it
    live (useful since the fallback LLM decision in offline test runs is
    always neutral)."""
    sessions = client.get(f"/api/tenants/{tenant_a['tenant_id']}/sessions?status=NEEDS_HUMAN").json()
    assert len(sessions) >= 1
    assert sessions[0]["sentiment"] == "frustrated"


def test_get_or_create_session_is_idempotent(client, tenant_a):
    """Two inbound messages from the same customer must land on the same
    session, not create duplicates - this is what the unique (tenant_id,
    customer_phone) index in app/database.py is there to guarantee."""
    phone = "+15557770005"
    r1 = client.post(
        "/api/simulate/inbound",
        json={"tenant_id": tenant_a["tenant_id"], "customer_phone": phone, "text": "First message"},
    )
    r2 = client.post(
        "/api/simulate/inbound",
        json={"tenant_id": tenant_a["tenant_id"], "customer_phone": phone, "text": "Second message"},
    )
    assert r1.json()["session_id"] == r2.json()["session_id"]

    msgs = client.get(
        f"/api/tenants/{tenant_a['tenant_id']}/sessions/{r1.json()['session_id']}/messages"
    ).json()
    assert len(msgs) == 4  # inbound+outbound, twice, all on one thread
