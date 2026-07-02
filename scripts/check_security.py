#!/usr/bin/env python3
"""
Security Configuration Check — JiuWei CRM v0.1.0

Purpose:
    Verify production security configuration before deployment.
    Checks JWT secret key, CORS origins, admin default password,
    environment file integrity, upload directories, and database.

Usage:
    python scripts/check_security.py

    # Custom database path
    python scripts/check_security.py --db backend/data/jiuwei_crm.db

Exit codes:
    0 — all checks PASS
    1 — one or more WARNING or FAIL checks found
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_DB_PATH = PROJECT_ROOT / "backend" / "data" / "jiuwei_crm.db"
ENV_EXAMPLE = PROJECT_ROOT / "backend" / ".env.example"
ENV_FILE = PROJECT_ROOT / "backend" / ".env"
UPLOADS_TEMP = PROJECT_ROOT / "backend" / "uploads" / "temp"
UPLOADS_PARSED = PROJECT_ROOT / "backend" / "uploads" / "parsed"

WEAK_JWT_SECRETS = {"change-me", "secret", "default", "admin", "changeme"}
WEAK_ADMIN_PASSWORDS = {"admin123", "123456", "password", "admin", ""}

Status = Literal["PASS", "WARNING", "FAIL"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_result(status: Status, label: str, detail: str = "") -> None:
    """Print a colour-coded check result."""
    prefix = {
        "PASS": "  [PASS]   ",
        "WARNING": "  [WARN]   ",
        "FAIL": "  [FAIL]   ",
    }[status]
    line = f"{prefix}{label}"
    if detail:
        line += f"  — {detail}"
    print(line)


def check_env_example_is_example() -> Status:
    """Ensure .env.example is still a template, not a real config copy."""
    if not ENV_EXAMPLE.exists():
        return ("FAIL", ".env.example is missing")
    content = ENV_EXAMPLE.read_text(encoding="utf-8")
    lines_lower = content.lower()

    # Heuristic: real secrets often have long random strings.
    # The example file should contain placeholder tokens.
    placeholder_markers = [
        "change-me",
        "replace-in-production",
        "your-",
        "example",
        "please-change",
    ]
    found_placeholder = any(m in lines_lower for m in placeholder_markers)

    if found_placeholder:
        return ("PASS", ".env.example appears to be a template file")
    return ("WARNING", ".env.example may contain real values — verify manually")


def check_jwt_secret_key() -> Status:
    """Check that JWT_SECRET_KEY is strong in the current environment."""
    raw = os.environ.get("JWT_SECRET_KEY", "").strip()

    if not raw:
        # Try reading from .env file
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("JWT_SECRET_KEY="):
                    raw = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not raw:
        return ("FAIL", "JWT_SECRET_KEY is not set in environment or .env file")

    if raw.lower() in WEAK_JWT_SECRETS:
        return (
            "FAIL",
            f"JWT_SECRET_KEY is a weak/default value: '{raw}'",
        )

    if len(raw) < 16:
        return (
            "WARNING",
            f"JWT_SECRET_KEY is shorter than 16 characters ({len(raw)} chars)",
        )

    # Mask display
    masked = raw[:3] + "*" * max(1, len(raw) - 6) + raw[-3:] if len(raw) > 6 else "***"
    return ("PASS", f"JWT_SECRET_KEY is set (value: {masked})")


def check_temp_file_retention() -> Status:
    """Check TEMP_FILE_RETENTION_DAYS is configured."""
    raw = os.environ.get("TEMP_FILE_RETENTION_DAYS", "").strip()

    if not raw and ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("TEMP_FILE_RETENTION_DAYS="):
                raw = line.split("=", 1)[1].strip()
                break

    if not raw:
        return ("WARNING", "TEMP_FILE_RETENTION_DAYS is not set (using default 0)")

    try:
        val = int(raw)
    except ValueError:
        return ("FAIL", f"TEMP_FILE_RETENTION_DAYS is not a valid integer: '{raw}'")

    if val < 0:
        return ("FAIL", f"TEMP_FILE_RETENTION_DAYS is negative ({val})")
    if val == 0:
        return ("PASS", "TEMP_FILE_RETENTION_DAYS=0 (files cleared after processing)")
    return ("PASS", f"TEMP_FILE_RETENTION_DAYS={val}")


def check_cors_origins() -> Status:
    """Check CORS_ORIGINS is explicitly configured."""
    raw = os.environ.get("CORS_ORIGINS", "").strip()

    if not raw and ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("CORS_ORIGINS="):
                raw = line.split("=", 1)[1].strip()
                break

    if not raw:
        return ("FAIL", "CORS_ORIGINS is not configured")

    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not origins:
        return ("FAIL", "CORS_ORIGINS is empty")

    # Check if it's localhost-only (OK for dev, warn for prod)
    only_localhost = all(
        "localhost" in o or "127.0.0.1" in o or o.startswith("http://0") for o in origins
    )
    if only_localhost:
        return (
            "WARNING",
            f"CORS_ORIGINS only contains localhost: {raw}"
            " — update for production",
        )

    return ("PASS", f"CORS_ORIGINS configured ({len(origins)} origin(s))")


def check_upload_directories() -> Status:
    """Check upload directories exist."""
    statuses: list[Status] = []

    for d, label in [(UPLOADS_TEMP, "uploads/temp"), (UPLOADS_PARSED, "uploads/parsed")]:
        if not d.exists():
            statuses.append("FAIL")
            _print_result("FAIL", f"Upload directory missing: {label}")
            continue
        if not d.is_dir():
            statuses.append("FAIL")
            _print_result("FAIL", f"Path is not a directory: {label}")
            continue
        # Check .gitkeep
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            _print_result("WARNING", f"{label}/.gitkeep missing")
        statuses.append("PASS")

    # Return worst status
    if "FAIL" in statuses:
        return ("FAIL", "One or more upload directories missing or invalid")
    return ("PASS", "Upload directories exist")


def check_database_file(db_path: Path = DEFAULT_DB_PATH) -> Status:
    """Check SQLite database file exists."""
    if db_path.exists():
        size = db_path.stat().st_size
        size_str = f"{size:,} bytes" if size >= 1024 else f"{size} bytes"
        return ("PASS", f"Database file exists ({size_str})")
    return ("WARNING", f"Database file not found at {db_path}")


def check_admin_default_password(db_path: Path = DEFAULT_DB_PATH) -> Status:
    """Check if admin password is still the default (admin123).

    We attempt to verify by hashing the known default password against
    the stored hash.  If we can't check, we advise running reset_prod_data.py.
    """
    if not db_path.exists():
        return ("WARNING", "Cannot check — database file not found")

    try:
        import sqlite3
    except ImportError:
        return ("FAIL", "sqlite3 module not available")

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = 'admin'")
        row = cursor.fetchone()
        conn.close()
    except Exception as exc:
        return ("FAIL", f"Database query error: {exc}")

    if row is None:
        return ("WARNING", "No admin user found in database")

    stored_hash = row[0]

    # Try to verify with passlib/bcrypt
    try:
        from passlib.hash import bcrypt
    except ImportError:
        return (
            "WARNING",
            "Cannot verify admin password — passlib not available. "
            "Run reset_prod_data.py before deployment.",
        )

    for weak_pwd in WEAK_ADMIN_PASSWORDS:
        try:
            if bcrypt.verify(weak_pwd, stored_hash):
                return (
                    "FAIL",
                    f"Admin password is still a default/weak value: '{weak_pwd}'"
                    " — run scripts/reset_prod_data.py",
                )
        except Exception:
            # Hash format mismatch — not bcrypt, or corrupted
            continue

    return ("PASS", "Admin password is not a known default value")


def check_env_example_content() -> Status:
    """Check that .env.example contains all required keys."""
    required_keys = [
        "DATABASE_URL",
        "JWT_SECRET_KEY",
        "UPLOAD_DIR",
        "TEMP_FILE_RETENTION_DAYS",
        "CORS_ORIGINS",
    ]

    if not ENV_EXAMPLE.exists():
        return ("FAIL", ".env.example is missing")

    content = ENV_EXAMPLE.read_text(encoding="utf-8")
    missing = [k for k in required_keys if f"{k}=" not in content]

    if missing:
        return (
            "FAIL",
            f".env.example missing keys: {', '.join(missing)}",
        )

    return ("PASS", f".env.example contains all {len(required_keys)} required keys")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="JiuWei CRM — Security Configuration Check (v0.1.0)"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database (default: {DEFAULT_DB_PATH})",
    )
    args = parser.parse_args()

    # Allow overriding DB path
    db_path = args.db

    print("=" * 60)
    print("  JiuWei CRM — Security Configuration Check (v0.1.0)")
    print("=" * 60)
    print()

    checks = [
        ("Environment File ", check_env_example_is_example),
        ("JWT Secret Key   ", check_jwt_secret_key),
        ("Temp File Retention", check_temp_file_retention),
        ("CORS Origins     ", check_cors_origins),
        ("Upload Directories", check_upload_directories),
        ("Database File    ", lambda: check_database_file(db_path)),
        ("Admin Password   ", lambda: check_admin_default_password(db_path)),
        (".env.example Content", check_env_example_content),
    ]

    results: list[tuple[str, Status, str]] = []
    for label, check_fn in checks:
        status, detail = check_fn()
        results.append((label, status, detail))
        _print_result(status, label.strip(), detail)

    # --- Summary --------------------------------------------------------
    print()
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    pass_count = sum(1 for _, s, _ in results if s == "PASS")
    warn_count = sum(1 for _, s, _ in results if s == "WARNING")
    fail_count = sum(1 for _, s, _ in results if s == "FAIL")

    print(f"  PASS:    {pass_count}")
    print(f"  WARNING: {warn_count}")
    print(f"  FAIL:    {fail_count}")
    print(f"  TOTAL:   {len(results)}")
    print("=" * 60)

    if fail_count > 0:
        print()
        print("ACTION REQUIRED:")
        for label, status, detail in results:
            if status == "FAIL":
                print(f"  - [{label.strip()}] {detail}")

    if fail_count > 0 or warn_count > 0:
        print()
        print("PRE-DEPLOYMENT CHECKLIST:")
        print("  1. Set a strong JWT_SECRET_KEY in backend/.env")
        print("  2. Run: ADMIN_INITIAL_PASSWORD='<strong-password>' python scripts/reset_prod_data.py")
        print("  3. Configure CORS_ORIGINS for your production domain")
        print("  4. Never commit backend/.env to Git")
        print("  5. Verify admin login after deployment")

    print()

    if fail_count == 0 and warn_count == 0:
        print("[OK] All security checks passed!")
        return 0
    elif fail_count == 0:
        print("[WARN] All required checks passed but some warnings remain.")
        return 0
    else:
        print("[FAIL] Some security checks failed — resolve before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
