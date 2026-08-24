import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from app.models.lead import Lead
from app.models.followup import FollowUp
from app.models.user import User

from app.services import datetime_utils


def _apply_lead_owner_filter(query, current_user: User):
    """Apply role-based owner filter to a Lead query.

    admin / manager: no filter (see all)
    counselor: only own leads (owner_id == current_user.id)
    """
    if current_user.role == "counselor":
        query = query.filter(Lead.owner_id == current_user.id)
    return query


def get_dashboard_summary(db: Session, current_user: User) -> dict:
    """Return dashboard summary statistics.

    Returns:
        dict with keys: total_leads, today_new_leads, pending_followups, enrolled_leads
    """

    today_str = datetime_utils.business_today()
    today_end = today_str + " 23:59:59"

    # Base query: non-deleted leads
    base = db.query(Lead).filter(Lead.deleted_at.is_(None))
    base = _apply_lead_owner_filter(base, current_user)

    # total_leads
    total_leads = base.count()

    # today_new_leads — created_at (UTC) falls within the Beijing business day.
    utc_start, utc_end = datetime_utils.business_day_utc_range()
    today_new_leads = base.filter(
        Lead.created_at >= utc_start,
        Lead.created_at < utc_end,
    ).count()

    # enrolled_leads
    enrolled_leads = base.filter(Lead.status == "enrolled").count()

    # pending_followups — distinct leads with a due followup; enrolled / invalid
    # leads are excluded so they no longer surface as "待跟进".
    pending_query = (
        db.query(func.count(func.distinct(FollowUp.lead_id)))
        .join(Lead, FollowUp.lead_id == Lead.id)
        .filter(
            FollowUp.deleted_at.is_(None),
            FollowUp.next_followup_at.isnot(None),
            datetime_utils.normalize_column(FollowUp.next_followup_at) <= today_end,
            Lead.deleted_at.is_(None),
            Lead.status.notin_(["enrolled", "invalid"]),
        )
    )
    pending_query = _apply_lead_owner_filter(pending_query, current_user)
    pending_followups = pending_query.scalar() or 0

    return {
        "total_leads": total_leads,
        "today_new_leads": today_new_leads,
        "pending_followups": pending_followups,
        "enrolled_leads": enrolled_leads,
    }


def get_today_followups(db: Session, current_user: User) -> list[dict]:
    """Return today's, overdue, and upcoming followups (max 30).

    Priority sorting:
    1. Overdue  (next_followup_at < today)
    2. Today    (next_followup_at == today)
    3. Upcoming (next_followup_at > today, within 3 days)

    Excludes enrolled and invalid leads.
    Deduplicates by lead_id — keeps the earliest next_followup_at per lead.
    """

    now = datetime_utils.business_now()
    today_str = now.strftime("%Y-%m-%d")
    today_start = today_str + " 00:00:00"
    today_end = today_str + " 23:59:59"
    upcoming_end = (now + datetime.timedelta(days=3)).strftime("%Y-%m-%d") + " 23:59:59"

    from app.models.course import Course

    # Subquery: earliest next_followup_at per lead — min over the normalised
    # value so mixed T / space formats resolve to the true earliest time.
    earliest_fu = (
        db.query(
            FollowUp.lead_id,
            func.min(datetime_utils.normalize_column(FollowUp.next_followup_at)).label("earliest_next"),
        )
        .filter(
            FollowUp.deleted_at.is_(None),
            FollowUp.next_followup_at.isnot(None),
            datetime_utils.normalize_column(FollowUp.next_followup_at) <= upcoming_end,
        )
        .group_by(FollowUp.lead_id)
        .subquery("earliest_fu")
    )

    # Correlated subquery: latest followup content for each lead
    latest_content_subq = (
        db.query(FollowUp.content)
        .filter(
            FollowUp.lead_id == Lead.id,
            FollowUp.deleted_at.is_(None),
        )
        .order_by(FollowUp.created_at.desc(), FollowUp.id.desc())
        .limit(1)
        .correlate(Lead)
        .scalar_subquery()
    )

    query = (
        db.query(
            Lead.id.label("lead_id"),
            Lead.name.label("lead_name"),
            Lead.phone,
            Lead.status,
            Lead.intention_level,
            earliest_fu.c.earliest_next.label("next_followup_at"),
            Lead.owner_id,
            User.real_name.label("owner_name"),
            Course.name.label("intended_course_name"),
            latest_content_subq.label("latest_followup_content"),
        )
        .join(earliest_fu, Lead.id == earliest_fu.c.lead_id)
        .outerjoin(Course, Lead.intended_course_id == Course.id)
        .outerjoin(User, Lead.owner_id == User.id)
        .filter(
            Lead.deleted_at.is_(None),
            Lead.status.notin_(["enrolled", "invalid"]),
        )
    )

    # Role-based filtering
    if current_user.role == "counselor":
        query = query.filter(Lead.owner_id == current_user.id)

    results = query.all()

    # Build response with priority classification and content truncation
    items = []
    for row in results:
        # Classify priority — normalise so both "T" and space formats compare
        # correctly against the day boundaries.
        next_at = datetime_utils.normalize_datetime(row.next_followup_at) or ""
        if next_at < today_start:
            priority = "overdue"
        elif next_at <= today_end:
            priority = "today"
        else:
            priority = "upcoming"

        # Truncate latest content for summary display
        content = row.latest_followup_content
        if content and len(content) > 50:
            content = content[:50] + "..."

        items.append({
            "lead_id": row.lead_id,
            "lead_name": row.lead_name,
            "phone": row.phone,
            "status": row.status,
            "intention_level": row.intention_level,
            "next_followup_at": row.next_followup_at,
            "owner_id": row.owner_id,
            "owner_name": row.owner_name,
            "intended_course_name": row.intended_course_name,
            "latest_followup_content": content,
            "followup_priority": priority,
        })

    # Sort: overdue → today → upcoming, each group ASC by next_followup_at
    priority_order = {"overdue": 0, "today": 1, "upcoming": 2}
    items.sort(key=lambda x: (
        priority_order.get(x["followup_priority"], 9),
        datetime_utils.normalize_datetime(x["next_followup_at"]) or "",
    ))

    return items[:30]


def _enrich_owner_names(db: Session, leads: list[Lead]) -> None:
    """Attach owner_name (User.real_name) to each Lead object in-place."""
    if not leads:
        return
    owner_ids = {lead.owner_id for lead in leads if lead.owner_id is not None}
    owner_map: dict[int, str] = {}
    if owner_ids:
        users = db.query(User).filter(User.id.in_(owner_ids)).all()
        owner_map = {u.id: u.real_name for u in users}
    for lead in leads:
        lead.owner_name = (
            owner_map.get(lead.owner_id) if lead.owner_id is not None else None
        )


def get_recent_leads(db: Session, current_user: User) -> list[Lead]:
    """Return the 10 most recently created non-deleted leads."""

    query = (
        db.query(Lead)
        .filter(Lead.deleted_at.is_(None))
    )
    query = _apply_lead_owner_filter(query, current_user)

    leads = (
        query
        .order_by(Lead.created_at.desc())
        .limit(10)
        .all()
    )
    _enrich_owner_names(db, leads)
    return leads
