#!/usr/bin/env python3
"""JiuWei CRM v0.2.1 migration — Resume Batch Import.

WHAT THIS SCRIPT DOES
    1. Backs up the SQLite database file (sqlite only).
    2. Records row counts of every business table BEFORE the change.
    3. Creates the new table `resume_import_batches` if it does not exist.
    4. Adds the new nullable columns to `import_logs` and `lead_drafts`.
    5. Records row counts AFTER the change and refuses to report success if
       any table lost rows.

WHAT THIS SCRIPT WILL NEVER DO
    No DROP, no DELETE, no TRUNCATE, no table rebuild, no data rewrite.
    Every change is additive. Existing rows are untouched and read back with
    NULL in the new columns.

USAGE (inside the backend container or the backend virtualenv)
    python -m migrations.v0_2_1_resume_batch_import            # apply
    python -m migrations.v0_2_1_resume_batch_import --check    # dry run
    python -m migrations.v0_2_1_resume_batch_import --no-backup

EXIT CODES
    0  success / nothing to do
    1  --check detected a required migration
    2  data loss detected (row count decreased)
    3  migration incomplete (schema still missing objects)
    4  backup failed (refusing to modify the schema without a verified backup)

ROLLBACK
    See backend/migrations/README.md. The short version: the new columns are
    nullable and ignored by v0.2.0 code, so rolling the application back does
    not require rolling the schema back. If you must, restore the backup file
    printed by this script.
"""

import argparse
import datetime
import os
import sqlite3
import sys
from pathlib import Path

# Allow running as `python migrations/v0_2_1_resume_batch_import.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.db_migrations import (  # noqa: E402
    ADDITIVE_COLUMNS,
    MIGRATION_VERSION,
    apply_additive_migrations,
    verify_schema,
)
from app.database import Base, engine  # noqa: E402
import app.models  # noqa: F401,E402  (registers every model on Base.metadata)

COUNTED_TABLES = (
    "users",
    "leads",
    "lead_followups",
    "lead_drafts",
    "import_logs",
    "courses",
    "lead_sources",
    "system_settings",
)


def sqlite_path() -> Path | None:
    """Return the on-disk path of the SQLite database, if we are on SQLite."""
    url = settings.DATABASE_URL
    if not url.startswith("sqlite"):
        return None
    raw = url.split("sqlite:///")[-1]
    return Path(raw).resolve()


class BackupError(RuntimeError):
    """Raised when a required SQLite backup cannot be created or verified."""


def backup_database() -> Path | None:
    """Create a consistent snapshot of the live SQLite DB via its backup API.

    Uses SQLite's official online backup (``sqlite3.Connection.backup``) rather
    than copying the file, so the snapshot is transactionally consistent even
    while the production database is being read/written. The live database is
    never stopped, deleted or rebuilt.

    Returns the backup path, or ``None`` when there is nothing to back up
    (non-SQLite backend, or the database file does not exist yet). Raises
    ``BackupError`` if the backup cannot be created or verified.
    """
    db_path = sqlite_path()
    if db_path is None:
        print("[backup] DATABASE_URL is not SQLite — back up with your DB tooling.")
        return None
    if not db_path.exists():
        print(f"[backup] No database file at {db_path} — nothing to back up.")
        return None

    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    target = db_path.with_name(f"{db_path.name}.bak-{MIGRATION_VERSION}-{stamp}")

    try:
        src = sqlite3.connect(str(db_path))
        try:
            dst = sqlite3.connect(str(target))
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
    except sqlite3.Error as exc:
        raise BackupError(f"could not back up {db_path} -> {target}: {exc}") from exc

    # Verify the backup exists and opens cleanly before touching the schema.
    if not target.exists():
        raise BackupError(f"backup file was not created at {target}")

    try:
        check = sqlite3.connect(str(target))
        try:
            result = check.execute("PRAGMA quick_check").fetchone()
            if result is None or result[0] != "ok":
                raise BackupError(
                    f"backup at {target} failed quick_check: {result}"
                )
        finally:
            check.close()
    except sqlite3.Error as exc:
        raise BackupError(f"backup at {target} does not open: {exc}") from exc

    size_mb = os.path.getsize(target) / 1024 / 1024
    print(f"[backup] {db_path}  ->  {target}  ({size_mb:.2f} MB)")
    return target


def row_counts() -> dict[str, int]:
    """Count rows in every business table that exists."""
    inspector = inspect(engine)
    present = set(inspector.get_table_names())
    counts: dict[str, int] = {}
    with engine.connect() as conn:
        for table in COUNTED_TABLES:
            if table not in present:
                continue
            counts[table] = conn.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            ).scalar_one()
    return counts


def print_counts(title: str, counts: dict[str, int]) -> None:
    print(f"\n[{title}]")
    for table, count in counts.items():
        print(f"    {table:<20} {count:>8}")


def main() -> int:
    parser = argparse.ArgumentParser(description=f"JiuWei CRM {MIGRATION_VERSION} migration")
    parser.add_argument(
        "--check", action="store_true", help="report what is missing, change nothing"
    )
    parser.add_argument(
        "--no-backup", action="store_true", help="skip the SQLite file backup"
    )
    args = parser.parse_args()

    print(f"JiuWei CRM migration {MIGRATION_VERSION} — Resume Batch Import")
    print(f"Database: {settings.DATABASE_URL}")

    missing = verify_schema(engine)
    if args.check:
        if missing:
            print("\n[check] Missing schema objects:")
            for item in missing:
                print(f"    - {item}")
            print("\n[check] Migration is REQUIRED.")
            return 1
        print("\n[check] Schema is already at v0.2.1. Nothing to do.")
        return 0

    if not missing:
        print("\nSchema is already at v0.2.1. Nothing to do.")
        return 0

    print("\nMissing schema objects:")
    for item in missing:
        print(f"    - {item}")

    before = row_counts()
    print_counts("row counts BEFORE", before)

    backup_path = None
    if not args.no_backup:
        print()
        try:
            backup_path = backup_database()
        except BackupError as exc:
            print(f"\n!! Backup failed: {exc}")
            print("!! Refusing to modify the schema without a verified backup.")
            print("!! Fix the backup issue, or pass --no-backup if you have your own backup.")
            return 4

    # 1. New tables only. create_all never alters an existing table.
    print("\n[schema] Creating any missing tables (additive)...")
    Base.metadata.create_all(bind=engine)

    # 2. New columns on existing tables.
    print("[schema] Adding missing columns (additive)...")
    result = apply_additive_migrations(engine)
    for column in result["added_columns"]:
        print(f"    + {column}")
    if not result["added_columns"]:
        print("    (no columns needed)")
    for index in result["added_indexes"]:
        print(f"    + index {index}")

    after = row_counts()
    print_counts("row counts AFTER", after)

    lost = [
        table
        for table, count in before.items()
        if after.get(table, 0) < count
    ]
    if lost:
        print(f"\n!! DATA LOSS DETECTED in: {', '.join(lost)}")
        if backup_path:
            print(f"!! Restore immediately from: {backup_path}")
        return 2

    still_missing = verify_schema(engine)
    if still_missing:
        print(f"\n!! Migration incomplete, still missing: {still_missing}")
        return 3

    expected = ", ".join(f"{t}.{c}" for t, c, _ in ADDITIVE_COLUMNS)
    print("\n[verify] All row counts preserved.")
    print(f"[verify] Schema now at {MIGRATION_VERSION}.")
    print(f"[verify] Columns present: {expected}")
    if backup_path:
        print(f"[verify] Backup kept at: {backup_path}")
    print("\nMigration completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
