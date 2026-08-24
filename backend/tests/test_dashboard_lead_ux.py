"""v0.2.2 — Dashboard & Lead list UX / permission tests.

Covers:
  - Dashboard summary / today-followups / recent-leads role scoping (Admin global,
    Counselor own leads only).
  - GET /api/v1/leads role scoping and query-param bypass attempts.
  - Card filters: created=today, followup=pending, status=enrolled.
  - owner_name (Lead.owner_id -> User.real_name) and last_followup_content
    (latest FollowUp.content) enrichment.
"""

import datetime

from app.core.security import get_password_hash
from app.models.followup import FollowUp
from app.models.lead import Lead
from app.models.user import User
from app.services import datetime_utils


# -- Helpers ---------------------------------------------------------------

# Mirror the users created by conftest fixtures, so a test can lazily ensure a
# user exists without depending on fixture ordering.
_TEST_USERS = {
    "test_admin": ("admin", "测试管理员"),
    "test_counselor": ("counselor", "测试咨询师"),
    "test_counselor2": ("counselor", "另一位咨询师"),
}


def _uid(db, username: str) -> int:
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        role, real_name = _TEST_USERS[username]
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


def _mk_lead(db, name, owner_id, status="new", created_at=None) -> Lead:
    lead = Lead(name=name, phone="13800000000", status=status, owner_id=owner_id)
    if created_at is not None:
        lead.created_at = created_at
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def _mk_followup(
    db, lead_id, created_by, content, next_followup_at=None, created_at=None
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


def _today_date() -> str:
    return datetime_utils.business_today()


def _today_end() -> str:
    return _today_date() + " 23:59:59"


def _yesterday_ts() -> str:
    ts = datetime_utils.business_now() - datetime.timedelta(days=1)
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def _now_ts() -> str:
    return datetime_utils.business_now().strftime("%Y-%m-%d %H:%M:%S")


# -- Dashboard summary ------------------------------------------------------


def test_admin_summary_returns_global(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    admin_id = _uid(db, "test_admin")
    _mk_lead(db, "A", counselor_id)
    _mk_lead(db, "B", counselor_id)
    _mk_lead(db, "C", admin_id)

    body = client.get("/api/v1/dashboard/summary", headers=admin_auth).json()
    assert body["success"]
    assert body["data"]["total_leads"] == 3


def test_counselor_summary_returns_own_only(
    client, db, counselor_auth
):
    counselor_id = _uid(db, "test_counselor")
    other_id = _uid(db, "test_counselor2")
    _mk_lead(db, "我的", counselor_id)
    _mk_lead(db, "别人的", other_id)

    body = client.get("/api/v1/dashboard/summary", headers=counselor_auth).json()
    assert body["data"]["total_leads"] == 1


# -- Dashboard today-followups ---------------------------------------------


def test_admin_today_followups_contains_different_owners(
    client, db, admin_auth
):
    counselor_id = _uid(db, "test_counselor")
    other_id = _uid(db, "test_counselor2")
    lead1 = _mk_lead(db, "甲", counselor_id)
    lead2 = _mk_lead(db, "乙", other_id)
    _mk_followup(db, lead1.id, counselor_id, "跟进甲", next_followup_at=_today_end())
    _mk_followup(db, lead2.id, other_id, "跟进乙", next_followup_at=_today_end())

    body = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    items = body["data"]
    names = {i["lead_name"] for i in items}
    assert {"甲", "乙"} <= names

    owner_names = {i["owner_name"] for i in items}
    assert owner_names == {"测试咨询师", "另一位咨询师"}


def test_counselor_today_followups_only_self(client, db, counselor_auth):
    counselor_id = _uid(db, "test_counselor")
    other_id = _uid(db, "test_counselor2")
    lead1 = _mk_lead(db, "我的", counselor_id)
    lead2 = _mk_lead(db, "别人的", other_id)
    _mk_followup(db, lead1.id, counselor_id, "内容", next_followup_at=_today_end())
    _mk_followup(db, lead2.id, other_id, "内容", next_followup_at=_today_end())

    body = client.get("/api/v1/dashboard/today-followups", headers=counselor_auth).json()
    items = body["data"]
    assert items, "expected at least one own pending followup"
    assert all(i["owner_id"] == counselor_id for i in items)


# -- Dashboard recent-leads ------------------------------------------------


def test_admin_recent_leads_contains_different_owners(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    other_id = _uid(db, "test_counselor2")
    _mk_lead(db, "甲", counselor_id)
    _mk_lead(db, "乙", other_id)

    body = client.get("/api/v1/dashboard/recent-leads", headers=admin_auth).json()
    items = body["data"]
    owner_names = {i["owner_name"] for i in items}
    assert owner_names == {"测试咨询师", "另一位咨询师"}


def test_counselor_recent_leads_only_self(client, db, counselor_auth):
    counselor_id = _uid(db, "test_counselor")
    other_id = _uid(db, "test_counselor2")
    _mk_lead(db, "我的", counselor_id)
    _mk_lead(db, "别人的", other_id)

    body = client.get("/api/v1/dashboard/recent-leads", headers=counselor_auth).json()
    items = body["data"]
    assert all(i["owner_id"] == counselor_id for i in items)
    assert {i["name"] for i in items} == {"我的"}


# -- Lead list permission ---------------------------------------------------


def test_admin_list_leads_global(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    other_id = _uid(db, "test_counselor2")
    _mk_lead(db, "A", counselor_id)
    _mk_lead(db, "B", other_id)

    body = client.get("/api/v1/leads", headers=admin_auth).json()
    assert body["data"]["total"] == 2


def test_counselor_list_leads_only_own(client, db, counselor_auth):
    counselor_id = _uid(db, "test_counselor")
    other_id = _uid(db, "test_counselor2")
    _mk_lead(db, "我的", counselor_id)
    _mk_lead(db, "别人的", other_id)

    body = client.get("/api/v1/leads", headers=counselor_auth).json()
    assert body["data"]["total"] == 1
    assert all(i["owner_id"] == counselor_id for i in body["data"]["items"])


def test_counselor_cannot_bypass_with_owner_id_param(client, db, counselor_auth):
    counselor_id = _uid(db, "test_counselor")
    other_id = _uid(db, "test_counselor2")
    _mk_lead(db, "我的", counselor_id)
    _mk_lead(db, "别人的", other_id)

    # Even with ?owner_id=<other>, counselor only sees their own.
    body = client.get(
        f"/api/v1/leads?owner_id={other_id}", headers=counselor_auth
    ).json()
    assert body["data"]["total"] == 1
    assert all(i["owner_id"] == counselor_id for i in body["data"]["items"])


def test_unassigned_lead_not_returned_to_counselor(client, db, admin_auth, counselor_auth):
    _mk_lead(db, "未分配", None)  # owner_id is None

    counselor_body = client.get("/api/v1/leads", headers=counselor_auth).json()
    assert counselor_body["data"]["total"] == 0

    admin_body = client.get("/api/v1/leads", headers=admin_auth).json()
    assert admin_body["data"]["total"] == 1
    item = admin_body["data"]["items"][0]
    assert item["owner_id"] is None
    assert item["owner_name"] is None


# -- Card filters -----------------------------------------------------------


def test_created_today_filter(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    _mk_lead(db, "今天", counselor_id, created_at=_now_ts())
    _mk_lead(db, "昨天", counselor_id, created_at=_yesterday_ts())

    body = client.get("/api/v1/leads?created=today", headers=admin_auth).json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["name"] == "今天"


def test_followup_pending_filter(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    lead1 = _mk_lead(db, "待跟进", counselor_id)
    _mk_lead(db, "无跟进", counselor_id)
    lead3 = _mk_lead(db, "未来跟进", counselor_id)
    _mk_followup(db, lead1.id, counselor_id, "内容", next_followup_at=_today_end())
    # A followup with a future next_followup_at is NOT "pending".
    future_ts = (datetime_utils.business_now() + datetime.timedelta(days=5)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    _mk_followup(db, lead3.id, counselor_id, "内容", next_followup_at=future_ts)

    body = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["name"] == "待跟进"


def test_pending_followup_excludes_enrolled_and_invalid(client, db, admin_auth):
    """Regression (v0.2.2 P0): enrolled / invalid leads must not count as 待跟进.

    All three leads carry an overdue/due followup; only the ``following`` lead
    may surface in the dashboard count and the ``followup=pending`` list.
    """
    counselor_id = _uid(db, "test_counselor")
    following = _mk_lead(db, "跟进中", counselor_id, status="following")
    enrolled = _mk_lead(db, "已报名", counselor_id, status="enrolled")
    invalid = _mk_lead(db, "无效", counselor_id, status="invalid")

    for lead in (following, enrolled, invalid):
        _mk_followup(db, lead.id, counselor_id, "内容", next_followup_at=_today_end())

    summary = client.get("/api/v1/dashboard/summary", headers=admin_auth).json()
    assert summary["data"]["pending_followups"] == 1

    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert pending["data"]["total"] == 1
    assert {i["name"] for i in pending["data"]["items"]} == {"跟进中"}

    tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    assert {i["lead_name"] for i in tf["data"]} == {"跟进中"}


# -- next_followup_at format compatibility (T vs space) ---------------------


def test_pending_t_format_and_space_format_consistent(client, db, admin_auth):
    """`datetime-local` stores `YYYY-MM-DDTHH:MM`; legacy stores `YYYY-MM-DD HH:MM:SS`.

    Both must be recognised as "today" pending followups, and the dashboard
    summary count must match the `followup=pending` list count.
    """
    counselor_id = _uid(db, "test_counselor")
    today = _today_date()
    yesterday = (datetime_utils.business_now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (datetime_utils.business_now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    lead_t = _mk_lead(db, "T格式今天", counselor_id)
    _mk_followup(db, lead_t.id, counselor_id, "内容", next_followup_at=today + "T00:05")

    lead_space = _mk_lead(db, "空格格式今天", counselor_id)
    _mk_followup(db, lead_space.id, counselor_id, "内容", next_followup_at=today + " 00:05:00")

    lead_overdue = _mk_lead(db, "T格式逾期", counselor_id)
    _mk_followup(db, lead_overdue.id, counselor_id, "内容", next_followup_at=yesterday + "T10:00")

    lead_upcoming = _mk_lead(db, "T格式未来", counselor_id)
    _mk_followup(db, lead_upcoming.id, counselor_id, "内容", next_followup_at=tomorrow + "T10:00")

    # Pending = overdue (1) + today (2); upcoming is excluded.
    summary = client.get("/api/v1/dashboard/summary", headers=admin_auth).json()
    assert summary["data"]["pending_followups"] == 3

    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert pending["data"]["total"] == 3
    names = {i["name"] for i in pending["data"]["items"]}
    assert names == {"T格式今天", "空格格式今天", "T格式逾期"}

    # overdue / today / upcoming classification preserved across both formats.
    tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    priority = {i["lead_name"]: i["followup_priority"] for i in tf["data"]}
    assert priority["T格式今天"] == "today"
    assert priority["空格格式今天"] == "today"
    assert priority["T格式逾期"] == "overdue"
    assert priority["T格式未来"] == "upcoming"


def test_pending_t_format_midnight_minutes_only(client, db, admin_auth):
    """Regression: `2026-08-24T00:05` must count as same-day pending (the bug)."""
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "ISO零点五分", counselor_id)
    _mk_followup(
        db, lead.id, counselor_id, "内容",
        next_followup_at=_today_date() + "T00:05",
    )

    summary = client.get("/api/v1/dashboard/summary", headers=admin_auth).json()
    assert summary["data"]["pending_followups"] == 1

    pending = client.get("/api/v1/leads?followup=pending", headers=admin_auth).json()
    assert pending["data"]["total"] == 1
    assert pending["data"]["items"][0]["name"] == "ISO零点五分"


def test_earliest_followup_handles_mixed_t_and_space_formats(client, db, admin_auth):
    """A lead with both T and space formats must resolve to the true earliest.

    Raw ``min()`` would pick ``2026-08-24 10:00:00`` over ``2026-08-24T08:00``
    because ``'T'`` (0x54) sorts after ``' '`` (0x20). The earliest must be the
    08:00 one (the T-format record).
    """
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "双格式", counselor_id)
    today = _today_date()
    _mk_followup(db, lead.id, counselor_id, "晚", next_followup_at=today + " 10:00:00")
    _mk_followup(db, lead.id, counselor_id, "早", next_followup_at=today + "T08:00")

    tf = client.get("/api/v1/dashboard/today-followups", headers=admin_auth).json()
    items = [i for i in tf["data"] if i["lead_name"] == "双格式"]
    assert len(items) == 1
    assert items[0]["followup_priority"] == "today"
    assert items[0]["next_followup_at"] == today + " 08:00"


def test_status_enrolled_filter(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    _mk_lead(db, "已报名", counselor_id, status="enrolled")
    _mk_lead(db, "新线索", counselor_id, status="new")

    body = client.get("/api/v1/leads?status=enrolled", headers=admin_auth).json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["name"] == "已报名"


def test_counselor_filters_combined_with_owner(client, db, counselor_auth):
    counselor_id = _uid(db, "test_counselor")
    other_id = _uid(db, "test_counselor2")
    _mk_lead(db, "我的已报名", counselor_id, status="enrolled")
    _mk_lead(db, "别人的已报名", other_id, status="enrolled")

    body = client.get("/api/v1/leads?status=enrolled", headers=counselor_auth).json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["owner_id"] == counselor_id


# -- owner_name / last_followup_content enrichment --------------------------


def test_lead_list_owner_name_and_followup_content(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "张三", counselor_id)
    _mk_followup(db, lead.id, counselor_id, "微信未通过，电话无人接听")

    body = client.get("/api/v1/leads", headers=admin_auth).json()
    item = body["data"]["items"][0]
    assert item["owner_name"] == "测试咨询师"
    assert item["last_followup_content"] == "微信未通过，电话无人接听"
    # last followup time remains populated from the latest followup.
    assert item["last_followup_at"] is not None


def test_lead_list_no_followup_content_is_none(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    _mk_lead(db, "无跟进", counselor_id)

    body = client.get("/api/v1/leads", headers=admin_auth).json()
    item = body["data"]["items"][0]
    assert item["last_followup_content"] is None
    assert item["last_followup_at"] is None


def test_lead_list_followup_content_truncated(client, db, admin_auth):
    counselor_id = _uid(db, "test_counselor")
    lead = _mk_lead(db, "长内容", counselor_id)
    _mk_followup(db, lead.id, counselor_id, "这是一个超过五十个字符的非常非常长的跟进内容" * 3)

    body = client.get("/api/v1/leads", headers=admin_auth).json()
    item = body["data"]["items"][0]
    assert item["last_followup_content"].endswith("...")
    assert len(item["last_followup_content"]) <= 53
