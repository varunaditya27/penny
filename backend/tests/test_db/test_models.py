import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from backend.app.db.session import Base
from backend.app.db.models import UserDB, FinancialEventDB, PaymentOptionDB, DecisionRecordDB


@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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


def test_payment_option_create_and_query(db_session):
    option = PaymentOptionDB(
        payment_option_id="opt_bnpl_3",
        request_id="req_test_99",
        payment_method="bnpl_3",
        payment_amount=120.0,
        number_of_payments=3,
        first_payment_date="2026-09-15",
        payment_frequency_days=30,
        financing_fee=5.0,
        total_payable_amount=365.0,
    )
    db_session.add(option)
    db_session.commit()

    fetched = db_session.query(PaymentOptionDB).filter_by(payment_option_id="opt_bnpl_3").first()
    assert fetched is not None
    assert fetched.request_id == "req_test_99"
    assert fetched.payment_method == "bnpl_3"
    assert fetched.payment_amount == 120.0
    assert fetched.number_of_payments == 3
    assert fetched.first_payment_date == "2026-09-15"
    assert fetched.payment_frequency_days == 30
    assert fetched.financing_fee == 5.0
    assert fetched.total_payable_amount == 365.0


def test_not_null_constraints(db_session):
    invalid_user = UserDB(
        user_id="user_invalid_01",
        home_currency=None,
        current_available_balance=100.0,
        minimum_balance_to_keep=50.0,
    )
    db_session.add(invalid_user)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unique_primary_key_constraint(db_session):
    user1 = UserDB(
        user_id="user_dup_01",
        home_currency="USD",
        current_available_balance=100.0,
        minimum_balance_to_keep=50.0,
    )
    db_session.add(user1)
    db_session.commit()

    user2 = UserDB(
        user_id="user_dup_01",
        home_currency="EUR",
        current_available_balance=200.0,
        minimum_balance_to_keep=100.0,
    )
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_foreign_key_constraint(db_session):
    event = FinancialEventDB(
        event_id="ev_orphaned_01",
        user_id="non_existent_user",
        event_type="recurring",
        description="Unknown",
        category="misc",
        direction="debit",
        amount=10.0,
        currency="USD",
        event_date="2026-09-01",
        status="settled",
    )
    db_session.add(event)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cascade_delete_user_events_and_decisions(db_session):
    user = UserDB(
        user_id="user_cascade_01",
        home_currency="USD",
        current_available_balance=1000.0,
        minimum_balance_to_keep=100.0,
    )
    db_session.add(user)
    db_session.commit()

    event = FinancialEventDB(
        event_id="ev_cascade_01",
        user_id="user_cascade_01",
        event_type="discretionary",
        description="Coffee Maker",
        category="appliances",
        direction="debit",
        amount=85.0,
        currency="USD",
        event_date="2026-09-02",
        status="settled",
    )
    decision = DecisionRecordDB(
        request_id="req_cascade_01",
        user_id="user_cascade_01",
        amount_safe_to_pay=85.0,
        affordability_status="affordable_now",
        recommended_payment_method="full_payment",
        payment_plan="2026-09-02:85.00",
        spending_changes_needed="none",
        decision_explanation="Safe to pay.",
    )
    db_session.add_all([event, decision])
    db_session.commit()

    assert db_session.query(FinancialEventDB).filter_by(user_id="user_cascade_01").count() == 1
    assert db_session.query(DecisionRecordDB).filter_by(user_id="user_cascade_01").count() == 1

    # Delete user
    db_session.delete(user)
    db_session.commit()

    # Verify cascade delete removed events and decisions
    assert db_session.query(FinancialEventDB).filter_by(user_id="user_cascade_01").count() == 0
    assert db_session.query(DecisionRecordDB).filter_by(user_id="user_cascade_01").count() == 0


def test_composite_indexes_defined():
    event_indexes = {idx.name: [c.name for c in idx.columns] for idx in FinancialEventDB.__table__.indexes}
    assert "ix_financial_events_user_date" in event_indexes
    assert event_indexes["ix_financial_events_user_date"] == ["user_id", "event_date"]

    decision_indexes = {idx.name: [c.name for c in idx.columns] for idx in DecisionRecordDB.__table__.indexes}
    assert "ix_decision_records_user_created" in decision_indexes
    assert decision_indexes["ix_decision_records_user_created"] == ["user_id", "created_at"]


def test_primary_keys_no_redundant_index():
    assert UserDB.__table__.c.user_id.index is not True
    assert FinancialEventDB.__table__.c.event_id.index is not True
    assert PaymentOptionDB.__table__.c.payment_option_id.index is not True
