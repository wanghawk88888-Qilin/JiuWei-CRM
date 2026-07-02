# Production Initialization — JiuWei CRM v0.1.0

> **Target Audience:** DevOps / Backend engineers preparing JiuWei CRM v0.1.0 for its first production deployment.

---

## 1. Why Initialize Before Production?

During development and testing, the database accumulates:

- Test leads, follow-ups, and draft records that should not appear in production
- Test user accounts with weak passwords
- Import logs and temporary files from development sessions

Running the production initialization script ensures a **clean, secure starting state** for the v0.1.0 launch.

---

## 2. What Gets Preserved

| Category | Table / Path | Description |
|----------|-------------|-------------|
| Admin account | `users` (role=admin) | Password is reset, account remains active |
| Lead sources | `lead_sources` | Default source definitions |
| Courses | `courses` | Default course catalog |
| System settings | `system_settings` | Default configuration values |
| Git keepers | `.gitkeep` | Preserve directory structure markers |

---

## 3. What Gets Cleared

| Category | Table / Path | Description |
|----------|-------------|-------------|
| Leads | `leads` | All lead records deleted |
| Follow-ups | `lead_followups` | All follow-up records deleted |
| Drafts | `lead_drafts` | All resume import drafts deleted |
| Import logs | `import_logs` | All import history deleted |
| Non-admin users | `users` (role≠admin) | All non-admin user accounts deleted |
| Temp uploads | `uploads/temp/*` | All except `.gitkeep` |
| Parsed files | `uploads/parsed/*` | All except `.gitkeep` |

---

## 4. How to Run

### 4.1 Reset Production Data

#### Option A: Environment Variable (recommended for automation)

```bash
ADMIN_INITIAL_PASSWORD='YourStrongPassword123!' python scripts/reset_prod_data.py
```

#### Option B: Interactive Input

```bash
python scripts/reset_prod_data.py
```

The script will prompt you to enter a new admin password.  The password is **never echoed** to the terminal, and is stored as a bcrypt hash.

#### Custom Database Path

```bash
python scripts/reset_prod_data.py --db /path/to/jiuwei_crm.db
```

### 4.2 Security Configuration Check

```bash
python scripts/check_security.py
```

This checks:
- JWT_SECRET_KEY strength
- CORS_ORIGINS configuration
- Admin password (not still using the default)
- Upload directory integrity
- Database file presence
- .env.example status
- TEMP_FILE_RETENTION_DAYS configuration

---

## 5. Pre-Launch Checklist

| # | Item | Command / Action |
|---|------|-----------------|
| 1 | **Reset admin password** | `ADMIN_INITIAL_PASSWORD='<strong>' python scripts/reset_prod_data.py` |
| 2 | **Set strong JWT_SECRET_KEY** | Edit `backend/.env` — use at least 32 random characters |
| 3 | **Configure CORS_ORIGINS** | Set to your production frontend domain(s) in `backend/.env` |
| 4 | **Run security check** | `python scripts/check_security.py` |
| 5 | **Verify .env is not in Git** | Ensure `backend/.env` is in `.gitignore` |
| 6 | **Deploy** | `docker compose up --build -d` (on ECS or equivalent) |
| 7 | **Verify login** | Log in with `admin` + the new password at the production URL |
| 8 | **Verify dashboard** | Dashboard should show 0 leads, 0 today's new, 0 pending |

---

## 6. Environment Variables Reference

These are the variables that must be configured in `backend/.env` for production:

| Variable | Example / Default | Production Requirement |
|----------|------------------|----------------------|
| `DATABASE_URL` | `sqlite:///./data/jiuwei_crm.db` | As-is (v0.1 uses SQLite) |
| `JWT_SECRET_KEY` | `change-me-please-replace-in-production` | **Must change** — 32+ random chars |
| `UPLOAD_DIR` | `./uploads/temp` | As-is |
| `TEMP_FILE_RETENTION_DAYS` | `0` | As-is (files cleared after use) |
| `CORS_ORIGINS` | `http://localhost:3000` | **Must change** to production domain(s) |

> ⚠️ **Never commit `backend/.env` to Git.**  The `.env.example` file is the template.

---

## 7. Docker / ECS Deployment Notes

When deploying on AWS ECS (or similar):

1. Mount a persistent volume for `backend/data/` to persist the SQLite database
2. Mount a persistent volume for `backend/uploads/` for file uploads
3. Pass environment variables via the container definition (not an .env file)
4. After container start, the application auto-creates tables and default configs
5. The admin account must be created **before** running `reset_prod_data.py`, or let the app create it on first start, then run the reset script

---

## 8. Rollback / Re-run

The script is **idempotent** and safe to run multiple times:

- It only deletes from specific tables
- It only removes non-admin users
- Admin password is reset each time
- Upload directories are cleaned each time

If you need to re-initialize after an incident, simply run the script again.

---

## 9. Risk & Warning

- **Data loss**: This script **permanently deletes** all leads, follow-ups, drafts, and import logs.  There is no undo.
- **Admin account**: Ensure at least one admin account exists in the `users` table before running, or let the application create it on first startup.
- **Backup**: Consider backing up `backend/data/jiuwei_crm.db` before running: `cp backend/data/jiuwei_crm.db backend/data/jiuwei_crm.db.bak`
