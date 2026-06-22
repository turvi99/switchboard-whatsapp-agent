"""Task 5 (backend half) - the dashboard API the frontend console reads from,
plus the broadcast campaign drawer's endpoint."""


def test_list_tenants_excludes_prompt_directions(client):
    tenants = client.get("/api/tenants").json()
    assert len(tenants) == 2
    for t in tenants:
        assert "prompt_directions" not in t


def test_tenant_detail_includes_media_library(client, tenant_a):
    detail = client.get(f"/api/tenants/{tenant_a['tenant_id']}").json()
    assert len(detail["media_library"]) >= 1
    keywords = {asset["keyword"] for asset in detail["media_library"]}
    assert "sofa" in keywords or "catalog" in keywords


def test_tenant_detail_404_for_unknown_id(client):
    r = client.get("/api/tenants/does-not-exist")
    assert r.status_code == 404


def test_stats_shape(client, tenant_a):
    stats = client.get(f"/api/tenants/{tenant_a['tenant_id']}/stats").json()
    for key in ("active_sessions", "needs_human", "resolved_today", "total_sessions", "total_messages"):
        assert key in stats
        assert isinstance(stats[key], int)


def test_sessions_filterable_by_status(client, tenant_a):
    all_sessions = client.get(f"/api/tenants/{tenant_a['tenant_id']}/sessions").json()
    resolved_only = client.get(f"/api/tenants/{tenant_a['tenant_id']}/sessions?status=RESOLVED").json()
    assert len(resolved_only) <= len(all_sessions)
    assert all(s["status"] == "RESOLVED" for s in resolved_only)


def test_tenant_isolation_sessions_dont_leak_across_tenants(client, tenant_a, tenant_b):
    """Multi-tenancy guarantee: tenant B must never see tenant A's sessions."""
    sessions_a = client.get(f"/api/tenants/{tenant_a['tenant_id']}/sessions").json()
    sessions_b = client.get(f"/api/tenants/{tenant_b['tenant_id']}/sessions").json()
    ids_a = {s["session_id"] for s in sessions_a}
    ids_b = {s["session_id"] for s in sessions_b}
    assert ids_a.isdisjoint(ids_b)


def test_broadcast_all_cohort_sends_to_every_session(client, tenant_a):
    sessions_before = client.get(f"/api/tenants/{tenant_a['tenant_id']}/sessions").json()
    r = client.post(
        f"/api/tenants/{tenant_a['tenant_id']}/broadcast",
        json={"cohort": "all", "template_name": "catalog_promo", "preview_text": "New arrivals!"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["sent"] == len(sessions_before)


def test_broadcast_needs_human_cohort_targets_only_flagged_sessions(client, tenant_a):
    r = client.post(
        f"/api/tenants/{tenant_a['tenant_id']}/broadcast",
        json={"cohort": "needs_human", "template_name": "we_miss_you", "preview_text": "Let's fix this."},
    )
    assert r.status_code == 200
    needs_human = client.get(f"/api/tenants/{tenant_a['tenant_id']}/sessions?status=NEEDS_HUMAN").json()
    assert r.json()["sent"] == len(needs_human)


def test_broadcast_custom_cohort_uses_provided_numbers(client, tenant_a):
    r = client.post(
        f"/api/tenants/{tenant_a['tenant_id']}/broadcast",
        json={
            "cohort": "custom",
            "phone_numbers": ["+15551112222"],
            "template_name": "catalog_promo",
            "preview_text": "Hi there",
        },
    )
    assert r.status_code == 200
    # Custom numbers with no existing session are silently skipped (no
    # message row to attach to) - this just confirms the endpoint doesn't 500.
    assert "sent" in r.json()


def test_broadcast_empty_cohort_returns_zero_sent(client, tenant_a):
    r = client.post(
        f"/api/tenants/{tenant_a['tenant_id']}/broadcast",
        json={"cohort": "custom", "phone_numbers": [], "template_name": "x", "preview_text": "x"},
    )
    assert r.status_code == 200
    assert r.json()["sent"] == 0
