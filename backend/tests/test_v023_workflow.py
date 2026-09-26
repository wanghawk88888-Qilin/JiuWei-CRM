"""v0.2.3 — Counselor workflow optimization tests.

Covers:
  - The unified "今日待跟进" definition (overdue + today only).
  - The latest-followup rule for ``next_followup_at``.
  - The dynamic queue (new followup / status change drives pending membership).
  - The invalid → following lifecycle.
  - Admin-only soft delete and its soft-delete ghosts.
"""

import datetime

from app.core.security import get_password_hash
from app.models.followup import FollowUp
from app.models.import_log import ImportLog
from app.models.lead import Lead
from app.models.lead_draft import LeadDraft
from app.models.resume_import_batch import ResumeImportBatch
from app.models.user import User
from app.services import datetime_utils
from app.services.resume_batch_service import build_batch_detail


# -- Helpers -----------------------------------------------------------------

_USERS = {
    "test_admin": ("admin", "测试管理员"),
    "test_manager": ("manager", "测试主管"),
    "test_counselor": ("counselor", "测试咨询师"),
    "test_counselor2": ("counselor", "另一位咨询师"),
}


def _uid(db, username: str) -> int:
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        role, real_name = _USERS[username]
        user = User(
            username=username,
            password_hash=get_password_hash("test-password-123"),
            real_name=real_name,
            role=role,
            is_active=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user.id


def _auth(client, db, username: str) -> dict:
    _uid(db, username)
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "test-password-123"},
    )
    body = resp.json()
    assert body["success"], body
    return {"Authorization": f"Bearer {body['data']['access_token']}"}


def _mk_lead(db, name, owner_id, status="new") -> Lead:
    lead = Lead(name=name, phone="13800000000", status=status, owner_id=owner_id)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def _mk_followup(
    db, lead_id, created_by, next_followup_at, content="内容", created_at=None
) -> FollowUp:
    fu = FollowUp(
        lead_id=lead_id,
        followup_type="phone",
        content=content,
        created_by=created_by,
        next_followup_at=next_followup_at,
    )
    if created_at is not None:
        fu.created_at = created_at
    db.add(fu)
    db.commit()
    db.refresh(fu)
    return fu


def _today() -> str:
    return datetime_utils.business_today()


def _offset(days: int, hhmm: str = "10:00") -> str:
    """A Beijing wall-clock ``YYYY-MM-DD HH:MM:SS`` string ``days`` from today."""
    d = datetime_utils.business_now() + datetime.timedelta(days=days)
    return d.strftime("%Y-%m-%d") + f" {hhmm}:00"


# ---------------------------------------------------------------------------
# 6.1 今日待跟进 unified definition
# ---------------------------------------------------------------------------


