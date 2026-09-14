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
        baseline_ledger: Optional[DailyLedger] = None,
    ) -> str:
        """
        Scans each day d in [0, 90]. Tests if a single payment of requested_amount on date(request_date + d)
        is safe (balance >= min_balance for all subsequent days).
        Returns the first safe date in YYYY-MM-DD format.
        If no date is safe within the forecast period, returns empty string "".
        """
        if baseline_ledger is None:
            baseline_ledger = DailyLedger(
                user=user,
                request_date=request_date,
                days=days,
                recurring_streams=recurring_streams,
                future_events=future_events,
            )

        balances = baseline_ledger.balances
        dates = baseline_ledger.dates
        n = len(balances)
        if n == 0:
            return ""

        min_bal = float(user.minimum_balance_to_keep)
        req_amt = float(requested_amount)

        # Suffix-minimum array: suffix_min[i] = min(balances[i:])
        suffix_min = [0.0] * n
        suffix_min[-1] = balances[-1]
        for i in range(n - 2, -1, -1):
            suffix_min[i] = min(balances[i], suffix_min[i + 1])

        limit = min(days + 1, n)
        for d in range(limit):
            # If baseline balance on day d is already below min_bal,
            # no subsequent day can ever be safe since day d was breached before candidate payment
            if balances[d] < min_bal:
                break
            if round(suffix_min[d] - req_amt, 2) >= min_bal:
                candidate_date_str = dates[d]
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
    baseline_ledger: Optional[DailyLedger] = None,
) -> str:
    return SafetyEngine.find_earliest_full_payment_date(
        user=user,
        recurring_streams=recurring_streams,
        future_events=future_events,
        request_date=request_date,
        requested_amount=requested_amount,
        days=days,
        desired_completion_date=desired_completion_date,
        baseline_ledger=baseline_ledger,
    )
