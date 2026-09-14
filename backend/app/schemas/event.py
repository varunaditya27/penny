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
    direction: str = Field(..., pattern=r"^(debit|credit)$")
    amount: Optional[float] = Field(None, gt=0, lt=1e9)
    currency: str = Field(..., pattern=r"^(INR|IDR|ZAR|EUR|USD)$")
    event_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    settlement_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: str = Field("settled", pattern=r"^(settled|pending|projected|cancelled)$")
    linked_event_id: Optional[str] = None
    flexibility: str = Field("fixed", pattern=r"^(fixed|flexible)$")
    minimum_allowed_amount: Optional[float] = None
