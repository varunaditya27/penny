from dataclasses import dataclass, field
from typing import Optional, List, Set


class CurrencyEnum:
    """Strict 5-currency enum validator to prevent catastrophic IDR vs INR confusion."""
    ALLOWED: Set[str] = {"INR", "IDR", "ZAR", "EUR", "USD"}

    @classmethod
    def validate(cls, currency: str) -> str:
        if not currency or not isinstance(currency, str):
            raise ValueError(f"Currency must be a non-empty string, got {repr(currency)}")
        cleaned = currency.strip()
        if cleaned not in cls.ALLOWED:
            raise ValueError(f"Invalid currency '{cleaned}'. Allowed currencies: {cls.ALLOWED}")
        return cleaned


@dataclass(frozen=True)
class UserProfile:
    user_id: str
    home_currency: str
    current_available_balance: float
    minimum_balance_to_keep: float
    financial_priorities: List[str] = field(default_factory=list)
    expense_categories_to_protect: Set[str] = field(default_factory=set)
    expense_categories_user_is_willing_to_reduce: Set[str] = field(default_factory=set)
    expense_categories_user_is_willing_to_stop: Set[str] = field(default_factory=set)
    payment_methods_user_will_consider: Set[str] = field(default_factory=set)
    max_installment_months: Optional[int] = None

    def __post_init__(self):
        CurrencyEnum.validate(self.home_currency)

    @property
    def headroom(self) -> float:
        return self.current_available_balance - self.minimum_balance_to_keep

    def considers_method(self, method: str) -> bool:
        return method in self.payment_methods_user_will_consider

    def is_category_protected(self, category: str) -> bool:
        return category in self.expense_categories_to_protect

    def can_reduce_category(self, category: str) -> bool:
        return (not self.is_category_protected(category)) and (
            category in self.expense_categories_user_is_willing_to_reduce
        )

    def can_stop_category(self, category: str) -> bool:
        return (not self.is_category_protected(category)) and (
            category in self.expense_categories_user_is_willing_to_stop
        )


@dataclass(frozen=True)
class PurchaseRequest:
    request_id: str
    user_id: str
    request_date: str
    request_type: str
    requested_amount: float
    desired_completion_date: str
    allows_partial_payment: bool
    request_text: str


@dataclass
class FinancialEvent:
    event_id: str
    user_id: str
    event_type: str
    description: str
    category: str
    direction: str
    amount: Optional[float]
    currency: str
    event_date: str
    settlement_date: str
    status: str
    linked_event_id: str = ""
    flexibility: str = "fixed"
    minimum_allowed_amount: Optional[float] = None

    def __post_init__(self):
        if self.currency:
            CurrencyEnum.validate(self.currency)

    @property
    def is_credit(self) -> bool:
        return self.direction == "credit"

    @property
    def is_debit(self) -> bool:
        return self.direction == "debit"

    @property
    def is_non_cash(self) -> bool:
        return self.direction == "non_cash" or self.status == "unrealized"


@dataclass(frozen=True)
class PaymentOption:
    payment_option_id: str
    request_id: str
    payment_method: str
    payment_amount: float
    number_of_payments: int
    first_payment_date: str
    payment_frequency_days: Optional[int]
    financing_fee: float
    total_payable_amount: float
