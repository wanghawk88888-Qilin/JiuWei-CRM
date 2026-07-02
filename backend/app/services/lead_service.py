import datetime

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.followup import FollowUp
from app.models.lead import Lead
from app.models.user import User


def create_lead(db: Session, lead_data: dict, current_user: User) -> Lead:
    """Create a new lead.

    If current_user is a counselor, owner_id is forced to current_user.id.
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Counselor must always own the leads they create
    if current_user.role == "counselor":
        lead_data["owner_id"] = current_user.id

    lead = Lead(**lead_data)
    lead.created_at = now
    lead.updated_at = now

    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def get_lead_by_id(db: Session, lead_id: int) -> Lead | None:
    """Get a lead by ID, excluding soft-deleted records."""
    return (
        db.query(Lead)
        .filter(Lead.id == lead_id, Lead.deleted_at.is_(None))
        .first()
    )


def _enrich_lead_items_with_followup(
    db: Session, items: list[Lead]
) -> None:
    """Attach latest followup info (by, by_name, at, next_at) to each Lead object in-place."""
    if not items:
        return

    lead_ids = [item.id for item in items]

    # Subquery: max created_at per lead for non-deleted followups
    latest_time_subq = (
        db.query(
            FollowUp.lead_id,
            func.max(FollowUp.created_at).label("max_created_at"),
        )
        .filter(
            FollowUp.lead_id.in_(lead_ids),
            FollowUp.deleted_at.is_(None),
        )
        .group_by(FollowUp.lead_id)
        .subquery()
    )

    # Get the actual latest FollowUp rows
    latest_fus = (
        db.query(FollowUp)
        .join(
            latest_time_subq,
            and_(
                FollowUp.lead_id == latest_time_subq.c.lead_id,
                FollowUp.created_at == latest_time_subq.c.max_created_at,
            ),
        )
        .filter(FollowUp.deleted_at.is_(None))
        .all()
    )

    fu_map: dict[int, FollowUp] = {}
    for fu in latest_fus:
        # In case of ties, keep the one with higher id (most recent insert)
        existing = fu_map.get(fu.lead_id)
        if existing is None or fu.id > existing.id:
            fu_map[fu.lead_id] = fu

    # Batch-fetch user names
    user_ids = list({fu.created_by for fu in fu_map.values()})
    user_map: dict[int, str] = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        user_map = {u.id: u.real_name for u in users}

    # Attach to lead objects
    for item in items:
        fu = fu_map.get(item.id)
        if fu:
            item.last_followup_by = fu.created_by
            item.last_followup_by_name = user_map.get(fu.created_by) or "未知用户"
            item.last_followup_at = fu.created_at
            item.next_followup_at = fu.next_followup_at
        else:
            item.last_followup_by = None
            item.last_followup_by_name = None
            item.last_followup_at = None
            item.next_followup_at = None


def list_leads(
    db: Session,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    status: str | None = None,
    source_id: int | None = None,
    owner_id: int | None = None,
) -> tuple[list[Lead], int]:
    """List leads with search, filter, pagination and role-based permission filtering.

    Returns (items, total).
    """
    query = db.query(Lead).filter(Lead.deleted_at.is_(None))

    # Keyword search: name / phone / wechat (fuzzy LIKE)
    if keyword:
        like_pattern = f"%{keyword}%"
        query = query.filter(
            Lead.name.like(like_pattern)
            | Lead.phone.like(like_pattern)
            | Lead.wechat.like(like_pattern)
        )

    # Exact-match filters
    if status:
        query = query.filter(Lead.status == status)
    if source_id is not None:
        query = query.filter(Lead.source_id == source_id)

    # Owner filter — counselors are forced to their own data regardless of param
    if current_user.role == "counselor":
        query = query.filter(Lead.owner_id == current_user.id)
    elif owner_id is not None:
        query = query.filter(Lead.owner_id == owner_id)
    # admin / manager: if owner_id is not passed, see all leads

    total = query.count()
    items = (
        query
        .order_by(Lead.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Enrich with latest followup info
    _enrich_lead_items_with_followup(db, items)

    return items, total


def update_lead(db: Session, lead: Lead, update_data: dict) -> Lead:
    """Update a lead with partial data. Updates updated_at automatically."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for key, value in update_data.items():
        if value is not None:
            setattr(lead, key, value)

    lead.updated_at = now
    db.commit()
    db.refresh(lead)
    return lead


def delete_lead(db: Session, lead: Lead) -> None:
    """Soft-delete a lead by setting deleted_at."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lead.deleted_at = now
    lead.updated_at = now
    db.commit()
