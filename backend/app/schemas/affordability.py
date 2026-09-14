from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PaymentScheduleItem(BaseModel):
    date: str
    amount: float


class SpendingChangeItem(BaseModel):
    action: str  # "stop" or "reduce_to"
    event_id: str
    amount: Optional[float] = None


class PaymentOptionInput(BaseModel):
    payment_option_id: Optional[str] = None
    payment_method: str = Field(..., description="Payment method: full_payment or installments")
    payment_amount: float = Field(..., gt=0, description="Amount per installment or full payment")
    number_of_payments: int = Field(..., gt=0, description="Number of payments")
    first_payment_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="First payment date (YYYY-MM-DD)")
    payment_frequency_days: int = Field(..., gt=0, description="Cadence between payments in days")
    financing_fee: float = Field(0.0, ge=0, description="Additional financing or interest fee")
    total_payable_amount: float = Field(..., gt=0, description="Total amount payable over all installments")


class AffordabilityRequest(BaseModel):
    user_id: str
    requested_amount: float = Field(..., gt=0, lt=1e9, description="Total amount the user wants to spend")
    desired_completion_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Target completion date (YYYY-MM-DD)")
    request_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Evaluation date (defaults to today or dataset date)")
    allows_partial_payment: bool = Field(False, description="Whether the request permits paying in two split payments")
    request_text: Optional[str] = Field("", description="Optional user question or item description")
    request_id: Optional[str] = Field(None, description="Optional existing request ID to link with pre-seeded merchant payment options")
    payment_options: Optional[List[PaymentOptionInput]] = Field(None, description="Optional merchant financing options provided at checkout")


class AffordabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: str
    user_id: str
    amount_safe_to_pay: float
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str = Field(..., description="[Deprecated] Raw pipe-delimited payment schedule string")
    payment_schedule: List[PaymentScheduleItem] = []
    earliest_date_for_full_payment: Optional[str] = None
    spending_changes_needed: str = Field(..., description="[Deprecated] Raw pipe-delimited spending modification string")
    spending_changes: List[SpendingChangeItem] = []
    decision_explanation: str
