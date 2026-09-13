from dataclasses import dataclass
from typing import List, Dict, Any, Set


class AffordabilityStatus:
    AFFORDABLE_NOW = "affordable_now"
    AFFORDABLE_WITH_PLAN = "affordable_with_plan"
    AFFORDABLE_LATER = "affordable_later"
    NOT_AFFORDABLE = "not_affordable"
    ALLOWED: Set[str] = {
        AFFORDABLE_NOW,
        AFFORDABLE_WITH_PLAN,
        AFFORDABLE_LATER,
        NOT_AFFORDABLE,
    }


class PaymentMethod:
    FULL_PAYMENT = "full_payment"
    PARTIAL_PAYMENT = "partial_payment"
    INSTALLMENTS = "installments"
    WAIT = "wait"
    NOT_RECOMMENDED = "not_recommended"
    ALLOWED: Set[str] = {
        FULL_PAYMENT,
        PARTIAL_PAYMENT,
        INSTALLMENTS,
        WAIT,
        NOT_RECOMMENDED,
    }


@dataclass(frozen=True)
class CandidatePlan:
    payment_method: str
    payment_plan: str
    first_payment_date: str
    total_payable_amount: float
    number_of_payments: int
    spending_changes_needed: str = "none"
    payment_option_id: str = "none"
    completes_by_deadline: bool = True
    requires_spending_changes: bool = False
    affordability_status: str = AffordabilityStatus.AFFORDABLE_NOW
    earliest_date_for_full_payment: str = ""
    amount_safe_to_pay: float = 0.0

    @property
    def ranking_key(self):
        """
        6-Tier Tie-Breaker:
        1. Complete by desired_completion_date (False before True for violations)
        2. Require no spending changes (False before True)
        3. Minimize total amount paid (float)
        4. Start payment earlier (date string)
        5. Use fewer payments (int)
        6. Lowest payment_option_id
        """
        return (
            not self.completes_by_deadline,
            self.requires_spending_changes,
            round(self.total_payable_amount, 2),
            self.first_payment_date,
            self.number_of_payments,
            self.payment_option_id,
        )


@dataclass(frozen=True)
class OutputRow:
    request_id: str
    amount_safe_to_pay: float
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str
    earliest_date_for_full_payment: str
    spending_changes_needed: str
    decision_explanation: str

    def __post_init__(self):
        if self.affordability_status not in AffordabilityStatus.ALLOWED:
            raise ValueError(f"Invalid affordability_status: {self.affordability_status}")
        if self.recommended_payment_method not in PaymentMethod.ALLOWED:
            raise ValueError(f"Invalid recommended_payment_method: {self.recommended_payment_method}")

    def to_csv_row(self) -> List[str]:
        # Format amounts cleanly: if int, format without .0, otherwise with standard decimal
        amt_str = (
            f"{self.amount_safe_to_pay:.2f}".rstrip("0").rstrip(".")
            if isinstance(self.amount_safe_to_pay, float)
            else str(self.amount_safe_to_pay)
        )
        return [
            self.request_id,
            amt_str,
            self.affordability_status,
            self.recommended_payment_method,
            self.payment_plan,
            self.earliest_date_for_full_payment,
            self.spending_changes_needed,
            self.decision_explanation,
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "amount_safe_to_pay": self.amount_safe_to_pay,
            "affordability_status": self.affordability_status,
            "recommended_payment_method": self.recommended_payment_method,
            "payment_plan": self.payment_plan,
            "earliest_date_for_full_payment": self.earliest_date_for_full_payment,
            "spending_changes_needed": self.spending_changes_needed,
            "decision_explanation": self.decision_explanation,
        }
