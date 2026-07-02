# Pre-Release Report — Production Initialization & Security Closure (v0.1.0)

> **Date:** 2026-07-02
> **Phase:** v0.1.0 Pre-Release Final
> **Status:** ✅ Complete

---

## 1. New Scripts

### 1.1 `scripts/reset_prod_data.py`

**Purpose:** Production data reset before v0.1.0 deployment.

**Features:**
- Connects to SQLite database (configurable via `--db` argument)
- Clears business test data: `leads`, `lead_followups`, `lead_drafts`, `import_logs`
- Removes all non-admin users
- Keeps admin account(s), resets password, ensures `is_active = 1`
- Preserves: `lead_sources`, `courses`, `system_settings`
- Cleans `uploads/temp/*` and `uploads/parsed/*` (preserves `.gitkeep`)
- Password handling:
  - Priority 1: `ADMIN_INITIAL_PASSWORD` environment variable
  - Priority 2: Interactive terminal input
  - Validation: ≥ 8 chars, not empty, not `admin123`/`123456`/`password`
  - Stored as bcrypt hash
- Idempotent — safe to run multiple times
- Outputs execution summary

### 1.2 `scripts/check_security.py`

**Purpose:** Security configuration validation before deployment.

**Checks:**
| # | Check | Description |
|---|-------|-------------|
| 1 | Environment File | `.env.example` is a template file (not leaked real config) |
| 2 | JWT Secret Key | Not a weak/default value, ≥ 16 chars recommended |
| 3 | Temp File Retention | `TEMP_FILE_RETENTION_DAYS` is set and valid |
| 4 | CORS Origins | Configured and not localhost-only in production |
| 5 | Upload Directories | `uploads/temp` and `uploads/parsed` exist |
| 6 | Database File | SQLite database exists and is accessible |
| 7 | Admin Password | Not still using a known default password |
| 8 | .env.example Content | All 5 required keys present |

**Output:** PASS / WARNING / FAIL with colour-coded results and summary.

---

## 2. Cleanup Scope

### Cleared

| Table / Path | Records Deleted (test run) |
|-------------|---------------------------|
| `leads` | 21 rows |
| `lead_followups` | 11 rows |
| `lead_drafts` | 11 rows |
| `import_logs` | 11 rows |
| Non-admin users | 5 users removed |
| `uploads/temp/*` | 0 files (already clean) |
| `uploads/parsed/*` | 0 files (already clean) |

### Preserved

| Table | Rows Retained |
|-------|--------------|
| `lead_sources` | 5 rows (default sources) |
| `courses` | 3 rows (default courses) |
| `system_settings` | 3 rows (default settings) |
| `users` (admin only) | 1 row (admin, password reset) |
| `.gitkeep` files | All preserved |

---

## 3. Security Checks (Test Results)

Executed `python scripts/check_security.py`:

| Check | Result | Detail |
|-------|--------|--------|
| Environment File | ✅ PASS | `.env.example` appears to be a template file |
| JWT Secret Key | ❌ FAIL | `JWT_SECRET_KEY` is a weak/default value: `change-me` |
| Temp File Retention | ✅ PASS | `TEMP_FILE_RETENTION_DAYS=0` |
| CORS Origins | ⚠️ WARN | Only contains localhost — update for production |
| Upload Directories | ✅ PASS | Both directories exist |
| Database File | ✅ PASS | Database file exists (53,248 bytes) |
| Admin Password | ✅ PASS | Admin password is not a known default value |
| .env.example Content | ✅ PASS | Contains all 5 required keys |

**Summary:** 6 PASS / 1 WARNING / 1 FAIL

> **Note:** The FAIL and WARNING are **expected** in a local/dev environment. These are the exact items the production deployment checklist instructs operators to fix.

---

## 4. Self-Test Results

### Test 1: Interactive Password Input

```bash
$ python scripts/reset_prod_data.py
```
- ✅ Prompts for password input
- ✅ Accepts valid password
- ✅ Rejects `admin123` (forbidden)
- ✅ Rejects `< 8 chars` (too short)
- ✅ Rejects empty password

### Test 2: Environment Variable Password

