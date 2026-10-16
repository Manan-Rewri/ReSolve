"""Lightweight schema migrations.

SQLAlchemy's create_all() never adds columns to tables that already exist, so a
database created by an older build silently lacks later additions (for example
problems.content_html) and every query against it fails with "no such column".
These helpers add any missing columns in place so upgrades survive without a
migration tool.
"""
from typing import Dict, List

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# Table -> {column name: SQL type}. Only additive, nullable-safe columns belong here.
BACKFILLABLE_COLUMNS: Dict[str, Dict[str, str]] = {
    "users": {"full_name": "VARCHAR(255)"},
    "problems": {"content_html": "TEXT"},
    "review_logs": {"notes": "TEXT"},
}


def missing_columns(engine: Engine, table_name: str) -> List[str]:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return []
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    return [name for name in BACKFILLABLE_COLUMNS.get(table_name, {}) if name not in existing]


def apply_migrations(engine: Engine) -> List[str]:
    """Adds any missing columns and returns them as "table.column" names."""
    added: List[str] = []

    with engine.begin() as connection:
        tables = set(inspect(connection).get_table_names())

        for table_name, columns in BACKFILLABLE_COLUMNS.items():
            if table_name not in tables:
                continue
            for column, sql_type in columns.items():
                if column not in missing_columns(engine, table_name):
                    continue
                connection.execute(
                    text(f'ALTER TABLE "{table_name}" ADD COLUMN "{column}" {sql_type}')
                )
                added.append(f"{table_name}.{column}")

    return added