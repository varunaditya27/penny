from typing import Annotated, Any, Dict, List, Optional, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Lightweight, modular graph state schema for Penny's financial assistant.
    Maintains conversational memory, user context, decision cards, and
    human-in-the-loop approval workflows.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    pending_action: Optional[Dict[str, Any]]
    action_approved: Optional[bool]
    decision_card: Optional[Dict[str, Any]]
    context: Dict[str, Any]
