import csv


def test_full_user_lifecycle_and_affordability_flow(client):
    # 1. Fetch initial profile
    res = client.get("/api/v1/users/user_01")
    assert res.status_code == 200
    initial_user = res.json()
    orig_min_bal = initial_user["minimum_balance_to_keep"]

    # 2. Add an essential debit event for user_01
    new_event = {
        "event_type": "recurring",
        "description": "Premium Health Insurance",
        "category": "healthcare",
        "direction": "debit",
        "amount": 250.0,
        "currency": initial_user["home_currency"],
        "event_date": "2026-01-05",
        "status": "settled",
        "flexibility": "fixed",
    }
    res = client.post("/api/v1/users/user_01/events", json=new_event)
    assert res.status_code == 201
    created_ev = res.json()
    assert created_ev["amount"] == 250.0

    # 3. Update user minimum balance floor
    updated_min_bal = orig_min_bal + 200.0
    res = client.patch(
        "/api/v1/users/user_01",
        json={"minimum_balance_to_keep": updated_min_bal},
    )
    assert res.status_code == 200
    assert res.json()["minimum_balance_to_keep"] == updated_min_bal

    # 4. Evaluate an affordability request with the tighter budget
    afford_payload = {
        "user_id": "user_01",
        "requested_amount": 500.0,
        "desired_completion_date": "2026-03-31",
        "request_date": "2026-01-01",
        "allows_partial_payment": True,
        "request_text": "New Monitor",
    }
    res = client.post("/api/v1/affordability/evaluate", json=afford_payload)
    assert res.status_code == 200
    decision = res.json()
    assert decision["user_id"] == "user_01"
    assert decision["affordability_status"] in [
        "affordable_now",
        "affordable_with_plan",
        "affordable_later",
        "not_affordable",
    ]

    # 5. Retrieve the updated trajectory curve
    res = client.get(
        "/api/v1/simulation/trajectory/user_01?prospective_amount=500.0&start_date=2026-01-01"
    )
    assert res.status_code == 200
    traj = res.json()
    assert traj["minimum_balance_to_keep"] == updated_min_bal
    assert len(traj["points"]) == 91


def test_batch_sample_requests_via_api(client):
    """Runs the first 5 requests from sample_requests.csv through the FastAPI endpoint."""
    with open("dataset/sample_requests.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 5:
                break
            payload = {
                "user_id": row["user_id"],
                "requested_amount": float(row["requested_amount"]),
                "desired_completion_date": row["desired_completion_date"],
                "request_date": row["request_date"],
                "allows_partial_payment": row["allows_partial_payment"].lower() == "true",
                "request_text": row.get("request_text", ""),
            }
            res = client.post("/api/v1/affordability/evaluate", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["affordability_status"] in [
                "affordable_now",
                "affordable_with_plan",
                "affordable_later",
                "not_affordable",
            ]
