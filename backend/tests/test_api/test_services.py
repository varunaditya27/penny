import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.db.session import Base
from backend.app.db.seeder import seed_database_from_dataset
from backend.app.services.finance_service import FinanceService
from backend.app.services.simulation_service import SimulationService
from backend.app.schemas.affordability import AffordabilityRequest


@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    seed_database_from_dataset(session, dataset_dir="dataset", limit_users=3)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


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
    result = service.evaluate_affordability(req)
    assert result.user_id == "user_01"
    assert result.affordability_status in [
        "affordable_now",
        "affordable_with_plan",
        "affordable_later",
        "not_affordable",
    ]
    assert result.decision_explanation != ""


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


def test_finance_service_user_risk_metrics(db_session):
    from backend.app.db.models import UserDB

    service = FinanceService(db_session)
    user_db = db_session.query(UserDB).filter_by(user_id="user_01").first()
    metrics = service.compute_user_risk_metrics(user_db)
    assert metrics.monthly_fixed_burn_rate >= 0.0
    assert metrics.monthly_confirmed_income >= 0.0
    assert metrics.fixed_cost_ratio >= 0.0


def test_cash_flow_risk_service_direct(db_session):
    from backend.app.db.models import UserDB
    from backend.app.services.risk_service import CashFlowRiskService

    user_db = db_session.query(UserDB).filter_by(user_id="user_01").first()
    metrics = CashFlowRiskService.compute_risk_metrics(user_db)
    assert metrics.monthly_fixed_burn_rate >= 0.0
    assert metrics.monthly_confirmed_income >= 0.0
    assert metrics.discretionary_cashflow is not None


def test_mappers_helpers(db_session):
    from backend.app.db.models import UserDB
    from backend.app.services.mappers import (
        map_events_to_domain,
        map_user_to_domain,
        map_user_to_response,
        parse_payment_schedule,
        parse_spending_changes,
    )

    user_db = db_session.query(UserDB).filter_by(user_id="user_01").first()
    domain_user = map_user_to_domain(user_db)
    assert domain_user.user_id == "user_01"
    assert isinstance(domain_user.expense_categories_to_protect, list)

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
    assert changes[1].amount == 50.0