def test_today_followups_includes_overdue_and_today(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    overdue = _mk_lead(db, "逾期", counselor_id)
    early = _mk_lead(db, "今天已到时间", counselor_id)
    later = _mk_lead(db, "今天稍后", counselor_id)
    _mk_followup(db, overdue.id, counselor_id, _offset(-1, "10:00"))
    _mk_followup(db, early.id, counselor_id, _today() + " 00:05:00")
    _mk_followup(db, later.id, counselor_id, _today() + " 23:50:00")

    tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    names = {i["lead_name"] for i in tf["data"]}
    assert names == {"逾期", "今天已到时间", "今天稍后"}
    priority = {i["lead_name"]: i["followup_priority"] for i in tf["data"]}
    assert priority["逾期"] == "overdue"
    assert priority["今天已到时间"] == "today"
    assert priority["今天稍后"] == "today"


def test_today_followups_excludes_tomorrow_and_future(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    tomorrow = _mk_lead(db, "明天", counselor_id)
    future = _mk_lead(db, "未来", counselor_id)
    _mk_followup(db, tomorrow.id, counselor_id, _offset(1, "09:00"))
    _mk_followup(db, future.id, counselor_id, _offset(5, "09:00"))

    tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    assert tf["data"] == []
    summary = client.get("/api/v1/dashboard/summary", headers=admin_auth).json()
    assert summary["data"]["pending_followups"] == 0


def test_today_followups_excludes_enrolled_invalid_deleted(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    enrolled = _mk_lead(db, "已报名", counselor_id, status="enrolled")
    invalid = _mk_lead(db, "无效", counselor_id, status="invalid")
    deleted = _mk_lead(db, "已删除", counselor_id)
    _mk_followup(db, enrolled.id, counselor_id, _today() + " 10:00:00")
    _mk_followup(db, invalid.id, counselor_id, _today() + " 10:00:00")
    _mk_followup(db, deleted.id, counselor_id, _today() + " 10:00:00")
    deleted.deleted_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    db.commit()

    tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    assert tf["data"] == []

    summary = client.get("/api/v1/dashboard/summary", headers=admin_auth).json()
    assert summary["data"]["pending_followups"] == 0

    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert pending["data"]["total"] == 0


def test_counselor_sees_only_own_pending(client, db, counselor_auth):
    counselor_id = _uid(db, "test_counselor")
    other_id = _uid(db, "test_counselor2")
    mine = _mk_lead(db, "我的", counselor_id)
    theirs = _mk_lead(db, "别人的", other_id)
    _mk_followup(db, mine.id, counselor_id, _today() + " 10:00:00")
    _mk_followup(db, theirs.id, other_id, _today() + " 10:00:00")

    tf = client.get("/api/v1/dashboard/today-followups", headers=counselor_auth).json()
    assert {i["lead_name"] for i in tf["data"]} == {"我的"}
    summary = client.get("/api/v1/dashboard/summary", headers=counselor_auth).json()
    assert summary["data"]["pending_followups"] == 1


def test_admin_sees_pending_across_owners(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    other_id = _uid(db, "test_counselor2")
    a = _mk_lead(db, "甲", counselor_id)
    b = _mk_lead(db, "乙", other_id)
    _mk_followup(db, a.id, counselor_id, _today() + " 10:00:00")
    _mk_followup(db, b.id, other_id, _today() + " 10:00:00")

    tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    assert {i["lead_name"] for i in tf["data"]} == {"甲", "乙"}


def test_card_count_matches_full_today_followups(client, db, admin_auth):
    """The card count must equal the full today-followups set (no silent cap)."""
    counselor_id = _uid(db, "test_counselor")
    for n in range(40):
        lead = _mk_lead(db, f"待跟进{n}", counselor_id)
        _mk_followup(db, lead.id, counselor_id, _today() + " 10:00:00")

    summary = client.get("/api/v1/dashboard/summary", headers=admin_auth).json()
    tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    assert summary["data"]["pending_followups"] == 40
    assert len(tf["data"]) == 40


# ---------------------------------------------------------------------------
# 6.2 latest followup rule
# ---------------------------------------------------------------------------


def test_latest_followup_rule_uses_last_followup(client, db, admin_auth):
    """FU1=09-20, FU2=09-26, FU3=09-28 → effective next must be FU3's 09-28."""
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "最新规则", counselor_id)
    today = _today()
    _mk_followup(
        db, lead.id, counselor_id, today + " 10:00:00",
        created_at="2026-09-20 08:00:00",
    )
    _mk_followup(
        db, lead.id, counselor_id, today + " 11:00:00",
        created_at="2026-09-26 08:00:00",
    )
    _mk_followup(
        db, lead.id, counselor_id, today + "T12:00",
        created_at="2026-09-28 08:00:00",
    )

    tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    items = [i for i in tf["data"] if i["lead_name"] == "最新规则"]
    assert len(items) == 1
    assert items[0]["next_followup_at"] == today + " 12:00"


def test_latest_followup_rule_skips_soft_deleted_followup(client, db, admin_auth):
    """If the latest followup is soft-deleted, use the latest non-deleted one."""
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "软删跟进", counselor_id)
    today = _today()
    _mk_followup(
        db, lead.id, counselor_id, today + " 10:00:00",
        created_at="2026-09-20 08:00:00",
    )
    _mk_followup(
        db, lead.id, counselor_id, today + " 11:00:00",
        created_at="2026-09-26 08:00:00",
    )
    fu3 = _mk_followup(
        db, lead.id, counselor_id, today + "T12:00",
        created_at="2026-09-28 08:00:00",
    )
    # Soft-delete the latest (FU3).
    fu3.deleted_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    db.commit()

    tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    items = [i for i in tf["data"] if i["lead_name"] == "软删跟进"]
    assert len(items) == 1
    assert items[0]["next_followup_at"] == today + " 11:00:00"

    # The pending list and summary agree on the same effective value.
    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert {i["name"] for i in pending["data"]["items"]} == {"软删跟进"}


def test_all_surfaces_show_latest_followup_next(client, db, admin_auth):
    """The normal list, the pending list, and the dashboard all show the latest
    non-deleted followup's next_followup_at — and all fall back to the
    second-latest after the latest followup is soft-deleted."""
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "三处统一", counselor_id)
    today = _today()
    _mk_followup(
        db, lead.id, counselor_id, today + " 10:00:00",
        created_at="2026-09-20 08:00:00",
    )
    _mk_followup(
        db, lead.id, counselor_id, today + " 11:00:00",
        created_at="2026-09-26 08:00:00",
    )
    fu3 = _mk_followup(
        db, lead.id, counselor_id, today + " 12:00:00",
        created_at="2026-09-28 08:00:00",
    )

    def assert_everywhere(expected_next: str) -> None:
        normal = client.get("/api/v1/leads", headers=admin_auth).json()
        normal_item = next(i for i in normal["data"]["items"] if i["id"] == lead.id)
        assert normal_item["next_followup_at"] == expected_next

        pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
        pending_item = next(i for i in pending["data"]["items"] if i["id"] == lead.id)
        assert pending_item["next_followup_at"] == expected_next

        tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
        tf_item = next(i for i in tf["data"] if i["lead_id"] == lead.id)
        assert tf_item["next_followup_at"] == expected_next

    # FU3 is the latest followup → all three surfaces show its value.
    assert_everywhere(today + " 12:00:00")

    # Soft-delete FU3 → all three surfaces fall back to FU2.
    fu3.deleted_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    db.commit()
    assert_everywhere(today + " 11:00:00")


# ---------------------------------------------------------------------------
# 6.3 dynamic queue
# ---------------------------------------------------------------------------


def test_new_followup_today_keeps_pending(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "动态", counselor_id)
    _mk_followup(db, lead.id, counselor_id, _today() + " 23:50:00")

    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert pending["data"]["total"] == 1


def test_new_followup_tomorrow_leaves_pending(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "动态", counselor_id)
    _mk_followup(db, lead.id, counselor_id, _today() + " 10:00:00")
    # A newer followup pushes the effective next to tomorrow.
    _mk_followup(db, lead.id, counselor_id, _offset(1, "09:00"))

    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert pending["data"]["total"] == 0
    tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    assert tf["data"] == []


def test_status_enrolled_and_invalid_leave_pending(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    enrolled = _mk_lead(db, "报名", counselor_id, status="enrolled")
    invalid = _mk_lead(db, "无效", counselor_id, status="invalid")
    _mk_followup(db, enrolled.id, counselor_id, _today() + " 10:00:00")
    _mk_followup(db, invalid.id, counselor_id, _today() + " 10:00:00")

    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert pending["data"]["total"] == 0


# ---------------------------------------------------------------------------
# 6.4 invalid lifecycle
# ---------------------------------------------------------------------------


def test_invalid_lifecycle_removes_and_restores(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "生命周期", counselor_id, status="following")
    _mk_followup(db, lead.id, counselor_id, _today() + " 10:00:00")

    # following + due today → pending
    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert pending["data"]["total"] == 1

    # → invalid → leaves pending
    resp = client.put(
        f"/api/v1/leads/{lead.id}", json={"status": "invalid"}, headers=admin_auth
    ).json()
    assert resp["success"]
    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert pending["data"]["total"] == 0

    # → following → status restored; still due today → re-enters pending
    resp = client.put(
        f"/api/v1/leads/{lead.id}", json={"status": "following"}, headers=admin_auth
    ).json()
    assert resp["success"]
    detail = client.get(f"/api/v1/leads/{lead.id}", headers=admin_auth).json()
    assert detail["data"]["status"] == "following"
    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert pending["data"]["total"] == 1


def test_invalid_restore_future_next_stays_out_of_pending(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "未来恢复", counselor_id, status="invalid")
    _mk_followup(db, lead.id, counselor_id, _offset(3, "09:00"))

    resp = client.put(
        f"/api/v1/leads/{lead.id}", json={"status": "following"}, headers=admin_auth
    ).json()
    assert resp["success"]
    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert pending["data"]["total"] == 0


def test_invalid_restore_without_next_stays_out_of_pending(client, db, admin_auth):
    """Restoring a lead with no next_followup_at must not invent a pending time."""
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "无时间恢复", counselor_id, status="invalid")

    resp = client.put(
        f"/api/v1/leads/{lead.id}", json={"status": "following"}, headers=admin_auth
    ).json()
    assert resp["success"]
    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert pending["data"]["total"] == 0


# ---------------------------------------------------------------------------
# 6.5 admin-only soft delete
# ---------------------------------------------------------------------------


def test_admin_delete_soft_deletes(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "待删", counselor_id)
    _mk_followup(db, lead.id, counselor_id, _today() + " 10:00:00")

    resp = client.delete(f"/api/v1/leads/{lead.id}", headers=admin_auth)
    assert resp.status_code == 200
    assert resp.json()["success"]

    # Invisible everywhere.
    assert client.get("/api/v1/leads", headers=admin_auth).json()["data"]["total"] == 0
    detail = client.get(f"/api/v1/leads/{lead.id}", headers=admin_auth).json()
    assert detail["success"] is False
    assert detail["error_code"] == "LEAD_NOT_FOUND"
    tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    assert tf["data"] == []
    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert pending["data"]["total"] == 0

    # Row still exists with deleted_at set (expire the session so the identity
    # map re-reads the soft-delete committed by the request-scoped session).
    db.expire_all()
    row = db.query(Lead).filter(Lead.id == lead.id).first()
    assert row is not None
    assert row.deleted_at is not None


def test_manager_delete_forbidden(client, db):
    manager_auth = _auth(client, db, "test_manager")
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "主管删", counselor_id)

    resp = client.delete(f"/api/v1/leads/{lead.id}", headers=manager_auth)
    assert resp.status_code == 403


