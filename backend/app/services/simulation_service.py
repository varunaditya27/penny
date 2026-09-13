from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.db.models import UserDB
from backend.app.schemas.simulation import TrajectoryPoint, TrajectoryResponse
from backend.app.services.mappers import map_events_to_domain, map_user_to_domain
from backend.core.simulation.ledger import DailyLedger
from backend.core.simulation.recurrence import RecurrenceDetector


class SimulationService:
    def __init__(self, db: Session):
        self.db = db

    def compute_user_trajectory(
        self,
        user_id: str,
        prospective_amount: Optional[float] = None,
        start_date: Optional[str] = None,
        days: int = 90,
    ) -> TrajectoryResponse:
        user_db = self.db.query(UserDB).filter_by(user_id=user_id).first()
        if not user_db:
            raise ValueError(f"User '{user_id}' not found.")

        domain_user = map_user_to_domain(user_db)
        domain_events = map_events_to_domain(user_db.events)

        eval_date = start_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        hist_events = [e for e in domain_events if e.event_date <= eval_date]
        future_events = [e for e in domain_events if e.event_date > eval_date]

        detector = RecurrenceDetector()
        recurring_streams = detector.detect_streams(hist_events)

        # Baseline ledger
        base_ledger = DailyLedger(
            user=domain_user,
            request_date=eval_date,
            days=days,
            recurring_streams=recurring_streams,
            future_events=future_events,
        )
        baseline_balances = base_ledger.balances

        with_purchase_balances = None
        if prospective_amount and prospective_amount > 0:
            purchase_ledger = DailyLedger(
                user=domain_user,
                request_date=eval_date,
                days=days,
                recurring_streams=recurring_streams,
                future_events=future_events,
                candidate_payments={eval_date: prospective_amount},
            )
            with_purchase_balances = purchase_ledger.balances

        dt_start = datetime.strptime(eval_date, "%Y-%m-%d")
        points = []
        lowest_balance = float("inf")
        lowest_balance_date = eval_date

        for i in range(days + 1):
            day_str = (dt_start + timedelta(days=i)).strftime("%Y-%m-%d")
            base_bal = baseline_balances[i] if i < len(baseline_balances) else baseline_balances[-1]
            purch_bal = None
            if with_purchase_balances is not None:
                purch_bal = with_purchase_balances[i] if i < len(with_purchase_balances) else with_purchase_balances[-1]
                if purch_bal < lowest_balance:
                    lowest_balance = purch_bal
                    lowest_balance_date = day_str
            else:
                if base_bal < lowest_balance:
                    lowest_balance = base_bal
                    lowest_balance_date = day_str

            points.append(
                TrajectoryPoint(
                    date=day_str,
                    baseline_balance=round(base_bal, 2),
                    with_purchase_balance=round(purch_bal, 2) if purch_bal is not None else None,
                )
            )

        is_safe = lowest_balance >= domain_user.minimum_balance_to_keep
        buffer_margin = round(lowest_balance - domain_user.minimum_balance_to_keep, 2)

        return TrajectoryResponse(
            user_id=user_id,
            currency=domain_user.home_currency,
            minimum_balance_to_keep=domain_user.minimum_balance_to_keep,
            points=points,
            lowest_projected_balance=round(lowest_balance, 2),
            lowest_balance_date=lowest_balance_date,
            buffer_margin=buffer_margin,
            is_safe=is_safe,
        )
