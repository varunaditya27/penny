from typing import List, Optional

from backend.app.db.models import FinancialEventDB, PaymentOptionDB, UserDB
from backend.app.schemas.affordability import PaymentScheduleItem, SpendingChangeItem
from backend.app.schemas.profile import CashFlowRiskMetrics, UserProfileResponse
from backend.core.models.domain import FinancialEvent, PaymentOption, UserProfile


def map_user_to_domain(user_db: UserDB) -> UserProfile:
    """Converts a UserDB SQLAlchemy model to a pure UserProfile domain dataclass."""
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


def map_events_to_domain(events_db: List[FinancialEventDB]) -> List[FinancialEvent]:
    """Converts a list of FinancialEventDB models to pure FinancialEvent domain dataclasses."""
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


def map_options_to_domain(options_db: List[PaymentOptionDB]) -> List[PaymentOption]:
    """Converts PaymentOptionDB models to pure PaymentOption domain dataclasses."""
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


def map_user_to_response(
    user: UserDB, risk_metrics: Optional[CashFlowRiskMetrics] = None
) -> UserProfileResponse:
    """Maps a UserDB model and optional risk metrics into a UserProfileResponse schema."""
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


def parse_payment_schedule(payment_plan_str: str) -> List[PaymentScheduleItem]:
    """Parses pipe-separated `<date>:<amount>` strings into PaymentScheduleItem models."""
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


def parse_spending_changes(spending_str: str) -> List[SpendingChangeItem]:
    """Parses pipe-separated `stop:<id>` and `reduce_to:<id>:<amt>` into SpendingChangeItem models."""
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
