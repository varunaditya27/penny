from sqlalchemy import text
from backend.app.db.session import engine, get_db


def test_database_connection():
    with engine.connect() as connection:
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
