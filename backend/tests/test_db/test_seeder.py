import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.db.session import Base
from backend.app.db.models import UserDB, FinancialEventDB, PaymentOptionDB
from backend.app.db.seeder import seed_database_from_dataset


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


def test_seed_database_from_dataset(db_session):
    counts = seed_database_from_dataset(db_session, dataset_dir="dataset", limit_users=5)
    assert counts["users"] == 5
    assert counts["events"] > 0

    user = db_session.query(UserDB).first()
    assert user is not None
    assert user.home_currency in ["EUR", "USD", "INR", "IDR", "ZAR"]
    assert len(user.events) > 0

    # Test idempotency - re-running seeder should not create duplicate users
    re_counts = seed_database_from_dataset(db_session, dataset_dir="dataset", limit_users=5)
    total_users = db_session.query(UserDB).count()
    assert total_users == 5
