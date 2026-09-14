from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.seeder import seed_database_from_dataset
from backend.app.db.session import Base

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_DIR = str(REPO_ROOT / "dataset")


@pytest.fixture(scope="session")
def session_engine():
    """Session-scoped in-memory SQLite engine seeded once for all agent tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()
    seed_database_from_dataset(db, dataset_dir=DATASET_DIR, limit_users=3)
    db.close()
    return engine


@pytest.fixture
def db_session(session_engine):
    """Provides an isolated database session rolled back after every test."""
    connection = session_engine.connect()
    transaction = connection.begin()
    TestingSession = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = TestingSession()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


from backend.app.agent.checkpointers.memory import reset_memory_checkpointer


@pytest.fixture(autouse=True)
def clean_checkpointer():
    reset_memory_checkpointer()
    yield
    reset_memory_checkpointer()
