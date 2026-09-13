from typing import List

from backend.app.db.models import UserDB
from backend.app.schemas.profile import CashFlowRiskMetrics
from backend.app.services.mappers import map_events_to_domain
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
    def compute_risk_metrics(cls, user_db: UserDB) -> CashFlowRiskMetrics:
        domain_events: List[FinancialEvent] = map_events_to_domain(user_db.events)
        detector = RecurrenceDetector()
        streams = detector.detect_streams(domain_events)

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
