"""Tests for the additive-only migration.

Requirement 29/30: the production upgrade must add columns without touching a
single existing row, and must be safe to run repeatedly.
"""

from sqlalchemy import create_engine, inspect, text

from app.core.db_migrations import (
    ADDITIVE_COLUMNS,
    apply_additive_migrations,
    verify_schema,
)


def _make_v020_database(path) -> object:
    """Build a database shaped like production BEFORE v0.2.1, with data in it."""
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE import_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name VARCHAR(255) NOT NULL,
                    file_type VARCHAR(20) NOT NULL,
                    file_size INTEGER,
                    temp_file_path VARCHAR(500),
                    parse_status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    parse_error TEXT,
                    extracted_text_length INTEGER,
                    llm_used INTEGER NOT NULL DEFAULT 0,
                    llm_provider VARCHAR(100),
                    temp_file_expires_at VARCHAR(50),
                    file_deleted_at VARCHAR(50),
                    created_by INTEGER,
                    created_at VARCHAR(50) NOT NULL,
                    updated_at VARCHAR(50) NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE lead_drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    import_log_id INTEGER,
                    name VARCHAR(255),
                    phone VARCHAR(50),
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    confirmed_lead_id INTEGER,
                    created_by INTEGER,
                    created_at VARCHAR(50) NOT NULL,
                    updated_at VARCHAR(50) NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO import_logs "
                "(file_name, file_type, parse_status, created_at, updated_at) "
                "VALUES ('old.docx', 'docx', 'parsed', '2026-01-01 00:00:00', "
                "'2026-01-01 00:00:00')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO lead_drafts "
                "(name, phone, status, created_at, updated_at) "
                "VALUES ('历史线索', '13800008888', 'pending', "
                "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
            )
        )
    return engine


def test_migration_adds_columns_without_losing_rows(tmp_path):
    engine = _make_v020_database(tmp_path / "legacy.db")

    with engine.connect() as conn:
        before_logs = conn.execute(text("SELECT COUNT(*) FROM import_logs")).scalar_one()
        before_drafts = conn.execute(text("SELECT COUNT(*) FROM lead_drafts")).scalar_one()

    result = apply_additive_migrations(engine)
    assert len(result["added_columns"]) == len(ADDITIVE_COLUMNS)

    inspector = inspect(engine)
    log_columns = {c["name"] for c in inspector.get_columns("import_logs")}
    draft_columns = {c["name"] for c in inspector.get_columns("lead_drafts")}
    assert {"batch_id", "error_code"} <= log_columns
    assert {
        "batch_id", "name_confidence", "phone_confidence",
        "conflict_flags", "duplicate_lead_id",
    } <= draft_columns

    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM import_logs")).scalar_one() == before_logs
        assert conn.execute(text("SELECT COUNT(*) FROM lead_drafts")).scalar_one() == before_drafts

        # Old data is intact and the new columns read back as NULL.
        row = conn.execute(
            text("SELECT name, phone, batch_id, name_confidence FROM lead_drafts")
        ).first()
        assert row[0] == "历史线索"
        assert row[1] == "13800008888"
        assert row[2] is None
        assert row[3] is None


def test_migration_is_idempotent(tmp_path):
    engine = _make_v020_database(tmp_path / "twice.db")

    first = apply_additive_migrations(engine)
    second = apply_additive_migrations(engine)

    assert len(first["added_columns"]) == len(ADDITIVE_COLUMNS)
    assert second["added_columns"] == []
    assert len(second["skipped_columns"]) == len(ADDITIVE_COLUMNS)

    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM lead_drafts")).scalar_one() == 1


def test_migration_skips_absent_tables(tmp_path):
    """A brand-new database has no tables yet — nothing should blow up."""
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    result = apply_additive_migrations(engine)

    assert result["added_columns"] == []
    assert all("table missing" in s for s in result["skipped_columns"])


def test_verify_schema_reports_missing_objects(tmp_path):
    engine = _make_v020_database(tmp_path / "verify.db")

    missing = verify_schema(engine)
    assert "lead_drafts.batch_id" in missing
    assert "resume_import_batches (table)" in missing

    apply_additive_migrations(engine)
    # The batches table is created by create_all, not by this function.
    assert verify_schema(engine) == ["resume_import_batches (table)"]


def test_live_test_database_is_fully_migrated(client):
    """The app's own startup hook must leave the schema complete."""
    from app.database import engine as app_engine

    assert verify_schema(app_engine) == []
