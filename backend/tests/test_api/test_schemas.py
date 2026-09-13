import pytest
from pydantic import ValidationError
from backend.app.schemas.affordability import AffordabilityRequest, AffordabilityResponse
from backend.app.schemas.profile import UserProfileResponse, UserProfileUpdate
from backend.app.schemas.event import FinancialEventResponse, FinancialEventCreate
from backend.app.schemas.simulation import TrajectoryResponse, TrajectoryPoint


def test_affordability_request_validation():
    req = AffordabilityRequest(
        user_id="user_01",
        requested_amount=500.0,
        desired_completion_date="2026-10-01",
        allows_partial_payment=True,
        request_text="Can I buy an iPad?",
    )
    assert req.requested_amount == 500.0
    assert req.allows_partial_payment is True

    # Negative or zero amount should fail validation
    with pytest.raises(ValidationError):
        AffordabilityRequest(
            user_id="user_01",
            requested_amount=-50.0,
            desired_completion_date="2026-10-01",
        )


def test_user_profile_schemas():
    profile = UserProfileResponse(
        user_id="user_01",
        home_currency="EUR",
        current_available_balance=1200.0,
        minimum_balance_to_keep=300.0,
        financial_priorities=["protect_essentials"],
        expense_categories_to_protect=["rent", "groceries"],
        expense_categories_to_reduce=["dining"],
        expense_categories_to_stop=["streaming"],
        payment_methods_user_will_consider=["full_payment"],
        max_installment_months=6,
    )
    assert profile.user_id == "user_01"
    assert "rent" in profile.expense_categories_to_protect

    update = UserProfileUpdate(minimum_balance_to_keep=400.0)
    assert update.minimum_balance_to_keep == 400.0


def test_simulation_trajectory_schema():
    point = TrajectoryPoint(date="2026-09-13", baseline_balance=1000.0, with_purchase_balance=800.0)
    resp = TrajectoryResponse(
        user_id="user_01",
        currency="USD",
        minimum_balance_to_keep=200.0,
        points=[point],
        lowest_projected_balance=800.0,
        lowest_balance_date="2026-09-13",
        buffer_margin=600.0,
        is_safe=True,
    )
    assert resp.is_safe is True
    assert resp.buffer_margin == 600.0
    assert resp.lowest_balance_date == "2026-09-13"
    assert len(resp.points) == 1
