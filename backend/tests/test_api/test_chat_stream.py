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
        "feedback": "Approved by user.",
    }
    resp = client.post("/api/v1/chat/approve", json=approval_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "approved" in data["message"]


def test_chat_stream_multi_turn_persistence(client: TestClient):
    """Verifies conversational history is maintained across sequential stream calls on same session."""
    session_id = "test_turn_persistence_sess"

    # Turn 1
    resp1 = client.post(
        "/api/v1/chat/stream",
        json={
            "user_id": "user_01",
            "message": "My name is Charlie.",
            "session_id": session_id,
        },
    )
    assert resp1.status_code == 200

    # Turn 2
    resp2 = client.post(
        "/api/v1/chat/stream",
        json={
            "user_id": "user_01",
            "message": "What is my name?",
            "session_id": session_id,
        },
    )
    assert resp2.status_code == 200

    # Verify checkpointer retained history
    from backend.app.agent.checkpointers.memory import get_memory_checkpointer
    cp = get_memory_checkpointer()
    state = cp.get({"configurable": {"thread_id": session_id}})
    assert state is not None
    messages = state["channel_values"]["messages"]
    # At least 2 turns (Human, AI, Human, AI)
    assert len(messages) >= 4


def test_chat_approval_nonexistent_session(client: TestClient):
    """Verifies 404 when approving a non-existent chat session."""
    payload = {
        "user_id": "user_01",
        "session_id": "nonexistent_session_9999",
        "approved": True,
    }
    resp = client.post("/api/v1/chat/approve", json=payload)
    assert resp.status_code == 404
    assert "no active session" in resp.json()["detail"].lower()


def test_chat_approval_action_id_mismatch(client: TestClient, db_session):
    """Verifies 400 when approving with an action_id that does not match pending action."""
    from backend.app.agent.graph import create_penny_agent
    session_id = "test_mismatch_sess"

    # Seed checkpointer with pending action using agent.update_state
    agent = create_penny_agent(db_session)
    agent.update_state(
        {"configurable": {"thread_id": session_id}},
        {
            "messages": [],
            "user_id": "user_01",
            "pending_action": {"action_id": "act_expected_123", "category": "dining"},
            "action_approved": None,
        },
    )

    payload = {
        "user_id": "user_01",
        "session_id": session_id,
        "approved": True,
        "action_id": "act_wrong_999",
    }
    resp = client.post("/api/v1/chat/approve", json=payload)
    assert resp.status_code == 400
    assert "does not match" in resp.json()["detail"].lower()
