"""Task 4: the webhook handler - verification handshake and signature checks."""
import hashlib
import hmac
import json


def test_verification_challenge_echoed_on_correct_token(client):
    r = client.get(
        "/api/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "test-verify-token", "hub.challenge": "999"},
    )
    assert r.status_code == 200
    assert r.text == "999"


def test_verification_rejected_on_wrong_token(client):
    r = client.get(
        "/api/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "999"},
    )
    assert r.status_code == 403


def test_inbound_post_rejects_invalid_signature(client):
    body = json.dumps({"entry": []}).encode()
    r = client.post(
        "/api/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": "sha256=not-the-real-digest", "Content-Type": "application/json"},
    )
    assert r.status_code == 403


def test_inbound_post_accepts_valid_signature(client):
    body = json.dumps({"entry": []}).encode()
    digest = hmac.new(b"test-app-secret", body, hashlib.sha256).hexdigest()
    r = client.post(
        "/api/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": f"sha256={digest}", "Content-Type": "application/json"},
    )
    assert r.status_code == 200


def test_webhook_responds_immediately_without_blocking_on_processing(client, tenant_a):
    """The brief requires a 200 within 3 seconds, with real processing happening
    in the background. We can't measure wall-clock 'before vs after the graph
    finished' through TestClient (it runs background tasks synchronously before
    returning), but we can assert the response shape never depends on graph
    output - the handler must return 200 even for an unrecognised phone_number_id."""
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "no-such-tenant-maps-to-this"},
                            "messages": [
                                {
                                    "id": "wamid.TEST",
                                    "from": "15551234567",
                                    "type": "text",
                                    "text": {"body": "hello"},
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }
    body = json.dumps(payload).encode()
    digest = hmac.new(b"test-app-secret", body, hashlib.sha256).hexdigest()
    r = client.post(
        "/api/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": f"sha256={digest}", "Content-Type": "application/json"},
    )
    assert r.status_code == 200
