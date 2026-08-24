"""v0.2.2 P0 — business date boundaries must use Asia/Shanghai, not server-local.

The production Docker image runs on UTC. Between Beijing 00:00 and 07:59 the
server-local ``datetime.datetime.now()`` still reports the *previous* calendar
day, so "today / today new leads / pending followups" would be off by one day.

These tests freeze the business clock at two points straddling midnight and
assert that the whole boundary pipeline (summary counts, ``created=today``,
``followup=pending``, and the overdue/today/upcoming classification) keys off
the Beijing calendar day, never the UTC one.
"""

import datetime

from app.services import datetime_utils
from app.models.followup import FollowUp
from app.models.lead import Lead
from app.models.user import User


# -- Helpers ---------------------------------------------------------------


def _admin_id(db) -> int:
    """Return the admin user id (created by the session-scoped admin_auth fixture)."""
    return db.query(User).filter(User.username == "test_admin").first().id


def _mk_lead(db, name: str, created_at: str | None = None) -> Lead:
    lead = Lead(name=name, phone="13800000000", status="new", owner_id=_admin_id(db))
    if created_at is not None:
        lead.created_at = created_at
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def _mk_followup(db, lead_id: int, next_followup_at: str) -> FollowUp:
    fu = FollowUp(
        lead_id=lead_id,
        followup_type="phone",
        content="内容",
        created_by=_admin_id(db),
        next_followup_at=next_followup_at,
    )
    db.add(fu)
    db.commit()
    db.refresh(fu)
    return fu


def _freeze_bj(monkeypatch, year: int, month: int, day: int, hour: int, minute: int = 0):
    """Freeze the business clock at a Beijing wall-clock instant."""
    fixed = datetime.datetime(
        year, month, day, hour, minute, 0, tzinfo=datetime_utils.BUSINESS_TZ
    )
    monkeypatch.setattr(datetime_utils, "business_now", lambda: fixed)
    return fixed


# -- Midnight boundary: Beijing 01:00 (UTC 2026-08-24 17:00) -----------------


def test_early_morning_boundary(client, db, admin_auth, monkeypatch):
    # Beijing 2026-08-25 01:00 == UTC 2026-08-24 17:00. The business "today"
    # must already be 08-25, even though UTC is still on 08-24.
    _freeze_bj(monkeypatch, 2026, 8, 25, 1, 0)

    assert datetime_utils.business_today() == "2026-08-25"

    # created_at is stored in UTC. Beijing "today" = 08-25 maps to UTC
    # [08-24 16:00, 08-25 16:00).
    lead_today = _mk_lead(db, "今日线索", created_at="2026-08-24 18:12:00")   # BJ 08-25 02:12
    lead_yesterday = _mk_lead(db, "昨日线索", created_at="2026-08-24 15:59:00")  # BJ 08-24 23:59

    # next_followup_at is Beijing wall clock: 00:05 today -> "today";
    # 23:55 yesterday -> "overdue".
    _mk_followup(db, lead_today.id, next_followup_at="2026-08-25T00:05")
    _mk_followup(db, lead_yesterday.id, next_followup_at="2026-08-24T23:55")

    # Today's new leads: only the 08-25 lead counts.
    summary = client.get("/api/v1/dashboard/summary", headers=admin_auth).json()
    assert summary["data"]["today_new_leads"] == 1

    created = client.get("/api/v1/leads?created=today", headers=admin_auth).json()
    assert {i["name"] for i in created["data"]["items"]} == {"今日线索"}

    # overdue / today classification.
    tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    priority = {i["lead_name"]: i["followup_priority"] for i in tf["data"]}
    assert priority["今日线索"] == "today"
    assert priority["昨日线索"] == "overdue"

    # Dashboard pending count matches the followup=pending list.
    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert summary["data"]["pending_followups"] == 2
    assert pending["data"]["total"] == 2


# -- Midnight boundary: Beijing 23:30 (other end of the day) ------------------


def test_late_evening_boundary(client, db, admin_auth, monkeypatch):
    # Near the end of the Beijing day, "today" must still be 08-25 and a
    # followup at 08-26 00:05 must already count as "upcoming" (not today).
    _freeze_bj(monkeypatch, 2026, 8, 25, 23, 30)

    assert datetime_utils.business_today() == "2026-08-25"

    lead_today = _mk_lead(db, "晚间今日", created_at="2026-08-25 15:59:00")   # BJ 08-25 23:59
    lead_tomorrow = _mk_lead(db, "次日线索", created_at="2026-08-25 16:00:00")  # BJ 08-26 00:00

    _mk_followup(db, lead_today.id, next_followup_at="2026-08-25T23:55")
    _mk_followup(db, lead_tomorrow.id, next_followup_at="2026-08-26T00:05")

    summary = client.get("/api/v1/dashboard/summary", headers=admin_auth).json()
    assert summary["data"]["today_new_leads"] == 1

    tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    priority = {i["lead_name"]: i["followup_priority"] for i in tf["data"]}
    assert priority["晚间今日"] == "today"
    assert priority["次日线索"] == "upcoming"

    # The 08-26 followup is upcoming, so it is excluded from pending.
    assert summary["data"]["pending_followups"] == 1
    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert pending["data"]["total"] == 1
    assert {i["name"] for i in pending["data"]["items"]} == {"晚间今日"}


# -- UTC storage: "today new leads" maps the Beijing day to a UTC range ---------


def test_business_day_utc_range_boundaries():
    """The UTC window for Beijing 2026-08-25 is [08-24 16:00, 08-25 16:00)."""
    utc_start, utc_end = datetime_utils.business_day_utc_range("2026-08-25")
    assert utc_start == "2026-08-24 16:00:00"
    assert utc_end == "2026-08-25 16:00:00"


def test_today_new_leads_uses_utc_range(client, db, admin_auth, monkeypatch):
    """created_at is UTC, so "today" must be matched against a UTC range.

    Five UTC instants map to the exact Beijing boundary the spec requires.
    """
    _freeze_bj(monkeypatch, 2026, 8, 25, 12, 0)

    cases = [
        ("昨日尾", "2026-08-24 15:59:00", False),   # BJ 08-24 23:59 -> not 08-25
        ("零点", "2026-08-24 16:00:00", True),      # BJ 08-25 00:00 -> 08-25
        ("凌晨", "2026-08-24 18:12:00", True),      # BJ 08-25 02:12 -> 08-25
        ("深夜", "2026-08-25 15:59:00", True),      # BJ 08-25 23:59 -> 08-25
        ("次日零点", "2026-08-25 16:00:00", False),  # BJ 08-26 00:00 -> not 08-25
    ]
    for name, created_at, _ in cases:
        _mk_lead(db, name, created_at=created_at)

    summary = client.get("/api/v1/dashboard/summary", headers=admin_auth).json()
    assert summary["data"]["today_new_leads"] == 3

    created = client.get("/api/v1/leads?created=today", headers=admin_auth).json()
    assert {i["name"] for i in created["data"]["items"]} == {"零点", "凌晨", "深夜"}
