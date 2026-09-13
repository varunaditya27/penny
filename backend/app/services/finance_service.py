import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.db.models import DecisionRecordDB, FinancialEventDB, PaymentOptionDB, UserDB
from backend.app.schemas.affordability import (
    AffordabilityRequest,
    AffordabilityResponse,
    PaymentScheduleItem,
    SpendingChangeItem,
)
from backend.app.schemas.profile import CashFlowRiskMetrics, UserProfileResponse, UserProfileUpdate
from backend.core.models.domain import FinancialEvent, PaymentOption, PurchaseRequest, UserProfile
from backend.core.pipeline import DecisionPipeline
from backend.core.simulation.recurrence import RecurrenceDetector

logger = logging.getLogger("penny.services.finance")


class FinanceService:
    def __init__(self, db: Session):
        self.db = db
        self.pipeline = DecisionPipeline(use_llm=False)

    def get_user(self, user_id: str) -> Optional[UserDB]:
        return self.db.query(UserDB).filter_by(user_id=user_id).first()

    def update_user(self, user: UserDB, update_in: UserProfileUpdate) -> UserDB:
        if update_in.minimum_balance_to_keep is not None:
            user.minimum_balance_to_keep = update_in.minimum_balance_to_keep
        if update_in.financial_priorities is not None:
            user.financial_priorities = "|".join(update_in.financial_priorities)
        if update_in.expense_categories_to_protect is not None:
            user.expense_categories_to_protect = "|".join(update_in.expense_categories_to_protect)
        if update_in.expense_categories_to_reduce is not None:
            user.expense_categories_to_reduce = "|".join(update_in.expense_categories_to_reduce)
        if update_in.expense_categories_to_stop is not None:
            user.expense_categories_to_stop = "|".join(update_in.expense_categories_to_stop)
        if update_in.payment_methods_user_will_consider is not None:
            user.payment_methods_user_will_consider = "|".join(update_in.payment_methods_user_will_consider)
        if update_in.max_installment_months is not None:
            user.max_installment_months = update_in.max_installment_months

        self.db.commit()
        self.db.refresh(user)
        return user

    def map_user_to_response(
        self, user: UserDB, risk_metrics: Optional[CashFlowRiskMetrics] = None
    ) -> UserProfileResponse:
        return UserProfileResponse(
            user_id=user.user_id,
            home_currency=user.home_currency,
            current_available_balance=user.current_available_balance,
            minimum_balance_to_keep=user.minimum_balance_to_keep,
            financial_priorities=user.financial_priorities.split("|") if user.financial_priorities else [],
            expense_categories_to_protect=user.expense_categories_to_protect.split("|") if user.expense_categories_to_protect else [],
            expense_categories_to_reduce=user.expense_categories_to_reduce.split("|") if user.expense_categories_to_reduce else [],
            expense_categories_to_stop=user.expense_categories_to_stop.split("|") if user.expense_categories_to_stop else [],
            payment_methods_user_will_consider=user.payment_methods_user_will_consider.split("|") if user.payment_methods_user_will_consider else [],
            max_installment_months=user.max_installment_months,
            risk_metrics=risk_metrics,
        )

    def compute_user_risk_metrics(self, user_db: UserDB) -> CashFlowRiskMetrics:
        """
        Calculates normalized cash-flow risk metrics based on discovered recurring streams:
        - monthly_fixed_burn_rate: committed monthly living expenses
        - monthly_confirmed_income: confirmed salary / employment credits
        - fixed_cost_ratio: committed expenses / confirmed income
        - discretionary_cashflow: surplus cash remaining
        """
        domain_events = self.map_events_to_domain(user_db.events)
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

    def map_user_to_domain(self, user_db: UserDB) -> UserProfile:
        return UserProfile(
            user_id=user_db.user_id,
            home_currency=user_db.home_currency,
            current_available_balance=user_db.current_available_balance,
            minimum_balance_to_keep=user_db.minimum_balance_to_keep,
            financial_priorities=user_db.financial_priorities.split("|") if user_db.financial_priorities else [],
            expense_categories_to_protect=user_db.expense_categories_to_protect.split("|") if user_db.expense_categories_to_protect else [],
            expense_categories_user_is_willing_to_reduce=user_db.expense_categories_to_reduce.split("|") if user_db.expense_categories_to_reduce else [],
            expense_categories_user_is_willing_to_stop=user_db.expense_categories_to_stop.split("|") if user_db.expense_categories_to_stop else [],
            payment_methods_user_will_consider=user_db.payment_methods_user_will_consider.split("|") if user_db.payment_methods_user_will_consider else [],
            max_installment_months=user_db.max_installment_months,
        )

    _map_user = map_user_to_domain

    def map_events_to_domain(self, events_db: List[FinancialEventDB]) -> List[FinancialEvent]:
        return [
            FinancialEvent(
                event_id=e.event_id,
                user_id=e.user_id,
                event_type=e.event_type,
                description=e.description,
                category=e.category,
                direction=e.direction,
                amount=e.amount,
                currency=e.currency,
                event_date=e.event_date,
                settlement_date=e.settlement_date,
                status=e.status,
                linked_event_id=e.linked_event_id,
                flexibility=e.flexibility,
                minimum_allowed_amount=e.minimum_allowed_amount,
            )
            for e in events_db
        ]

    _map_events = map_events_to_domain

    def map_options_to_domain(self, options_db: List[PaymentOptionDB]) -> List[PaymentOption]:
        return [
            PaymentOption(
                payment_option_id=o.payment_option_id,
                request_id=o.request_id,
                payment_method=o.payment_method,
                payment_amount=o.payment_amount,
                number_of_payments=o.number_of_payments,
                first_payment_date=o.first_payment_date,
                payment_frequency_days=o.payment_frequency_days,
                financing_fee=o.financing_fee,
                total_payable_amount=o.total_payable_amount,
            )
            for o in options_db
        ]

    _map_options = map_options_to_domain

    def parse_payment_schedule(self, payment_plan_str: str) -> List[PaymentScheduleItem]:
        if not payment_plan_str or payment_plan_str.strip() in ["none", ""]:
            return []
        items = []
        for entry in payment_plan_str.split("|"):
            parts = entry.strip().split(":")
            if len(parts) == 2:
                try:
                    items.append(PaymentScheduleItem(date=parts[0], amount=float(parts[1])))
                except ValueError:
                    continue
        return items

    def parse_spending_changes(self, spending_str: str) -> List[SpendingChangeItem]:
        if not spending_str or spending_str.strip() in ["none", ""]:
            return []
        changes = []
        for entry in spending_str.split("|"):
            parts = entry.strip().split(":")
            if parts[0] == "stop" and len(parts) >= 2:
                changes.append(SpendingChangeItem(action="stop", event_id=parts[1]))
            elif parts[0] == "reduce_to" and len(parts) >= 3:
                try:
                    changes.append(SpendingChangeItem(action="reduce_to", event_id=parts[1], amount=float(parts[2])))
                except ValueError:
                    continue
        return changes

    def evaluate_affordability(self, request_in: AffordabilityRequest, save_decision: bool = True) -> AffordabilityResponse:
        user_db = self.get_user(request_in.user_id)
        if not user_db:
            raise ValueError(f"User '{request_in.user_id}' not found.")

        req_id = request_in.request_id or f"req_{uuid.uuid4().hex[:8]}"
        req_date = request_in.request_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        domain_user = self.map_user_to_domain(user_db)
        domain_events = self.map_events_to_domain(user_db.events)

        # Resolve payment options: inline provided options, or query seeded options if request_id supplied
        domain_options: List[PaymentOption] = []
        if request_in.payment_options:
            for idx, opt_in in enumerate(request_in.payment_options):
                domain_options.append(
                    PaymentOption(
                        payment_option_id=opt_in.payment_option_id or f"{req_id}_opt_{idx + 1}",
                        request_id=req_id,
                        payment_method=opt_in.payment_method,
                        payment_amount=opt_in.payment_amount,
                        number_of_payments=opt_in.number_of_payments,
                        first_payment_date=opt_in.first_payment_date,
                        payment_frequency_days=opt_in.payment_frequency_days,
                        financing_fee=opt_in.financing_fee,
                        total_payable_amount=opt_in.total_payable_amount,
                    )
                )
        elif request_in.request_id:
            db_opts = self.db.query(PaymentOptionDB).filter_by(request_id=request_in.request_id).all()
            domain_options = self.map_options_to_domain(db_opts)

        purchase_request = PurchaseRequest(
            request_id=req_id,
            user_id=request_in.user_id,
            request_date=req_date,
            request_type="purchase",
            requested_amount=request_in.requested_amount,
            desired_completion_date=request_in.desired_completion_date,
            allows_partial_payment=request_in.allows_partial_payment,
            request_text=request_in.request_text or "",
        )

        output_row = self.pipeline.process_request(
            request=purchase_request,
            user=domain_user,
            user_events=domain_events,
            payment_options=domain_options,
        )

        if save_decision:
            rec = DecisionRecordDB(
                request_id=req_id,
                user_id=request_in.user_id,
                amount_safe_to_pay=output_row.amount_safe_to_pay,
                affordability_status=output_row.affordability_status,
                recommended_payment_method=output_row.recommended_payment_method,
                payment_plan=output_row.payment_plan,
                earliest_date_for_full_payment=output_row.earliest_date_for_full_payment or None,
                spending_changes_needed=output_row.spending_changes_needed,
                decision_explanation=output_row.decision_explanation,
            )
            self.db.add(rec)
            self.db.commit()

        schedule = self.parse_payment_schedule(output_row.payment_plan)
        changes = self.parse_spending_changes(output_row.spending_changes_needed)

        return AffordabilityResponse(
            request_id=req_id,
            user_id=request_in.user_id,
            amount_safe_to_pay=output_row.amount_safe_to_pay,
            affordability_status=output_row.affordability_status,
            recommended_payment_method=output_row.recommended_payment_method,
            payment_plan=output_row.payment_plan,
            payment_schedule=schedule,
            earliest_date_for_full_payment=output_row.earliest_date_for_full_payment or None,
            spending_changes_needed=output_row.spending_changes_needed,
            spending_changes=changes,
            decision_explanation=output_row.decision_explanation,
        )
