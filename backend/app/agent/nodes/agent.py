import logging
from typing import Any, Callable, Dict
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.runnables import Runnable, RunnableConfig

from backend.app.agent.prompts.system import PENNY_SYSTEM_PROMPT
from backend.app.agent.state import AgentState
from backend.app.agent.supervisor import DeterministicFallbackChatModel

logger = logging.getLogger("penny.agent.nodes.agent")


def create_agent_node(llm_with_tools: Runnable) -> Callable[[AgentState, RunnableConfig], Dict[str, Any]]:
    """
    Constructs the conversational agent node.
    Injects the Penny system prompt and calls the tool-bound model.
    Falls back gracefully to DeterministicFallbackChatModel if remote LLM call fails.
    """
    def agent_node(state: AgentState, config: RunnableConfig = None) -> Dict[str, Any]:
        messages = list(state.get("messages", []))

        # Ensure system prompt is present as the foundational instruction
        if not messages or not isinstance(messages[0], SystemMessage):
            system_msg = SystemMessage(content=PENNY_SYSTEM_PROMPT)
            full_messages = [system_msg] + messages
        else:
            full_messages = messages

        try:
            response = llm_with_tools.invoke(full_messages, config=config)
        except Exception as exc:
            logger.warning("LLM invocation failed (%s); engaging deterministic fallback.", exc)
            fallback = DeterministicFallbackChatModel()
            response = fallback.invoke(full_messages, config=config)

        return {"messages": [response]}

    return agent_node

