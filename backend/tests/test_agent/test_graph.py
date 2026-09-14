from langchain_core.messages import HumanMessage
from backend.app.agent import create_penny_agent


def test_agent_graph_execution(db_session):
    """Executes single-turn conversation through compiled LangGraph."""
    agent = create_penny_agent(db_session)
    initial_state = {
        "messages": [HumanMessage(content="Hello Penny, can I afford a $100 jacket today?")],
        "user_id": "user_01",
    }
    config = {"configurable": {"thread_id": "test_sess_001"}}

    res = agent.invoke(initial_state, config=config)
    assert "messages" in res
    assert len(res["messages"]) >= 2
    last_msg = res["messages"][-1]
    assert last_msg.content != ""


def test_agent_graph_stateful_multi_turn(db_session):
    """Verifies that thread_id maintains conversational state across sequential turns."""
    agent = create_penny_agent(db_session)
    config = {"configurable": {"thread_id": "test_sess_multi"}}

    # Turn 1
    state_turn1 = {
        "messages": [HumanMessage(content="My name is Alex.")],
        "user_id": "user_01",
    }
    res_turn1 = agent.invoke(state_turn1, config=config)
    assert len(res_turn1["messages"]) >= 2

    # Turn 2 on same thread
    state_turn2 = {
        "messages": [HumanMessage(content="What was my name?")],
        "user_id": "user_01",
    }
    res_turn2 = agent.invoke(state_turn2, config=config)
    # Total messages on thread should now be >= 4 (Human, AI, Human, AI)
    assert len(res_turn2["messages"]) >= 4


def test_agent_graph_approval_cycle_and_persistence(db_session):
    """Verifies end-to-end tool execution into approval node and thread state persistence."""
    from langchain_core.messages import AIMessage, ToolMessage
    from backend.app.agent.supervisor import DeterministicFallbackChatModel

    class MockApprovalToolModel(DeterministicFallbackChatModel):
        def invoke(self, messages, *args, **kwargs):
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "request_spending_modification_approval",
                    "args": {
                        "user_id": "user_01",
                        "category": "Dining Out",
                        "reduction_amount": 50.0,
                        "reason": "Afford purchase",
                    },
                    "id": "call_approve_001",
                }],
            )

    config = {"configurable": {"thread_id": "test_approval_full_loop"}}

    # 1. Agent 1 initiates approval via tool call
    agent1 = create_penny_agent(db_session, llm=MockApprovalToolModel())
    res = agent1.invoke(
        {"messages": [HumanMessage(content="Can I buy concert tickets?")], "user_id": "user_01"},
        config=config,
    )

    # Verify tool execution occurred and ToolMessage was recorded
    tool_msgs = [m for m in res["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_msgs) == 1
    assert tool_msgs[0].tool_call_id == "call_approve_001"

    # Verify pending action was captured and approval node emitted prompt
    assert res.get("pending_action") is not None
    assert res["pending_action"]["category"] == "Dining Out"
    assert "Dining Out" in res["messages"][-1].content

    # 2. Agent 2 instantiated separately (simulating separate HTTP request)
    agent2 = create_penny_agent(db_session)
    state2 = agent2.get_state(config)
    assert state2.values.get("pending_action") is not None

    # Apply user approval
    agent2.update_state(
        config=config,
        values={"action_approved": True, "pending_action": None},
        as_node="approval",
    )

    # Next node should cleanly point to agent
    assert agent2.get_state(config).next == ("agent",)
