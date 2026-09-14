import pytest
from fastapi.testclient import TestClient


def test_chat_stream_endpoint(client: TestClient):
    """Verifies that /api/v1/chat/stream returns a streaming SSE response with valid event types."""
    payload = {
        "user_id": "user_01",
        "message": "Can I afford to buy a $150 dinner tonight?",
        "session_id": "test_stream_session_01",
    }
    with client.stream("POST", "/api/v1/chat/stream", json=payload) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        lines = [line for line in response.iter_lines() if line]
        assert len(lines) > 0

        # Check for standard SSE event prefixes
        event_lines = [l for l in lines if l.startswith("event:")]
        data_lines = [l for l in lines if l.startswith("data:")]

        assert len(event_lines) > 0
        assert len(data_lines) > 0

        event_types = {l.split("event:")[1].strip() for l in event_lines}
        assert "status" in event_types
        assert "done" in event_types


def test_chat_stream_nonexistent_user(client: TestClient):
    """Verifies 404 when streaming chat for a non-existent user."""
    payload = {
        "user_id": "non_existent_user_999",
        "message": "Can I afford this?",
    }
    response = client.post("/api/v1/chat/stream", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_chat_approval_endpoint(client: TestClient):
    """Verifies that /api/v1/chat/approve records human-in-the-loop decisions."""
    # Seed session state first via a stream call
    client.post(
        "/api/v1/chat/stream",
        json={
            "user_id": "user_01",
            "message": "Hello Penny",
            "session_id": "test_approval_session",
        },
    )

    # Submit approval
    approval_payload = {
        "user_id": "user_01",
        "session_id": "test_approval_session",
        "approved": True,
        "action_id": "act_test_001",
        "feedback": "Approved by user.",
    }
    resp = client.post("/api/v1/chat/approve", json=approval_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "approved" in data["message"]
