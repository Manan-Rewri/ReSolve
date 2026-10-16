from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from app.database import engine as app_engine
from app.migrations import apply_migrations, missing_columns


def _stale_engine():
    """A database created before problems.content_html existed."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE problems ("
                "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE users ("
                "id VARCHAR(36) PRIMARY KEY, email VARCHAR(255) NOT NULL)"
            )
        )
    return engine


def test_missing_columns_detects_stale_schema():
    engine = _stale_engine()
    assert missing_columns(engine, "problems") == ["content_html"]
    assert missing_columns(engine, "users") == ["full_name"]
    assert missing_columns(engine, "table_that_does_not_exist") == []


def test_apply_migrations_adds_missing_columns():
    engine = _stale_engine()
    added = apply_migrations(engine)

    assert "problems.content_html" in added
    assert "users.full_name" in added

    columns = {c["name"] for c in inspect(engine).get_columns("problems")}
    assert "content_html" in columns


def test_apply_migrations_is_idempotent():
    engine = _stale_engine()
    apply_migrations(engine)
    assert apply_migrations(engine) == []


def test_live_database_is_up_to_date():
    """Guards the real dev database against the stale-column 500s."""
    assert missing_columns(app_engine, "problems") == []
    assert missing_columns(app_engine, "review_logs") == []
    assert missing_columns(app_engine, "users") == []


def test_live_database_has_all_tables():
    tables = set(inspect(app_engine).get_table_names())
    assert {"users", "problems", "review_logs"} <= tables