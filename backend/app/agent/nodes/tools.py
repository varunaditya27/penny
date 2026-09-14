import json
from typing import Any, Callable, Dict, List, Sequence
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool

from backend.app.agent.state import AgentState


def create_tools_node(tools: Sequence[BaseTool]) -> Callable[[AgentState, RunnableConfig], Dict[str, Any]]:
    """
    Constructs the tool execution node.
    Executes tool calls requested by the agent, constructs ToolMessages,
    and updates structured state items like decision_card and pending_action.
    """
    tools_by_name = {tool.name: tool for tool in tools}

    def tools_node(state: AgentState, config: RunnableConfig = None) -> Dict[str, Any]:
        messages = state.get("messages", [])
        if not messages:
            return {}

        last_message = messages[-1]
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {}

        tool_messages: List[ToolMessage] = []
        decision_card = state.get("decision_card")
        pending_action = state.get("pending_action")

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]

            selected_tool = tools_by_name.get(tool_name)
            if not selected_tool:
                result_str = json.dumps({"error": f"Tool '{tool_name}' not found."})
            else:
                try:
                    result = selected_tool.invoke(tool_args)
                    result_str = str(result)
                except Exception as exc:
                    result_str = json.dumps({"error": str(exc)})

            # Check if this output contains a decision card or pending action
            try:
                parsed = json.loads(result_str)
                if isinstance(parsed, dict):
                    if "affordability_status" in parsed and parsed.get("affordability_status") != "error":
                        decision_card = parsed
                    if parsed.get("status") == "pending_user_confirmation":
                        pending_action = parsed
            except Exception:
                pass

            tool_messages.append(
                ToolMessage(
                    content=result_str,
                    name=tool_name,
                    tool_call_id=tool_id,
                )
            )

        updates: Dict[str, Any] = {"messages": tool_messages}
        if decision_card is not None:
            updates["decision_card"] = decision_card
        if pending_action is not None:
            updates["pending_action"] = pending_action

        return updates

    return tools_node
