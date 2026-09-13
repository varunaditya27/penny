def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


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
