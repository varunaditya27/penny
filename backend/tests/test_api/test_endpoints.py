import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.session import Base, get_db
from backend.app.db.seeder import seed_database_from_dataset
from backend.app.main import app

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_database_from_dataset(db, dataset_dir="dataset", limit_users=3)
    db.close()


def teardown_module():
    Base.metadata.drop_all(bind=test_engine)


def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_get_user_profile():
    res = client.get("/api/v1/users/user_01")
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "user_01"
    assert data["home_currency"] in ["EUR", "USD", "INR", "IDR", "ZAR"]


def test_get_user_events():
    res = client.get("/api/v1/users/user_01/events")
    assert res.status_code == 200
    events = res.json()
    assert isinstance(events, list)
    assert len(events) > 0


def test_evaluate_affordability_endpoint():
    payload = {
        "user_id": "user_01",
        "requested_amount": 250.0,
        "desired_completion_date": "2026-03-31",
        "request_date": "2026-01-01",
        "allows_partial_payment": True,
        "request_text": "Fitness Watch",
    }
    res = client.post("/api/v1/affordability/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "user_01"
    assert "amount_safe_to_pay" in data
    assert "affordability_status" in data
    assert "recommended_payment_method" in data


def test_get_simulation_trajectory_endpoint():
    res = client.get("/api/v1/simulation/trajectory/user_01?prospective_amount=150.0&start_date=2026-01-01")
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "user_01"
    assert len(data["points"]) == 91
    assert "lowest_projected_balance" in data
    assert "is_safe" in data
