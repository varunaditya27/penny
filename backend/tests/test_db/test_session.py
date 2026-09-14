import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import backend.app.db.session as session_module
from backend.app.db.session import get_db, set_sqlite_pragma


@pytest.fixture(autouse=True)
def isolated_db_environment(monkeypatch):
    """
    Ensure test isolation: use an in-memory SQLite database and monkeypatch
    SessionLocal so get_db never connects to or creates ./penny.db.
    """
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False, "timeout": 30.0},
        pool_pre_ping=True,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    monkeypatch.setattr(session_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(session_module, "engine", test_engine)
    yield test_engine
    test_engine.dispose()


def test_database_connection(isolated_db_environment):
    with isolated_db_environment.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_get_db_generator():
    db_gen = get_db()
    session = next(db_gen)
    assert session is not None
    try:
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


def test_get_db_rollback_on_error(monkeypatch):
    mock_session = MagicMock()
    mock_session_maker = MagicMock(return_value=mock_session)
    monkeypatch.setattr(session_module, "SessionLocal", mock_session_maker)

    db_gen = get_db()
    session = next(db_gen)
    assert session is mock_session

    with pytest.raises(RuntimeError, match="Simulated error"):
        db_gen.throw(RuntimeError("Simulated error"))

    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()


def test_sqlite_pragma_applied():
    mock_dbapi_con = MagicMock()
    mock_cursor = MagicMock()
    mock_dbapi_con.cursor.return_value = mock_cursor

    set_sqlite_pragma(mock_dbapi_con, None)

    assert mock_cursor.execute.call_count == 2
    mock_cursor.execute.assert_any_call("PRAGMA journal_mode=WAL")
    mock_cursor.execute.assert_any_call("PRAGMA synchronous=NORMAL")
    mock_cursor.close.assert_called_once()
