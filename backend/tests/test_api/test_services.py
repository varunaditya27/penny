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
