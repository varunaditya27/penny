from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class StreamEventType(str, Enum):
    STATUS = "status"
    TOKEN = "token"
    TOOL_CALL = "tool_call"
    DECISION_CARD = "decision_card"
    APPROVAL_REQUIRED = "approval_required"
    DONE = "done"
    ERROR = "error"


class ChatStreamRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="Identifier of the requesting user")
    message: str = Field(..., min_length=1, description="User conversational input message")
    session_id: Optional[str] = Field(None, description="Persistent conversational thread ID")


class ChatApprovalRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="Identifier of the requesting user")
    session_id: str = Field(..., min_length=1, description="Conversational thread ID")
    approved: bool = Field(..., description="Whether user approves the pending modification")
    action_id: Optional[str] = Field(None, description="ID of the pending action")
    feedback: Optional[str] = Field(None, description="Optional user commentary")


class ChatApprovalResponse(BaseModel):
    status: str
    session_id: str
    message: str
