#!/usr/bin/env python3
"""
Production Data Reset Script — JiuWei CRM v0.1.0

Purpose:
    Clean up all test/business data before production deployment.
    Reset admin password, clear leads/followups/drafts/import_logs,
    remove non-admin users, and clean temporary upload directories.

Usage:
    # Interactive password input
    python scripts/reset_prod_data.py

    # With environment variable
    ADMIN_INITIAL_PASSWORD='StrongPassword123!' python scripts/reset_prod_data.py

    # Custom database path
    python scripts/reset_prod_data.py --db backend/data/jiuwei_crm.db

Configuration:
    - ADMIN_INITIAL_PASSWORD (env): new admin password
    - Falls back to interactive terminal input if env var is not set

Password Requirements:
    - Minimum 8 characters
    - Must not be: admin123, 123456, password, or empty
"""

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path resolution — resolve relative to project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_DB_PATH = PROJECT_ROOT / "backend" / "data" / "jiuwei_crm.db"
UPLOADS_TEMP = PROJECT_ROOT / "backend" / "uploads" / "temp"
UPLOADS_PARSED = PROJECT_ROOT / "backend" / "uploads" / "parsed"

FORBIDDEN_PASSWORDS = {"admin123", "123456", "password"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def require_sqlite():
    """Late-import sqlite3 so we can give a clear error message."""
    try:
        import sqlite3
        return sqlite3
    except ImportError as exc:
        sys.exit("ERROR: sqlite3 module is required (bundled with Python).")


def require_bcrypt():
    """Import passlib/bcrypt for password hashing."""
    try:
        from passlib.hash import bcrypt as _bcrypt
        return _bcrypt
    except ImportError:
        sys.exit(
            "ERROR: passlib with bcrypt is required.\n"
            "       Install it with: pip install passlib[bcrypt]"
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="JiuWei CRM — Production Data Reset (v0.1.0)"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database (default: {DEFAULT_DB_PATH})",
    )
    return parser.parse_args()


def read_password() -> str:
    """Read new admin password, preferring env var over interactive input."""
    env_val = os.environ.get("ADMIN_INITIAL_PASSWORD", "").strip()
    if env_val:
        print("[INFO] Using password from ADMIN_INITIAL_PASSWORD environment variable.")
        return env_val

    print("[INPUT] Enter new admin password (minimum 8 characters):")
    try:
        pwd = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n[ABORT] Password input cancelled.")
        sys.exit(1)
    return pwd


def validate_password(password: str) -> None:
    """Raise SystemExit if the password fails validation."""
    if not password:
        sys.exit("ERROR: Password must not be empty.")

    if len(password) < 8:
        sys.exit("ERROR: Password must be at least 8 characters long.")

    if password.lower() in FORBIDDEN_PASSWORDS:
        sys.exit(
            f"ERROR: Password must not be one of: "
            f"{', '.join(sorted(FORBIDDEN_PASSWORDS))}"
        )

    # Friendly warning for common weak patterns
    weak_hints = []
    if password.isdigit():
        weak_hints.append("password is all digits")
    if password.isalpha():
        weak_hints.append("password is all letters")
    if password.lower() == password:
        weak_hints.append("password has no uppercase letters")
    if weak_hints:
        print(f"[WARNING] Weak password detected: {'; '.join(weak_hints)}.")
        print("          Consider using a stronger password for production.")
        try:
            confirm = input("Continue anyway? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n[ABORT] Cancelled.")
            sys.exit(1)
        if confirm not in ("y", "yes"):
            sys.exit("[ABORT] Password rejected by user.")


def hash_password(password: str) -> str:
    """Generate a bcrypt hash for the given password."""
    bcrypt = require_bcrypt()
    return bcrypt.hash(password)


def clean_directory(dir_path: Path) -> int:
    """Delete all files in *dir_path* except .gitkeep.  Return count of removed files."""
    if not dir_path.exists():
        print(f"[WARNING] Directory does not exist, skipping: {dir_path}")
        return 0

    removed = 0
    for item in dir_path.iterdir():
        if item.name == ".gitkeep":
            continue
        try:
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                import shutil
                shutil.rmtree(item)
            removed += 1
        except OSError as exc:
            print(f"[WARNING] Failed to remove {item}: {exc}")
    return removed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    db_path: Path = args.db

    # --- Validate database existence ---------------------------------------
    if not db_path.exists():
        sys.exit(f"ERROR: Database file not found: {db_path}")

    sqlite3 = require_sqlite()

    print("=" * 60)
    print("  JiuWei CRM — Production Data Reset (v0.1.0)")
    print("=" * 60)
    print(f"  Database : {db_path}")
    print(f"  Uploads  : {UPLOADS_TEMP}")
    print(f"  Parsed   : {UPLOADS_PARSED}")
    print("-" * 60)

    # --- Password ----------------------------------------------------------
    raw_password = read_password()
    validate_password(raw_password)
    password_hash = hash_password(raw_password)
    print("[OK] Password validated and hashed (bcrypt).")

    # --- Connect -----------------------------------------------------------
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    stats: dict[str, int] = {}

    try:
        # --- 1. Delete business data tables --------------------------------
        tables = [
            ("lead_followups", "跟进记录"),
            ("lead_drafts", "线索草稿"),
            ("import_logs", "导入日志"),
            ("leads", "线索"),
        ]

        for table_name, label in tables:
            cursor.execute(f"DELETE FROM {table_name}")
            stats[table_name] = cursor.rowcount
            print(f"  [CLEARED] {label} ({table_name}): {cursor.rowcount} rows")

        # --- 2. Delete non-admin users -------------------------------------
        cursor.execute("SELECT id, username, role FROM users WHERE role != 'admin'")
        non_admin_users = cursor.fetchall()
        if non_admin_users:
            cursor.execute("DELETE FROM users WHERE role != 'admin'")
            stats["non_admin_users"] = cursor.rowcount
            for uid, uname, role in non_admin_users:
                print(f"  [REMOVED] User: {uname} (id={uid}, role={role})")
        else:
            stats["non_admin_users"] = 0
            print("  [SKIP] No non-admin users to remove.")

        # --- 3. Ensure admin exists & is active ----------------------------
        cursor.execute("SELECT id, username, is_active FROM users WHERE role = 'admin'")
        admin_rows = cursor.fetchall()

        if not admin_rows:
            print("[WARNING] No admin user found! Check database integrity.")
            stats["admin_reset"] = 0
        else:
            for admin_id, admin_username, admin_active in admin_rows:
                cursor.execute(
                    "UPDATE users SET password_hash = ?, is_active = 1, updated_at = datetime('now','localtime') WHERE id = ?",
                    (password_hash, admin_id),
                )
                print(
                    f"  [RESET] Admin password for: {admin_username} (id={admin_id}, "
                    f"was_active={'yes' if admin_active else 'no'})"
                )
            stats["admin_reset"] = len(admin_rows)

        # --- 4. Preserved tables (report only) -----------------------------
        preserved = {
            "lead_sources": "线索来源",
            "courses": "意向课程",
            "system_settings": "系统配置",
        }
        for table_name, label in preserved.items():
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  [KEPT] {label} ({table_name}): {count} rows")

        conn.commit()
        print("-" * 60)

        # --- 5. Clean upload directories -----------------------------------
        temp_removed = clean_directory(UPLOADS_TEMP)
        parsed_removed = clean_directory(UPLOADS_PARSED)
        stats["uploads_temp_removed"] = temp_removed
        stats["uploads_parsed_removed"] = parsed_removed
        print(f"  [CLEANED] uploads/temp: {temp_removed} files")
        print(f"  [CLEANED] uploads/parsed: {parsed_removed} files")

    except Exception as exc:
        conn.rollback()
        sys.exit(f"ERROR: {exc}")
    finally:
        conn.close()

    # --- 6. Summary --------------------------------------------------------
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  leads            : {stats.get('leads', 0)} rows deleted")
    print(f"  lead_followups   : {stats.get('lead_followups', 0)} rows deleted")
    print(f"  lead_drafts      : {stats.get('lead_drafts', 0)} rows deleted")
    print(f"  import_logs      : {stats.get('import_logs', 0)} rows deleted")
    print(f"  non-admin users  : {stats.get('non_admin_users', 0)} removed")
    print(f"  admin accounts   : {stats.get('admin_reset', 0)} password(s) reset")
    print(f"  uploads/temp     : {stats.get('uploads_temp_removed', 0)} files removed")
    print(f"  uploads/parsed   : {stats.get('uploads_parsed_removed', 0)} files removed")
    print("-" * 60)
    print("  Preserved:")
    print("    - lead_sources (线索来源)")
    print("    - courses (意向课程)")
    print("    - system_settings (系统配置)")
    print("    - .gitkeep files")
    print("=" * 60)
    print("[DONE] Production data reset completed successfully.")
    print()
    print("NEXT STEPS:")
    print("  1. Verify login with the new admin password.")
    print("  2. Run: python scripts/check_security.py")
    print("  3. Set a strong JWT_SECRET_KEY in backend/.env")
    print("  4. Configure CORS_ORIGINS for your production domain.")


if __name__ == "__main__":
    main()
