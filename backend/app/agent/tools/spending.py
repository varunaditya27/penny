import json
import uuid
from typing import List, Optional
from langchain_core.tools import BaseTool, tool
from sqlalchemy.orm import Session

from backend.app.db.models import FinancialEventDB, UserDB


def create_spending_tools(db: Session) -> List[BaseTool]:
    @tool
    def simulate_spending_reduction(
        user_id: str,
        category: str,
        reduction_pct: float = 0.5,
    ) -> str:
        """
        Simulates reducing recurring expenses in a specified flexible category (e.g. Dining, Entertainment).
        Calculates historical 30-day average spend and forward 90-day estimated savings.
        """
        try:
            user = db.query(UserDB).filter_by(user_id=user_id).first()
            if not user:
                return json.dumps({"error": f"User '{user_id}' not found."})

            # Check if category is protected
            protected = [c.strip().lower() for c in (user.expense_categories_to_protect or "").split("|") if c.strip()]
            if category.strip().lower() in protected:
                return json.dumps({
                    "allowed": False,
                    "reason": f"Category '{category}' is marked as protected in user preferences."
                })

            events = (
                db.query(FinancialEventDB)
                .filter(
                    FinancialEventDB.user_id == user_id,
                    FinancialEventDB.category.ilike(f"%{category}%"),
                    FinancialEventDB.direction == "debit",
                    FinancialEventDB.amount > 0,
                )
                .all()
            )

            total_past_spend = sum(abs(e.amount or 0.0) for e in events)
            # Estimate monthly spend from sample (approx 90-day lookback / 3 months)
            monthly_est = total_past_spend / 3.0 if total_past_spend > 0 else 50.0
            monthly_savings = monthly_est * max(0.0, min(1.0, reduction_pct))
            estimated_90d_savings = monthly_savings * 3.0

            return json.dumps({
                "allowed": True,
                "category": category,
                "reduction_pct": reduction_pct,
                "estimated_monthly_savings": round(monthly_savings, 2),
                "estimated_90d_savings": round(estimated_90d_savings, 2),
                "home_currency": user.home_currency,
            })
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    @tool
    def request_spending_modification_approval(
        user_id: str,
        category: str,
        reduction_amount: float,
        reason: str,
    ) -> str:
        """
        Initiates a Human-in-the-Loop approval gate to ask the user if they consent to
        cutting or reducing expenses in a specific category to afford their goal.
        """
        action_id = f"act_{uuid.uuid4().hex[:8]}"
        return json.dumps({
            "status": "pending_user_confirmation",
            "action_id": action_id,
            "user_id": user_id,
            "category": category,
            "reduction_amount": reduction_amount,
            "reason": reason,
            "message": f"Approval requested: Reduce {category} by {reduction_amount} for '{reason}'."
        })

    return [simulate_spending_reduction, request_spending_modification_approval]
