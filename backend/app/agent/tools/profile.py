import json
from langchain_core.tools import BaseTool, tool
from sqlalchemy.orm import Session

from backend.app.services.finance_service import FinanceService


def create_profile_tool(db: Session) -> BaseTool:
    finance_service = FinanceService(db)

    @tool
    def get_user_financial_profile(user_id: str) -> str:
        """
        Retrieves the financial profile and cashflow risk metrics for a user.
        Includes available balance, minimum reserve threshold, protected expense categories,
        and spending flexibility priorities.
        """
        try:
            profile = finance_service.get_user_profile(user_id, include_risk_metrics=True)
            if not profile:
                return json.dumps({"error": f"User '{user_id}' not found."})

            return json.dumps(
                {
                    "user_id": profile.user_id,
                    "home_currency": profile.home_currency,
                    "current_available_balance": profile.current_available_balance,
                    "minimum_balance_to_keep": profile.minimum_balance_to_keep,
                    "financial_priorities": profile.financial_priorities,
                    "expense_categories_to_protect": profile.expense_categories_to_protect,
                    "expense_categories_to_reduce": profile.expense_categories_to_reduce,
                    "expense_categories_to_stop": profile.expense_categories_to_stop,
                    "max_installment_months": profile.max_installment_months,
                    "risk_metrics": profile.risk_metrics.model_dump() if profile.risk_metrics else None,
                }
            )
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    return get_user_financial_profile
