import pytest
from backend.app.db.models import DecisionRecordDB, FinancialEventDB, UserDB
from backend.app.exceptions import UserNotFoundError
from backend.app.schemas.affordability import AffordabilityRequest
from backend.app.schemas.event import FinancialEventCreate
from backend.app.schemas.profile import UserProfileUpdate
from backend.app.services.event_service import EventService
from backend.app.services.finance_service import FinanceService
from backend.app.services.simulation_service import SimulationService
from backend.app.services.risk_service import CashFlowRiskService
from backend.app.services.mappers import (
    map_events_to_domain,
    map_user_to_domain,
    map_user_to_response,
    parse_payment_schedule,
    parse_spending_changes,
)


def test_finance_service_evaluate_affordability(db_session):
    service = FinanceService(db_session)
    req = AffordabilityRequest(
        user_id="user_01",
        requested_amount=100.0,
        desired_completion_date="2026-03-31",
        request_date="2026-01-01",
        allows_partial_payment=True,
        request_text="Headphones",
    )
    result = service.evaluate_affordability(req, save_decision=True)
    assert result.user_id == "user_01"
    assert result.affordability_status in [
        "affordable_now",
        "affordable_with_plan",
        "affordable_later",
        "not_affordable",
    ]
    assert result.decision_explanation != ""

    # Verify decision record was actually persisted to DB (fixes HI-013)
    record = db_session.query(DecisionRecordDB).filter_by(request_id=result.request_id).first()
    assert record is not None
    assert record.user_id == "user_01"
    assert record.amount_safe_to_pay == result.amount_safe_to_pay


def test_finance_service_evaluate_without_saving(db_session):
    service = FinanceService(db_session)
    req = AffordabilityRequest(
        user_id="user_01",
        requested_amount=50.0,
        desired_completion_date="2026-03-31",
        request_date="2026-01-01",
    )
    result = service.evaluate_affordability(req, save_decision=False)
    record = db_session.query(DecisionRecordDB).filter_by(request_id=result.request_id).first()
    assert record is None


def test_finance_service_user_not_found_raises(db_session):
    service = FinanceService(db_session)
    req = AffordabilityRequest(
        user_id="nonexistent_user",
        requested_amount=50.0,
        desired_completion_date="2026-03-31",
    )
    with pytest.raises(UserNotFoundError, match="User 'nonexistent_user' not found"):
        service.evaluate_affordability(req)


def test_finance_service_update_user(db_session):
    service = FinanceService(db_session)
    user = service.get_user("user_01")
    assert user is not None

    update_in = UserProfileUpdate(
        minimum_balance_to_keep=25000.0,
        financial_priorities=["housing", "groceries"],
        expense_categories_to_protect=["rent"],
        expense_categories_to_reduce=["dining_out"],
        expense_categories_to_stop=["subscriptions"],
        payment_methods_user_will_consider=["full_payment", "installments"],
        max_installment_months=6,
    )
    updated = service.update_user(user, update_in)
    assert updated.minimum_balance_to_keep == 25000.0
    assert updated.financial_priorities == "housing|groceries"
    assert updated.expense_categories_to_protect == "rent"
    assert updated.expense_categories_to_reduce == "dining_out"
    assert updated.expense_categories_to_stop == "subscriptions"
    assert updated.max_installment_months == 6


def test_simulation_service_trajectory(db_session):
    sim_service = SimulationService(db_session)
    traj = sim_service.compute_user_trajectory(
        user_id="user_01",
        prospective_amount=100.0,
        start_date="2026-01-01",
    )
    assert traj.user_id == "user_01"
    assert len(traj.points) == 91  # 0..90 days
    assert traj.points[0].with_purchase_balance is not None
    assert traj.lowest_projected_balance <= traj.points[0].baseline_balance
    assert traj.lowest_balance_date != ""
    assert traj.buffer_margin is not None


def test_simulation_service_baseline_without_prospective(db_session):
    sim_service = SimulationService(db_session)
    traj = sim_service.compute_user_trajectory(
        user_id="user_01",
        prospective_amount=None,
        start_date="2026-01-01",
    )
    assert traj.points[0].with_purchase_balance is None
    assert traj.points[0].baseline_balance is not None


def test_simulation_service_user_not_found_raises(db_session):
    sim_service = SimulationService(db_session)
    with pytest.raises(UserNotFoundError, match="User 'unknown' not found"):
        sim_service.compute_user_trajectory(user_id="unknown")


def test_event_service(db_session):
    event_service = EventService(db_session)
    events = event_service.list_user_events(user_id="user_01", limit=10, offset=0)
    assert len(events) <= 10
    assert all(e.user_id == "user_01" for e in events)

    new_event_in = FinancialEventCreate(
        event_type="expense",
        description="Coffee Beans",
        category="groceries",
        direction="debit",
        amount=15.0,
        currency="ZAR",
        event_date="2026-02-01",
    )
    created = event_service.create_event("user_01", new_event_in)
    assert created.description == "Coffee Beans"
    assert created.amount == 15.0


def test_finance_service_user_risk_metrics(db_session):
    service = FinanceService(db_session)
    user = service.get_user("user_01")
    metrics = service.compute_user_risk_metrics(user)
    assert metrics.monthly_fixed_burn_rate >= 0.0
    assert metrics.monthly_confirmed_income >= 0.0
    assert isinstance(metrics.fixed_cost_ratio, float)
    assert isinstance(metrics.discretionary_cashflow, float)


def test_cash_flow_risk_service_direct(db_session):
    user_db = db_session.query(UserDB).filter_by(user_id="user_01").first()
    metrics = CashFlowRiskService.compute_risk_metrics(user_db)
    assert metrics.monthly_fixed_burn_rate > 0.0


def test_mappers_helpers(db_session):
    user_db = db_session.query(UserDB).filter_by(user_id="user_01").first()
    domain_user = map_user_to_domain(user_db)
    assert domain_user.user_id == "user_01"
    assert isinstance(domain_user.expense_categories_to_protect, (set, list))

    domain_events = map_events_to_domain(user_db.events)
    assert len(domain_events) == len(user_db.events)

    response_schema = map_user_to_response(user_db)
    assert response_schema.user_id == "user_01"

    schedule = parse_payment_schedule("2026-01-01:100.00|2026-02-01:100.00")
    assert len(schedule) == 2
    assert schedule[0].amount == 100.0

    changes = parse_spending_changes("stop:event_101|reduce_to:event_102:50.0")
    assert len(changes) == 2
    assert changes[0].action == "stop"
