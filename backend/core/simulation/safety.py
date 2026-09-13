import logging
from datetime import datetime, timedelta
from typing import List, Optional

from backend.core.models.domain import FinancialEvent, UserProfile
from backend.core.simulation.ledger import DailyLedger
from backend.core.simulation.recurrence import RecurringStream

logger = logging.getLogger("buy_or_wait.simulation.safety")


class SafetyEngine:
    """
    Decoupled Financial Safety Engine.
    Evaluates pure financial capacity:
    - compute_safe_amount: Maximum cash safe to disburse today without breaching minimum balance over 90 days.
    - find_earliest_full_payment_date: First date when full payment is safe without spending modifications.
    """

    @classmethod
    def compute_safe_amount(
        cls, ledger: DailyLedger, requested_amount: float, limit_days: Optional[int] = None
    ) -> float:
        """
        Answers: 'What is the maximum cash that could safely leave today without breaching minimum balance
        over the forecast horizon before optional spending changes?'
        Formula: max(0.0, min(requested_amount, headroom)), rounded to 2 decimal places.
        """
        if limit_days is not None and limit_days > 0:
            effective_balances = ledger.balances[: min(limit_days, len(ledger.balances))]
            headroom = min(b - ledger.user.minimum_balance_to_keep for b in effective_balances)
        else:
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

            # The challenge requires safety at every point in the full 90-day forecast.
            # Do not shorten this window to the requested completion date or invent an
            # additional cushion: either changes the contract's definition of safe.
            is_safe_candidate = test_ledger.is_safe()

            if is_safe_candidate:
                logger.debug(f"Found earliest safe full payment date: {candidate_date_str} (day {d})")
                return candidate_date_str

        logger.debug(f"No safe date for full payment of {requested_amount} within {days} days.")
        return ""


# Module-level convenience functions
def compute_safe_amount(
    ledger: DailyLedger, requested_amount: float, limit_days: Optional[int] = None
) -> float:
    return SafetyEngine.compute_safe_amount(ledger, requested_amount, limit_days)


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
