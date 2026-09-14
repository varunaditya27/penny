from typing import List, Optional

from backend.app.db.models import UserDB
from backend.app.schemas.profile import CashFlowRiskMetrics
from backend.app.services.mappers import map_events_to_domain
from backend.core.data.currency import ExchangeRateConverter
from backend.core.models.domain import FinancialEvent
from backend.core.simulation.recurrence import RecurrenceDetector


class CashFlowRiskService:
    """
    Computes cash-flow risk & underwriting metrics from recurring financial events:
    - monthly_fixed_burn_rate: committed monthly living expenses
    - monthly_confirmed_income: confirmed recurring payroll / employment credits
    - fixed_cost_ratio: ratio of committed expenses to confirmed income
    - discretionary_cashflow: surplus cash remaining each month
    """

    @classmethod
    def compute_risk_metrics(
        cls,
        events: Optional[object] = None,
        user_db: Optional[UserDB] = None,
        home_currency: Optional[str] = None,
        converter: Optional[ExchangeRateConverter] = None,
    ) -> CashFlowRiskMetrics:
        """
        Accepts either pure domain events + home_currency, or a UserDB instance for backward compatibility.
        Filters out non-cash and non-settled transactions, and normalizes foreign currencies.
        """
        if isinstance(events, UserDB):
            user_db = events
            events = None

        if events is None and user_db is not None:
            events = map_events_to_domain(user_db.events)
            if home_currency is None:
                home_currency = user_db.home_currency

        if events is None:
            events = []

        # Filter out non-cash or non-settled events to avoid distorted burn rates
        valid_events = [e for e in events if e.status == "settled" and not e.is_non_cash]

        # Normalize currencies if converter provided
        if converter and home_currency:
            normalized_events: List[FinancialEvent] = []
            for ev in valid_events:
                if ev.currency != home_currency and ev.amount is not None:
                    converted_amt = converter.convert(
                        amount=ev.amount,
                        from_currency=ev.currency,
                        to_currency=home_currency,
                        as_of_date=ev.event_date,
                    )
                    normalized_events.append(
                        FinancialEvent(
                            event_id=ev.event_id,
                            user_id=ev.user_id,
                            event_type=ev.event_type,
                            description=ev.description,
                            category=ev.category,
                            direction=ev.direction,
                            amount=converted_amt,
                            currency=home_currency,
                            event_date=ev.event_date,
                            settlement_date=ev.settlement_date,
                            status=ev.status,
                            linked_event_id=ev.linked_event_id,
                            flexibility=ev.flexibility,
                            minimum_allowed_amount=ev.minimum_allowed_amount,
                        )
                    )
                else:
                    normalized_events.append(ev)
            valid_events = normalized_events

        detector = RecurrenceDetector()
        streams = detector.detect_streams(valid_events)

        monthly_burn = 0.0
        monthly_income = 0.0

        for s in streams:
            if s.cadence_type == "dom":
                monthly_amt = s.baseline_amount
            elif s.cadence_type == "step" and s.step_days and s.step_days > 0:
                monthly_amt = s.baseline_amount * (30.0 / s.step_days)
            else:
                monthly_amt = s.baseline_amount

            if s.is_credit:
                monthly_income += monthly_amt
            else:
                monthly_burn += monthly_amt

        ratio = round((monthly_burn / monthly_income), 4) if monthly_income > 0 else 0.0
        discretionary = round(monthly_income - monthly_burn, 2)

        return CashFlowRiskMetrics(
            monthly_fixed_burn_rate=round(monthly_burn, 2),
            monthly_confirmed_income=round(monthly_income, 2),
            fixed_cost_ratio=ratio,
            discretionary_cashflow=discretionary,
        )
