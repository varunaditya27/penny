import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict
from langchain_core.messages import AIMessage, HumanMessage

from backend.app.schemas.chat import ChatStreamRequest, StreamEventType

logger = logging.getLogger("penny.api.chat.events")


def format_sse(event: StreamEventType, data: Any) -> str:
    """
    Formats an SSE message block adhering to W3C Server-Sent Events standard.
    """
    payload = json.dumps(data) if not isinstance(data, str) else json.dumps({"message": data})
    return f"event: {event.value}\ndata: {payload}\n\n"


async def generate_chat_stream(
    agent: Any,
    request: ChatStreamRequest,
    session_id: str,
) -> AsyncGenerator[str, None]:
    """
    Async generator yielding real-time SSE events from the LangGraph agent execution.
    Delivers status updates, tool invocations, token streams, decision cards, and approval gates.
    """
    yield format_sse(StreamEventType.STATUS, {"status": "started", "message": "Analyzing request..."})

    state: Dict[str, Any] = {
        "messages": [HumanMessage(content=request.message)],
        "user_id": request.user_id,
    }
    config = {"configurable": {"thread_id": session_id}}

    try:
        async for chunk in agent.astream(state, config=config, stream_mode="updates"):
            for node_name, updates in chunk.items():
                if node_name == "agent":
                    messages = updates.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, AIMessage):
                            # Check tool calls
                            if msg.tool_calls:
                                for tc in msg.tool_calls:
                                    yield format_sse(
                                        StreamEventType.TOOL_CALL,
                                        {"tool": tc["name"], "args": tc["args"]},
                                    )
                                    yield format_sse(
                                        StreamEventType.STATUS,
                                        {"status": "executing_tool", "tool": tc["name"]},
                                    )
                            # Check text tokens
                            if msg.content:
                                text_content = (
                                    msg.content
                                    if isinstance(msg.content, str)
                                    else "".join(
                                        [b.get("text", "") if isinstance(b, dict) else str(b) for b in msg.content]
                                    )
                                )
                                yield format_sse(
                                    StreamEventType.TOKEN,
                                    {"content": text_content, "delta": text_content},
                                )

                elif node_name == "tools":
                    yield format_sse(
                        StreamEventType.STATUS,
                        {"status": "tools_completed", "message": "Simulations completed."},
                    )
                    decision_card = updates.get("decision_card")
                    if decision_card:
                        yield format_sse(StreamEventType.DECISION_CARD, decision_card)

                    pending_action = updates.get("pending_action")
                    if pending_action:
                        yield format_sse(StreamEventType.APPROVAL_REQUIRED, pending_action)

                elif node_name == "approval":
                    messages = updates.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, AIMessage) and msg.content:
                            text_content = (
                                msg.content
                                if isinstance(msg.content, str)
                                else "".join(
                                    [b.get("text", "") if isinstance(b, dict) else str(b) for b in msg.content]
                                )
                            )
                            yield format_sse(
                                StreamEventType.TOKEN,
                                {"content": text_content, "delta": text_content},
                            )

        yield format_sse(
            StreamEventType.DONE,
            {"session_id": session_id, "user_id": request.user_id, "status": "completed"},
        )

    except asyncio.CancelledError:
        logger.info("SSE client disconnected from session %s", session_id)
        raise
    except Exception as exc:
        logger.exception("Error during agent stream execution: %s", exc)
        yield format_sse(StreamEventType.ERROR, {"error": str(exc)})
