from typing import Literal
from langchain_core.messages import AIMessage
from langgraph.graph import END

from backend.app.agent.state import AgentState


def route_from_agent(state: AgentState) -> Literal["tools", "approval", "__end__"]:
    """
    Evaluates whether the agent produced tool calls or completed its response.
    Routes to tools, human-in-the-loop approval, or terminates turn.
    """
    messages = state.get("messages", [])
    if not messages:
        return END

    last_message = messages[-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return END

    # Check if any tool call requires immediate human approval
    for tc in last_message.tool_calls:
        if tc["name"] == "request_spending_modification_approval":
            if state.get("action_approved") is None:
                return "approval"

    return "tools"


def route_from_tools(state: AgentState) -> Literal["agent", "approval"]:
    """
    After executing tools, checks if an approval action was initiated.
    If so, transfers to approval gate; otherwise returns to agent for synthesis.
    """
    if state.get("pending_action") is not None and state.get("action_approved") is None:
        return "approval"
    return "agent"


def route_from_approval(state: AgentState) -> Literal["agent", "__end__"]:
    """
    After the approval node executes:
    If the approval decision is still pending (awaiting external user input), pause at END.
    If the decision has been submitted (True or False), route back to agent.
    """
    if state.get("action_approved") is not None:
        return "agent"
    return END
