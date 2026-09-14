import json
from typing import Any, Dict, List, Optional
from langchain_core.tools import BaseTool, tool
from sqlalchemy.orm import Session

from backend.app.schemas.affordability import AffordabilityRequest, PaymentOptionInput
from backend.app.services.finance_service import FinanceService
from backend.core.pipeline import DecisionPipeline


def create_evaluation_tool(db: Session, pipeline: Optional[DecisionPipeline] = None) -> BaseTool:
    finance_service = FinanceService(db, pipeline=pipeline)

    @tool
    def evaluate_purchase(
        user_id: str,
        requested_amount: float,
        desired_completion_date: Optional[str] = None,
        allows_partial: bool = False,
        request_date: Optional[str] = None,
        payment_options: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Evaluates whether a user can afford a prospective purchase over the 90-day forward simulation.
        Checks candidate plans including full payment, installments, partial payments, and spending modifications.
        Returns detailed status, safe payment amount, payment plan, and financial rationale.
        """
        options_input = None
        if payment_options:
            options_input = [PaymentOptionInput(**opt) for opt in payment_options]

        # Ensure valid ISO completion date
        comp_date = desired_completion_date or "2026-12-31"

        request_in = AffordabilityRequest(
            user_id=user_id,
            requested_amount=requested_amount,
            desired_completion_date=comp_date,
            allows_partial_payment=allows_partial,
            request_date=request_date,
            payment_options=options_input,
        )

        try:
            res = finance_service.evaluate_affordability(request_in, save_decision=True)
            return json.dumps(
                {
                    "affordability_status": res.affordability_status,
                    "payment_method": res.recommended_payment_method,
                    "amount_safe_to_pay": res.amount_safe_to_pay,
                    "payment_plan": res.payment_plan,
                    "payment_schedule": [p.model_dump() for p in res.payment_schedule],
                    "spending_changes": [s.model_dump() for s in res.spending_changes],
                    "explanation": res.decision_explanation,
                    "earliest_date_for_full_payment": res.earliest_date_for_full_payment,
                }
            )
        except Exception as exc:
            return json.dumps({"error": str(exc), "affordability_status": "error"})

    return evaluate_purchase