```bash
$ ADMIN_INITIAL_PASSWORD='StrongPassword123!' python scripts/reset_prod_data.py
```
- ✅ Reads password from env var
- ✅ Clears `leads` (21 → 0)
- ✅ Clears `lead_followups` (11 → 0)
- ✅ Clears `lead_drafts` (11 → 0)
- ✅ Clears `import_logs` (11 → 0)
- ✅ Removes non-admin users (5 → 0)
- ✅ Resets admin password (bcrypt hash)
- ✅ Preserves `lead_sources` (5), `courses` (3), `system_settings` (3)
- ✅ Cleans upload directories

### Test 3: Security Check

```bash
$ python scripts/check_security.py
```
- ✅ All 8 checks execute
- ✅ Correctly identifies weak JWT secret
- ✅ Correctly identifies localhost-only CORS
- ✅ Correctly verifies admin password changed
- ✅ Outputs PASS/WARNING/FAIL with summary

### Test 4: Docker Compose

```bash
$ docker compose up --build
```
- ✅ Backend builds and starts (FastAPI on port 8000)
- ✅ Frontend builds and starts (Next.js on port 3000)
- ✅ Health check returns `{"status":"ok"}`
- ✅ Login with new password returns JWT token
- ✅ Dashboard shows `total_leads: 0, today_new_leads: 0, pending_followups: 0, enrolled_leads: 0`

---

## 5. Pre-Launch Operation Steps

The operator must complete these steps before the first production deployment:

| # | Step | Command |
|---|------|---------|
| 1 | **Reset production data** | `ADMIN_INITIAL_PASSWORD='<strong-password>' python scripts/reset_prod_data.py` |
| 2 | **Set JWT_SECRET_KEY** | Edit `backend/.env`: at least 32 random characters |
| 3 | **Configure CORS_ORIGINS** | Edit `backend/.env`: set to production domain(s) |
| 4 | **Run security check** | `python scripts/check_security.py` |
| 5 | **Verify .gitignore** | Ensure `backend/.env` is in `.gitignore` |
| 6 | **Deploy** | `docker compose up --build -d` (or ECS equivalent) |
| 7 | **Verify login** | Log in with `admin` + new password |
| 8 | **Verify dashboard** | Confirm 0 leads, 0 today, 0 pending, 0 enrolled |

---

## 6. Files Changed / Added

| File | Action |
|------|--------|
| `scripts/reset_prod_data.py` | **New** — Production data reset script |
| `scripts/check_security.py` | **New** — Security configuration check script |
| `backend/.env.example` | **Updated** — `JWT_SECRET_KEY=change-me-please-replace-in-production` |
| `docs/07-Deployment/Production-Init-v0.1.md` | **New** — Production initialization documentation |
| `README.md` | **Updated** — Added Production Initialization section |
| `reports/pre-release-production-init.md` | **New** — This report |

### NOT Modified (per specification)

- Lead business logic
- FollowUp business logic
- Resume Import
- LeadDraft
- Dashboard
- User Management pages
- Frontend UI
- Database table structure
- `docs/` existing content

---

## 7. Risk & Warnings

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Data loss** — script permanently deletes all leads/followups | High | Backup DB before running: `cp backend/data/jiuwei_crm.db backend/data/jiuwei_crm.db.bak` |
| **Admin lockout** — forgetting the new password | Medium | Store password in a secure password manager |
| **Weak JWT secret** — `change-me` is trivially forgeable | High | Must be changed before any production traffic |
| **CORS misconfiguration** — localhost in production | Medium | Set to actual production domain(s) |
| **.env in Git** — leaking secrets | High | Verify `.gitignore` includes `backend/.env` |

---

## 8. Conclusion

All pre-release production initialization and security closure tasks are complete.

- ✅ `reset_prod_data.py` — production data reset with strong password handling
- ✅ `check_security.py` — 8-point security configuration check
- ✅ `.env.example` — updated with placeholder values
- ✅ `Production-Init-v0.1.md` — comprehensive deployment documentation
- ✅ `README.md` — production initialization section added
- ✅ Self-tests pass — interactive input, env var, security check, Docker
- ✅ Dashboard verified — all zeros after reset

**Ready for v0.1.0 production deployment.**
