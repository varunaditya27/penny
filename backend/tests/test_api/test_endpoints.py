import pytest
from fastapi import HTTPException
from backend.app.api.deps import get_current_user_id, verify_user_access, DEFAULT_USER_ID
from backend.app.config import settings


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_security_headers(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert res.headers["x-xss-protection"] == "1; mode=block"
    assert res.headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_cors_headers(client):
    # Preflight OPTIONS request
    res = client.options(
        "/api/v1/users/user_01",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
    allowed_methods = res.headers.get("access-control-allow-methods", "")
    assert "PATCH" in allowed_methods
    assert "GET" in allowed_methods
    assert "POST" in allowed_methods
    assert "OPTIONS" in allowed_methods


def test_get_user_profile(client):
    res = client.get("/api/v1/users/user_01")
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "user_01"
    assert data["home_currency"] in ["EUR", "USD", "INR", "IDR", "ZAR"]
    assert "risk_metrics" in data
    assert data["risk_metrics"]["monthly_fixed_burn_rate"] >= 0.0


def test_get_user_events(client):
    res = client.get("/api/v1/users/user_01/events")
    assert res.status_code == 200
    events = res.json()
    assert isinstance(events, list)
    assert len(events) > 0


def test_evaluate_affordability_endpoint(client):
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


def test_get_simulation_trajectory_endpoint(client):
    res = client.get("/api/v1/simulation/trajectory/user_01?prospective_amount=150.0&start_date=2026-01-01")
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "user_01"
    assert len(data["points"]) == 91
    assert "lowest_projected_balance" in data
    assert "lowest_balance_date" in data
    assert "buffer_margin" in data
    assert "is_safe" in data


def test_evaluate_affordability_with_installment_options(client):
    payload = {
        "user_id": "user_01",
        "requested_amount": 600.0,
        "desired_completion_date": "2026-03-31",
        "request_date": "2026-01-01",
        "allows_partial_payment": False,
        "payment_options": [
            {
                "payment_option_id": "opt_split_3",
                "payment_method": "installments",
                "payment_amount": 200.0,
                "number_of_payments": 3,
                "first_payment_date": "2026-01-01",
                "payment_frequency_days": 30,
                "financing_fee": 0.0,
                "total_payable_amount": 600.0,
            }
        ],
    }
    res = client.post("/api/v1/affordability/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "user_01"
    assert "payment_plan" in data


def test_update_user_profile_endpoint(client):
    res = client.patch(
        "/api/v1/users/user_01",
        json={"minimum_balance_to_keep": 450.0},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "user_01"
    assert data["minimum_balance_to_keep"] == 450.0
    assert "risk_metrics" in data


def test_auth_scaffolding_dependencies():
    # 1. get_current_user_id with Bearer token
    assert get_current_user_id(authorization="Bearer token_123") == "token_123"
    assert get_current_user_id(authorization="raw_token_xyz") == "raw_token_xyz"
    assert get_current_user_id(authorization=None) == DEFAULT_USER_ID

    # 2. verify_user_access: authorized matching user
    assert verify_user_access(target_user_id="user_01", current_user_id="user_01") == "user_01"

    # 3. verify_user_access: unauthorized mismatch
    with pytest.raises(HTTPException) as exc:
        verify_user_access(target_user_id="user_01", current_user_id="user_02")
    assert exc.value.status_code == 403

    # 4. verify_user_access: dev bypass when header omitted (current_user_id == DEFAULT_USER_ID)
    assert verify_user_access(target_user_id="user_01", current_user_id=DEFAULT_USER_ID) == "user_01"

    # 5. verify_user_access: production mode enforces auth
    original_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        with pytest.raises(HTTPException) as exc_prod:
            verify_user_access(target_user_id="user_01", current_user_id=DEFAULT_USER_ID)
        assert exc_prod.value.status_code == 403
    finally:
        settings.ENVIRONMENT = original_env
