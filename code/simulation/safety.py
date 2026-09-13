import logging
from datetime import datetime, timedelta
from typing import List, Optional

from code.models.domain import FinancialEvent, UserProfile
from code.simulation.ledger import DailyLedger
from code.simulation.recurrence import RecurringStream

logger = logging.getLogger("buy_or_wait.simulation.safety")


class SafetyEngine:
    """
    Decoupled Financial Safety Engine.
    Evaluates pure financial capacity:
    - compute_safe_amount: Maximum cash safe to disburse today without breaching minimum balance over 90 days.
    - find_earliest_full_payment_date: First date when full payment is safe without spending modifications.
    """

    @classmethod
    def compute_safe_amount(cls, ledger: DailyLedger, requested_amount: float) -> float:
        """
        Answers: 'What is the maximum cash that could safely leave today without breaching minimum balance
        over the next 90 days before optional spending changes?'
        Formula: max(0.0, min(requested_amount, ledger.min_headroom())), rounded to 2 decimal places.
        """
        headroom = ledger.min_headroom()
        safe = max(0.0, min(float(requested_amount), headroom))
        return round(safe, 2)

    @classmethod
    def find_earliest_full_payment_date(
        cls,
        user: UserProfile,
        recurring_streams: List[RecurringStream],
        future_events: List[FinancialEvent],
        request_date: str,
        requested_amount: float,
        days: int = 90,
        desired_completion_date: Optional[str] = None,
    ) -> str:
        """
        Scans each day d in [0, 90]. Tests if a single payment of requested_amount on date(request_date + d)
        is safe (balance >= min_balance for all subsequent days).
        Returns the first safe date in YYYY-MM-DD format.
        If no date is safe within the forecast period, returns empty string "".
        """
        start_dt = datetime.strptime(request_date, "%Y-%m-%d")
        target_end_dt = (
            datetime.strptime(desired_completion_date, "%Y-%m-%d")
            if desired_completion_date
            else None
        )
        req_amt = float(requested_amount)

        for d in range(days + 1):
            candidate_dt = start_dt + timedelta(days=d)
            candidate_date_str = candidate_dt.strftime("%Y-%m-%d")

            test_ledger = DailyLedger(
                user=user,
                request_date=request_date,
                days=days,
                recurring_streams=recurring_streams,
                future_events=future_events,
                candidate_payments=[(candidate_date_str, req_amt)],
            )

            cushion = (user.minimum_balance_to_keep * 0.005) if d > 0 else 0.0
            if target_end_dt and candidate_dt <= target_end_dt:
                end_idx = min(len(test_ledger.dates) - 1, (target_end_dt - start_dt).days)
            elif target_end_dt:
                # Post-deadline deferred payment: must remain safe across subsequent 30-day cycle
                end_idx = min(len(test_ledger.dates) - 1, d + 30)
            else:
                end_idx = len(test_ledger.dates) - 1

            is_safe_candidate = all(
                b >= (user.minimum_balance_to_keep + cushion) for b in test_ledger.balances[d : end_idx + 1]
            )

            if is_safe_candidate:
                logger.debug(f"Found earliest safe full payment date: {candidate_date_str} (day {d})")
                return candidate_date_str

        logger.debug(f"No safe date for full payment of {requested_amount} within {days} days.")
        return ""


# Module-level convenience functions
def compute_safe_amount(ledger: DailyLedger, requested_amount: float) -> float:
    return SafetyEngine.compute_safe_amount(ledger, requested_amount)


def find_earliest_full_payment_date(
    user: UserProfile,
    recurring_streams: List[RecurringStream],
    future_events: List[FinancialEvent],
    request_date: str,
    requested_amount: float,
    days: int = 90,
    desired_completion_date: Optional[str] = None,
) -> str:
    return SafetyEngine.find_earliest_full_payment_date(
        user=user,
        recurring_streams=recurring_streams,
        future_events=future_events,
        request_date=request_date,
        requested_amount=requested_amount,
        days=days,
        desired_completion_date=desired_completion_date,
    )
