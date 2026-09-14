import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

from backend.app.agent.graph import create_penny_agent
from backend.app.api.deps import get_checkpointer, get_db, verify_user_access
from backend.app.api.v1.chat.events import generate_chat_stream
from backend.app.db.models import UserDB
from backend.app.schemas.chat import (
    ChatApprovalRequest,
    ChatApprovalResponse,
    ChatStreamRequest,
)

router = APIRouter()


@router.post("/stream", summary="Stream conversational financial assistant responses via SSE")
async def stream_chat(
    request: ChatStreamRequest,
    db: Session = Depends(get_db),
    checkpointer=Depends(get_checkpointer),
    _authorized: bool = Depends(verify_user_access),
):
    """
    Initiates a streaming chat session with Penny.
    Emits real-time Server-Sent Events (SSE) including status indicators,
    tool execution logs, token streams, and rich decision cards.
    """
    user = db.query(UserDB).filter_by(user_id=request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{request.user_id}' not found.",
        )

    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    agent = create_penny_agent(db, checkpointer=checkpointer)

    return StreamingResponse(
        generate_chat_stream(agent, request, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/approve", response_model=ChatApprovalResponse, summary="Submit Human-in-the-Loop decision approval")
def approve_pending_action(
    request: ChatApprovalRequest,
    db: Session = Depends(get_db),
    checkpointer=Depends(get_checkpointer),
    _authorized: bool = Depends(verify_user_access),
):
    """
    Submits user approval or rejection for a pending budget modification.
    Updates the agent's checkpointed state for the given session.
    """
    user = db.query(UserDB).filter_by(user_id=request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{request.user_id}' not found.",
        )

    agent = create_penny_agent(db, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": request.session_id}}

    state = agent.get_state(config)
    if not state or not state.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active session found with session_id '{request.session_id}'.",
        )

    pending_action = state.values.get("pending_action")
    if pending_action and request.action_id and pending_action.get("action_id") != request.action_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action ID '{request.action_id}' does not match pending action '{pending_action.get('action_id')}'.",
        )

    category = pending_action.get("category", "expenses") if pending_action else "expenses"
    decision_label = "approved" if request.approved else "declined"
    feedback_note = f" Feedback: {request.feedback}" if request.feedback else ""
    ack_msg = HumanMessage(
        content=f"User decision: {decision_label.capitalize()} spending modification for {category}.{feedback_note}"
    )

    try:
        agent.update_state(
            config=config,
            values={
                "action_approved": request.approved,
                "pending_action": None,
                "messages": [ack_msg],
            },
            as_node="approval",
        )
        return ChatApprovalResponse(
            status="success",
            session_id=request.session_id,
            message=f"Budget modification action {decision_label} successfully.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update approval state: {str(exc)}",
        )
