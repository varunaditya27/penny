from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CashFlowRiskMetrics(BaseModel):
    monthly_fixed_burn_rate: float = Field(..., description="Estimated monthly fixed living commitments")
    monthly_confirmed_income: float = Field(..., description="Confirmed recurring monthly income")
    fixed_cost_ratio: float = Field(..., description="Percentage of income locked into fixed commitments")
    discretionary_cashflow: float = Field(..., description="Estimated discretionary surplus remaining each month")


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    home_currency: str
    current_available_balance: float
    minimum_balance_to_keep: float
    financial_priorities: List[str] = []
    expense_categories_to_protect: List[str] = []
    expense_categories_to_reduce: List[str] = []
    expense_categories_to_stop: List[str] = []
    payment_methods_user_will_consider: List[str] = []
    max_installment_months: Optional[int] = None
    risk_metrics: Optional[CashFlowRiskMetrics] = None


class UserProfileUpdate(BaseModel):
    minimum_balance_to_keep: Optional[float] = None
    financial_priorities: Optional[List[str]] = None
    expense_categories_to_protect: Optional[List[str]] = None
    expense_categories_to_reduce: Optional[List[str]] = None
    expense_categories_to_stop: Optional[List[str]] = None
    payment_methods_user_will_consider: Optional[List[str]] = None
    max_installment_months: Optional[int] = None
