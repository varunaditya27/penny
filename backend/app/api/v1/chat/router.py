import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.agent.graph import create_penny_agent
from backend.app.api.deps import get_db, verify_user_access
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
    agent = create_penny_agent(db)

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

    agent = create_penny_agent(db)
    config = {"configurable": {"thread_id": request.session_id}}

    try:
        # Update state with user approval decision
        agent.update_state(
            config=config,
            values={"action_approved": request.approved},
            as_node="approval",
        )
        decision_label = "approved" if request.approved else "declined"
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
