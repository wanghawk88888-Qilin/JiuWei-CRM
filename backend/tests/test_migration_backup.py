"""Tests for the v0.2.1 migration's SQLite backup and startup behavior.

The production safety closure requires two guarantees:
  * the migration backs up the live SQLite database with the official backup
    API (not a raw file copy), producing a valid, row-for-row consistent file;
  * the backend startup no longer auto-applies additive migrations.
"""

import sqlite3

from migrations.v0_2_1_resume_batch_import import (
    COUNTED_TABLES,
    backup_database,
    row_counts,
    sqlite_path,
)

# Every table created by Base.metadata.create_all that holds business data.
KEY_TABLES = (
    "users",
    "leads",
    "lead_followups",
    "lead_drafts",
    "import_logs",
    "resume_import_batches",
)


def _seed_business_rows(path) -> None:
    """Insert known rows into a couple of business tables via a raw connection."""
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO import_logs "
            "(file_name, file_type, parse_status, llm_used, created_at, updated_at) "
            "VALUES ('a.docx', 'docx', 'parsed', 0, "
            "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
        )
        cur.execute(
            "INSERT INTO import_logs "
            "(file_name, file_type, parse_status, llm_used, created_at, updated_at) "
            "VALUES ('b.pdf', 'pdf', 'parsed', 0, "
            "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
        )
        cur.execute(
            "INSERT INTO lead_drafts "
            "(name, phone, status, created_at, updated_at) "
            "VALUES ('张三', '13800001111', 'pending', "
            "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
        )
        conn.commit()
    finally:
        conn.close()


def _counts(path, tables) -> dict[str, int]:
    conn = sqlite3.connect(str(path))
    try:
        return {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in tables
        }
    finally:
        conn.close()


def test_sqlite_backup_produces_valid_database(client):
    """The backup must be an openable, integrity-clean SQLite database file."""
    backup_path = backup_database()
    assert backup_path is not None, "SQLite backup should produce a file"
    assert backup_path.exists()

    conn = sqlite3.connect(str(backup_path))
    try:
        result = conn.execute("PRAGMA quick_check").fetchone()
        assert result is not None and result[0] == "ok", result

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "leads" in tables and "import_logs" in tables
    finally:
        conn.close()


def test_sqlite_backup_preserves_key_table_row_counts(client):
    """Backup row counts must match the live source database exactly."""
    db_path = sqlite_path()
    assert db_path is not None and db_path.exists()

    _seed_business_rows(db_path)

    before = _counts(db_path, KEY_TABLES)
    backup_path = backup_database()
    assert backup_path is not None

    after = _counts(backup_path, KEY_TABLES)
    assert after == before, f"row counts diverged: source={before} backup={after}"


def test_counted_tables_names_lead_followups():
    """The follow-up table is named `lead_followups`, not `followups`."""
    assert "lead_followups" in COUNTED_TABLES
    assert "followups" not in COUNTED_TABLES


def test_row_counts_tracks_lead_followups_across_migration(client, db):
    """`row_counts` must count `lead_followups` and keep it stable.

    Regression for the bug where COUNTED_TABLES listed "followups" (a table
    that does not exist): row_counts() silently skipped it, so the follow-up
    table was never checked for data loss.
    """
    from app.core.db_migrations import apply_additive_migrations
    from app.database import engine
    from app.models.followup import FollowUp

    db.add(
        FollowUp(
            lead_id=1,
            followup_type="call",
            content="电话跟进",
            created_by=1,
        )
    )
    db.commit()

    before = row_counts()["lead_followups"]
    assert before >= 1

    # Re-applying the additive migration must not change the row count.
    apply_additive_migrations(engine)

    after = row_counts()["lead_followups"]
    assert after == before


def test_lifespan_does_not_call_apply_additive_migrations():
    """Backend startup must not auto-modify an existing production schema."""
    import inspect

    import app.main as main

    # No module-level import of the migration hook...
    assert not hasattr(main, "apply_additive_migrations"), (
        "app.main must not import apply_additive_migrations"
    )
    # ...and no call to it inside the lifespan startup path.
    lifespan_src = inspect.getsource(main.lifespan)
    assert "apply_additive_migrations" not in lifespan_src, (
        "lifespan must not call apply_additive_migrations on startup"
    )
