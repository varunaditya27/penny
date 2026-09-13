import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.db.models import DecisionRecordDB, PaymentOptionDB, UserDB
from backend.app.schemas.affordability import AffordabilityRequest, AffordabilityResponse
from backend.app.schemas.profile import CashFlowRiskMetrics, UserProfileResponse, UserProfileUpdate
from backend.app.services.mappers import (
    map_events_to_domain,
    map_options_to_domain,
    map_user_to_domain,
    map_user_to_response,
    parse_payment_schedule,
    parse_spending_changes,
)
from backend.app.services.risk_service import CashFlowRiskService
from backend.core.models.domain import PaymentOption, PurchaseRequest
from backend.core.pipeline import DecisionPipeline

logger = logging.getLogger("penny.services.finance")


class FinanceService:
    """
    Coordinates user financial profile persistence and purchase
    affordability evaluation against the forward simulation engine.
    """

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
        return map_user_to_response(user, risk_metrics)

    def compute_user_risk_metrics(self, user_db: UserDB) -> CashFlowRiskMetrics:
        return CashFlowRiskService.compute_risk_metrics(user_db)

    # Static compatibility aliases for callers and existing tests
    map_user_to_domain = staticmethod(map_user_to_domain)
    _map_user = staticmethod(map_user_to_domain)
    map_events_to_domain = staticmethod(map_events_to_domain)
    _map_events = staticmethod(map_events_to_domain)
    map_options_to_domain = staticmethod(map_options_to_domain)
    _map_options = staticmethod(map_options_to_domain)
    parse_payment_schedule = staticmethod(parse_payment_schedule)
    parse_spending_changes = staticmethod(parse_spending_changes)

    def evaluate_affordability(
        self, request_in: AffordabilityRequest, save_decision: bool = True
    ) -> AffordabilityResponse:
        user_db = self.get_user(request_in.user_id)
        if not user_db:
            raise ValueError(f"User '{request_in.user_id}' not found.")

        req_id = request_in.request_id or f"req_{uuid.uuid4().hex[:8]}"
        req_date = request_in.request_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        domain_user = map_user_to_domain(user_db)
        domain_events = map_events_to_domain(user_db.events)

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
            domain_options = map_options_to_domain(db_opts)

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

        schedule = parse_payment_schedule(output_row.payment_plan)
        changes = parse_spending_changes(output_row.spending_changes_needed)

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
