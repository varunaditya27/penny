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
