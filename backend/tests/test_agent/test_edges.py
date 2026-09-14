from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END

from backend.app.agent.edges.routing import (
    route_from_agent,
    route_from_approval,
    route_from_tools,
)


def test_route_from_agent():
    """Verifies edge routing from agent node depending on message and tool calls."""
    # Case 1: Final answer without tool calls -> END
    state_final = {
        "messages": [AIMessage(content="You can easily afford this purchase.")],
        "user_id": "user_01",
    }
    assert route_from_agent(state_final) == END

    # Case 2: Standard tool calls -> tools node
    state_tool = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"id": "c1", "name": "evaluate_purchase", "args": {}}],
            )
        ],
        "user_id": "user_01",
    }
    assert route_from_agent(state_tool) == "tools"

    # Case 3: Human approval tool call -> approval node
    state_approval = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {"id": "c2", "name": "request_spending_modification_approval", "args": {}}
                ],
            )
        ],
        "user_id": "user_01",
        "action_approved": None,
    }
    assert route_from_agent(state_approval) == "approval"


def test_route_from_tools():
    """Verifies edge routing from tools node."""
    # No pending action -> route back to agent
    state_normal = {"pending_action": None, "action_approved": None}
    assert route_from_tools(state_normal) == "agent"

    # Pending action requiring confirmation -> route to approval
    state_pending = {"pending_action": {"action_id": "act_123"}, "action_approved": None}
    assert route_from_tools(state_pending) == "approval"


def test_route_from_approval():
    """Verifies edge routing from approval node."""
    # Approval decision resolved -> agent
    state_resolved = {"action_approved": True}
    assert route_from_approval(state_resolved) == "agent"

    # Approval still pending -> END (waiting for client)
    state_waiting = {"action_approved": None}
    assert route_from_approval(state_waiting) == END