def test_counselor_delete_own_forbidden(client, db, counselor_auth):
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "咨询师删自己的", counselor_id)

    resp = client.delete(f"/api/v1/leads/{lead.id}", headers=counselor_auth)
    assert resp.status_code == 403


def test_counselor_delete_others_forbidden(client, db, counselor_auth):
    other_id = _uid(db, "test_counselor2")
    lead = _mk_lead(db, "删别人的", other_id)

    resp = client.delete(f"/api/v1/leads/{lead.id}", headers=counselor_auth)
    assert resp.status_code == 403


def test_soft_deleted_lead_not_a_valid_duplicate(client, db, admin_auth):
    """A soft-deleted lead must not surface as a valid duplicate in batch detail."""
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "软删重复源", counselor_id)
    lead.deleted_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    db.commit()

    batch = ResumeImportBatch(
        batch_no="RB-TEST-DUP", total_files=1, status="completed",
        created_by=counselor_id,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    log = ImportLog(
        batch_id=batch.id, file_name="dup.docx", file_type="docx",
        parse_status="parsed", created_by=counselor_id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    draft = LeadDraft(
        import_log_id=log.id, batch_id=batch.id, name="重复", phone="13800000000",
        status="duplicate", duplicate_lead_id=lead.id, created_by=counselor_id,
    )
    db.add(draft)
    db.commit()

    detail = build_batch_detail(db, batch)
    item = detail["items"][0]
    assert item["status"] == "duplicate"
    # The soft-deleted lead is filtered out → no existing_lead_name.
    assert item["duplicate"]["existing_lead_name"] is None
    assert item["duplicate"]["existing_lead_id"] == lead.id
