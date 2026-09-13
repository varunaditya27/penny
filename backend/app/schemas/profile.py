from typing import List, Optional
from pydantic import BaseModel, ConfigDict


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


class UserProfileUpdate(BaseModel):
    minimum_balance_to_keep: Optional[float] = None
    financial_priorities: Optional[List[str]] = None
    expense_categories_to_protect: Optional[List[str]] = None
    expense_categories_to_reduce: Optional[List[str]] = None
    expense_categories_to_stop: Optional[List[str]] = None
    payment_methods_user_will_consider: Optional[List[str]] = None
    max_installment_months: Optional[int] = None
