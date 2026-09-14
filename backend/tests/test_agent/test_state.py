from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.message import add_messages

from backend.app.agent.state import AgentState


def test_agent_state_structure():
    """Verifies AgentState dictionary keys and types."""
    state: AgentState = {
        "messages": [HumanMessage(content="Can I buy this?")],
        "user_id": "user_01",
        "pending_action": None,
        "action_approved": None,
        "decision_card": None,
        "context": {"source": "mobile_app"},
    }
    assert state["user_id"] == "user_01"
    assert len(state["messages"]) == 1
    assert state["pending_action"] is None
    assert state["context"]["source"] == "mobile_app"


def test_agent_state_message_reducer():
    """Verifies that add_messages appends and preserves message history."""
    m1 = HumanMessage(content="Hello Penny", id="m1")
    m2 = AIMessage(content="Hello! How can I assist?", id="m2")

    combined = add_messages([m1], [m2])
    assert len(combined) == 2
    assert combined[0].content == "Hello Penny"
    assert combined[1].content == "Hello! How can I assist?"
