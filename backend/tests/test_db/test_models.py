import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.db.session import Base
from backend.app.db.models import UserDB, FinancialEventDB, PaymentOptionDB, DecisionRecordDB


@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


def test_create_user_and_event(db_session):
    user = UserDB(
        user_id="user_test_01",
        home_currency="USD",
        current_available_balance=1000.0,
        minimum_balance_to_keep=200.0,
        financial_priorities="protect_essentials|save_buffer",
        expense_categories_to_protect="rent|groceries",
        expense_categories_to_reduce="entertainment",
        expense_categories_to_stop="streaming",
        payment_methods_user_will_consider="full_payment|installments",
        max_installment_months=6,
    )
    db_session.add(user)
    db_session.commit()

    event = FinancialEventDB(
        event_id="ev_test_01",
        user_id="user_test_01",
        event_type="recurring",
        description="Apartment Rent",
        category="rent",
        direction="debit",
        amount=500.0,
        currency="USD",
        event_date="2026-09-01",
        settlement_date="2026-09-01",
        status="settled",
        flexibility="fixed",
    )
    db_session.add(event)
    db_session.commit()

    fetched_user = db_session.query(UserDB).filter_by(user_id="user_test_01").first()
    assert fetched_user is not None
    assert fetched_user.home_currency == "USD"
    assert len(fetched_user.events) == 1
    assert fetched_user.events[0].amount == 500.0
    assert fetched_user.events[0].user.user_id == "user_test_01"


def test_create_decision_record(db_session):
    user = UserDB(
        user_id="user_test_02",
        home_currency="EUR",
        current_available_balance=500.0,
        minimum_balance_to_keep=100.0,
    )
    db_session.add(user)
    db_session.commit()

    decision = DecisionRecordDB(
        request_id="req_01",
        user_id="user_test_02",
        amount_safe_to_pay=300.0,
        affordability_status="affordable_now",
        recommended_payment_method="full_payment",
        payment_plan="2026-09-13:300.00",
        earliest_date_for_full_payment="2026-09-13",
        spending_changes_needed="none",
        decision_explanation="Safe to pay today with ample buffer.",
    )
    db_session.add(decision)
    db_session.commit()

    fetched_decision = db_session.query(DecisionRecordDB).filter_by(request_id="req_01").first()
    assert fetched_decision is not None
    assert fetched_decision.amount_safe_to_pay == 300.0
    assert fetched_decision.user.user_id == "user_test_02"
