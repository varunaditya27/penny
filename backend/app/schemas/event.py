from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class FinancialEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    user_id: str
    event_type: str
    description: str
    category: str
    direction: str
    amount: Optional[float] = None
    currency: str
    event_date: str
    settlement_date: Optional[str] = None
    status: str
    linked_event_id: Optional[str] = None
    flexibility: str = "fixed"
    minimum_allowed_amount: Optional[float] = None


class FinancialEventCreate(BaseModel):
    event_id: Optional[str] = None
    event_type: str
    description: str
    category: str
    direction: str = Field(..., pattern="^(debit|credit)$")
    amount: Optional[float] = None
    currency: str
    event_date: str
    settlement_date: Optional[str] = None
    status: str = "settled"
    linked_event_id: Optional[str] = None
    flexibility: str = "fixed"
    minimum_allowed_amount: Optional[float] = None
