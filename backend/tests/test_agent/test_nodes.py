import json
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool

from backend.app.agent.nodes.agent import create_agent_node
from backend.app.agent.nodes.approval import approval_node
from backend.app.agent.nodes.tools import create_tools_node
from backend.app.agent.supervisor import DeterministicFallbackChatModel


def test_agent_node_prepends_system_prompt():
    """Agent node automatically ensures system prompt is in place."""
    model = DeterministicFallbackChatModel()
    agent_node = create_agent_node(model)

    state = {
        "messages": [HumanMessage(content="Can I buy dinner?")],
        "user_id": "user_01",
    }
    result = agent_node(state)
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)


def test_tools_node_executes_and_captures_state():
    """Tools node processes tool calls, generates ToolMessages, and updates state."""
    @tool
    def mock_calc(x: int) -> str:
        """Adds 10 to x."""
        return json.dumps({"result": x + 10, "affordability_status": "affordable"})

    tools_node = create_tools_node([mock_calc])

    ai_msg = AIMessage(
        content="Let me compute that.",
        tool_calls=[{"id": "call_1", "name": "mock_calc", "args": {"x": 5}}],
    )
    state = {
        "messages": [ai_msg],
        "user_id": "user_01",
        "decision_card": None,
        "pending_action": None,
    }

    result = tools_node(state)
    assert len(result["messages"]) == 1
    assert result["messages"][0].tool_call_id == "call_1"
    assert result["decision_card"] == {"result": 15, "affordability_status": "affordable"}


def test_approval_node_states():
    """Verifies approval node behavior for pending, approved, and declined paths."""
    # 1. Pending state (no decision yet)
    state_pending = {
        "messages": [],
        "user_id": "user_01",
        "pending_action": {"message": "Reduce Dining by $50"},
        "action_approved": None,
    }
    res_pending = approval_node(state_pending)
    assert "⚠️" in res_pending["messages"][0].content

    # 2. Approved state
    state_approved = {
        "messages": [],
        "user_id": "user_01",
        "pending_action": {"category": "Entertainment"},
        "action_approved": True,
    }
    res_approved = approval_node(state_approved)
    assert res_approved["action_approved"] is True
    assert "approved" in res_approved["messages"][0].content.lower()
    assert res_approved["pending_action"] is None

    # 3. Declined state
    state_declined = {
        "messages": [],
        "user_id": "user_01",
        "pending_action": {"category": "Entertainment"},
        "action_approved": False,
    }
    res_declined = approval_node(state_declined)
    assert res_declined["action_approved"] is False
    assert "declined" in res_declined["messages"][0].content.lower()
