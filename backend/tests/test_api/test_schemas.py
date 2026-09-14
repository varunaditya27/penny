import pytest
from pydantic import ValidationError
from backend.app.schemas.affordability import AffordabilityRequest, AffordabilityResponse, PaymentOptionInput
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

    # Exceeding 1e9 should fail validation
    with pytest.raises(ValidationError):
        AffordabilityRequest(
            user_id="user_01",
            requested_amount=1e9 + 1,
            desired_completion_date="2026-10-01",
        )

    # Malformed date should fail validation
    with pytest.raises(ValidationError):
        AffordabilityRequest(
            user_id="user_01",
            requested_amount=500.0,
            desired_completion_date="2026/10/01",
        )

    with pytest.raises(ValidationError):
        AffordabilityRequest(
            user_id="user_01",
            requested_amount=500.0,
            desired_completion_date="2026-10-01",
            request_date="invalid-date",
        )


def test_payment_option_input_validation():
    valid = PaymentOptionInput(
        payment_option_id="opt_1",
        payment_method="installments",
        payment_amount=100.0,
        payment_frequency_days=30,
        number_of_payments=3,
        first_payment_date="2026-02-01",
        financing_fee=0.0,
        total_payable_amount=300.0,
    )
    assert valid.payment_amount == 100.0
    assert valid.payment_frequency_days == 30

    # Non-positive payment_amount
    with pytest.raises(ValidationError):
        PaymentOptionInput(
            payment_method="installments",
            payment_amount=0.0,
            payment_frequency_days=30,
            number_of_payments=3,
            first_payment_date="2026-02-01",
            total_payable_amount=300.0,
        )

    # Non-positive payment_frequency_days
    with pytest.raises(ValidationError):
        PaymentOptionInput(
            payment_method="installments",
            payment_amount=100.0,
            payment_frequency_days=0,
            number_of_payments=3,
            first_payment_date="2026-02-01",
            total_payable_amount=300.0,
        )

    # Non-positive number_of_payments
    with pytest.raises(ValidationError):
        PaymentOptionInput(
            payment_method="installments",
            payment_amount=100.0,
            payment_frequency_days=30,
            number_of_payments=0,
            first_payment_date="2026-02-01",
            total_payable_amount=300.0,
        )

    # Non-positive total_payable_amount
    with pytest.raises(ValidationError):
        PaymentOptionInput(
            payment_method="installments",
            payment_amount=100.0,
            payment_frequency_days=30,
            number_of_payments=3,
            first_payment_date="2026-02-01",
            total_payable_amount=-5.0,
        )


def test_affordability_response_deprecated_fields():
    fields = AffordabilityResponse.model_fields
    assert "[Deprecated]" in fields["payment_plan"].description
    assert "[Deprecated]" in fields["spending_changes_needed"].description


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


def test_profile_delimiter_guards():
    list_fields = [
        "financial_priorities",
        "expense_categories_to_protect",
        "expense_categories_to_reduce",
        "expense_categories_to_stop",
        "payment_methods_user_will_consider",
    ]
    for field in list_fields:
        # Pipe delimiter rejection
        with pytest.raises(ValidationError) as exc_pipe:
            UserProfileUpdate(**{field: ["safe", "danger|item"]})
        assert "cannot contain '|' or ':' delimiters" in str(exc_pipe.value)

        # Colon delimiter rejection
        with pytest.raises(ValidationError) as exc_colon:
            UserProfileUpdate(**{field: ["danger:item"]})
        assert "cannot contain '|' or ':' delimiters" in str(exc_colon.value)


def test_profile_boundary_constraints():
    # Negative minimum balance rejected
    with pytest.raises(ValidationError):
        UserProfileUpdate(minimum_balance_to_keep=-1.0)

    # 0 installment months rejected (must be gt 0)
    with pytest.raises(ValidationError):
        UserProfileUpdate(max_installment_months=0)

    # > 36 installment months rejected (must be le 36)
    with pytest.raises(ValidationError):
        UserProfileUpdate(max_installment_months=37)

    # Valid boundaries
    up = UserProfileUpdate(minimum_balance_to_keep=0.0, max_installment_months=36)
    assert up.minimum_balance_to_keep == 0.0
    assert up.max_installment_months == 36


def test_financial_event_create_validation():
    valid_event = FinancialEventCreate(
        event_type="recurring_debit",
        description="Gym membership",
        category="fitness",
        direction="debit",
        amount=50.0,
        currency="USD",
        event_date="2026-01-15",
        settlement_date="2026-01-16",
        status="settled",
        flexibility="fixed",
    )
    assert valid_event.amount == 50.0
    assert valid_event.currency == "USD"

    # Unsupported currency
    with pytest.raises(ValidationError):
        FinancialEventCreate(
            event_type="test",
            description="test",
            category="test",
            direction="debit",
            amount=50.0,
            currency="GBP",  # Not in INR, IDR, ZAR, EUR, USD
            event_date="2026-01-15",
        )

    # Negative amount
    with pytest.raises(ValidationError):
        FinancialEventCreate(
            event_type="test",
            description="test",
            category="test",
            direction="debit",
            amount=-10.0,
            currency="USD",
            event_date="2026-01-15",
        )

    # Amount >= 1e9
    with pytest.raises(ValidationError):
        FinancialEventCreate(
            event_type="test",
            description="test",
            category="test",
            direction="debit",
            amount=1e9,
            currency="USD",
            event_date="2026-01-15",
        )

    # Invalid event_date format
    with pytest.raises(ValidationError):
        FinancialEventCreate(
            event_type="test",
            description="test",
            category="test",
            direction="debit",
            amount=50.0,
            currency="USD",
            event_date="15-01-2026",
        )

    # Invalid settlement_date format
    with pytest.raises(ValidationError):
        FinancialEventCreate(
            event_type="test",
            description="test",
            category="test",
            direction="debit",
            amount=50.0,
            currency="USD",
            event_date="2026-01-15",
            settlement_date="2026/01/16",
        )

    # Invalid direction
    with pytest.raises(ValidationError):
        FinancialEventCreate(
            event_type="test",
            description="test",
            category="test",
            direction="inbound",
            amount=50.0,
            currency="USD",
            event_date="2026-01-15",
        )

    # Invalid status
    with pytest.raises(ValidationError):
        FinancialEventCreate(
            event_type="test",
            description="test",
            category="test",
            direction="debit",
            amount=50.0,
            currency="USD",
            event_date="2026-01-15",
            status="unknown",
        )

    # Invalid flexibility
    with pytest.raises(ValidationError):
        FinancialEventCreate(
            event_type="test",
            description="test",
            category="test",
            direction="debit",
            amount=50.0,
            currency="USD",
            event_date="2026-01-15",
            flexibility="semi-fixed",
        )


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
