"""Additive-only schema migrations for JiuWei CRM.

Design constraints (production runs a live SQLite database with real data):

* The ONLY DDL this module can emit is ``ALTER TABLE ... ADD COLUMN`` and
  ``CREATE INDEX IF NOT EXISTS``. There is no code path here that drops,
  renames, truncates or rewrites a table.
* Every step is idempotent — it inspects ``PRAGMA table_info`` first, so
  running it twice is a no-op and running it on a fresh database is a no-op
  too (``Base.metadata.create_all`` already created the columns).
* New *tables* are created by ``Base.metadata.create_all``, which never
  touches existing tables.

The same function is used by the startup hook in ``app.main`` and by the
standalone script ``backend/migrations/v0_2_1_resume_batch_import.py``.
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

MIGRATION_VERSION = "v0.2.1"

# (table, column, column_type) — all nullable, all without defaults, so
# existing rows keep working untouched and read back as NULL.
ADDITIVE_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("import_logs", "batch_id", "INTEGER"),
    ("import_logs", "error_code", "VARCHAR(50)"),
    ("lead_drafts", "batch_id", "INTEGER"),
    ("lead_drafts", "name_confidence", "VARCHAR(20)"),
    ("lead_drafts", "phone_confidence", "VARCHAR(20)"),
    ("lead_drafts", "conflict_flags", "TEXT"),
    ("lead_drafts", "duplicate_lead_id", "INTEGER"),
)

# (index_name, table, column)
ADDITIVE_INDEXES: tuple[tuple[str, str, str], ...] = (
    ("ix_import_logs_batch_id", "import_logs", "batch_id"),
    ("ix_lead_drafts_batch_id", "lead_drafts", "batch_id"),
)


def _existing_columns(engine: Engine, table: str) -> set[str]:
    """Return the current column names of a table, or an empty set if absent."""
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def apply_additive_migrations(engine: Engine) -> dict:
    """Add any missing v0.2.1 columns and indexes.

    Returns a summary dict: {"added_columns": [...], "added_indexes": [...],
    "skipped_columns": [...]}. Safe to call on every startup.
    """
    added_columns: list[str] = []
    skipped_columns: list[str] = []
    added_indexes: list[str] = []

    for table, column, column_type in ADDITIVE_COLUMNS:
        columns = _existing_columns(engine, table)
        if not columns:
            # Table does not exist yet — create_all will build it complete.
            skipped_columns.append(f"{table}.{column} (table missing)")
            continue
        if column in columns:
            skipped_columns.append(f"{table}.{column} (already present)")
            continue

        with engine.begin() as conn:
            conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
            )
        added_columns.append(f"{table}.{column}")
        logger.info("Migration %s: added column %s.%s", MIGRATION_VERSION, table, column)

    for index_name, table, column in ADDITIVE_INDEXES:
        columns = _existing_columns(engine, table)
        if column not in columns:
            continue
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column})"
                )
            )
        added_indexes.append(index_name)

    if added_columns:
        logger.info(
            "Migration %s applied: %s", MIGRATION_VERSION, ", ".join(added_columns)
        )
    else:
        logger.info("Migration %s: schema already up to date", MIGRATION_VERSION)

    return {
        "version": MIGRATION_VERSION,
        "added_columns": added_columns,
        "added_indexes": added_indexes,
        "skipped_columns": skipped_columns,
    }


def verify_schema(engine: Engine) -> list[str]:
    """Return the list of expected v0.2.1 columns that are still missing."""
    missing: list[str] = []
    for table, column, _ in ADDITIVE_COLUMNS:
        columns = _existing_columns(engine, table)
        if not columns or column not in columns:
            missing.append(f"{table}.{column}")

    inspector = inspect(engine)
    if "resume_import_batches" not in inspector.get_table_names():
        missing.append("resume_import_batches (table)")
    return missing
