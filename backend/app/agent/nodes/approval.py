from typing import Any, Dict
from langchain_core.messages import AIMessage, HumanMessage

from backend.app.agent.state import AgentState


def approval_node(state: AgentState) -> Dict[str, Any]:
    """
    Human-in-the-Loop approval node.
    Inspects pending_action and action_approved status.
    If approval has not been decided yet, emits an explicit request for confirmation.
    If approval is decided, acknowledges user's decision and updates state.
    """
    pending = state.get("pending_action")
    approved = state.get("action_approved")

    if approved is True:
        category = pending.get("category", "expenses") if pending else "expenses"
        msg = AIMessage(
            content=f"Budget modification approved by user for category: {category}. Applying changes to plan."
        )
        return {
            "messages": [msg],
            "pending_action": None,
            "action_approved": True,
        }
    elif approved is False:
        category = pending.get("category", "expenses") if pending else "expenses"
        msg = AIMessage(
            content=f"Budget modification declined by user for category: {category}. Searching for alternative options."
        )
        return {
            "messages": [msg],
            "pending_action": None,
            "action_approved": False,
        }

    # If pending and approval not yet submitted
    desc = pending.get("message", "Approval required for spending modification.") if pending else "Approval required."
    msg = AIMessage(
        content=f"⚠️ {desc} Please submit approval to proceed with this adjustment."
    )
    return {
        "messages": [msg],
    }
