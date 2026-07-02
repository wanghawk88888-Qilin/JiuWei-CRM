import datetime

from sqlalchemy.orm import Session

from app.models.followup import FollowUp
from app.models.lead import Lead
from app.models.user import User


def list_followups_by_lead(db: Session, lead_id: int) -> list[dict]:
    """List all follow-ups for a lead with creator name, excluding soft-deleted records."""
    results = (
        db.query(FollowUp, User.real_name)
        .outerjoin(User, FollowUp.created_by == User.id)
        .filter(
            FollowUp.lead_id == lead_id,
            FollowUp.deleted_at.is_(None),
        )
        .order_by(FollowUp.created_at.desc())
        .all()
    )

    followups = []
    for fu, real_name in results:
        followups.append({
            "id": fu.id,
            "lead_id": fu.lead_id,
            "followup_type": fu.followup_type,
            "content": fu.content,
            "intention_level": fu.intention_level,
            "next_followup_at": fu.next_followup_at,
            "created_by": fu.created_by,
            "created_by_name": real_name if real_name else "未知用户",
            "created_at": fu.created_at,
            "updated_at": fu.updated_at,
        })

    return followups


def get_followup_by_id(db: Session, followup_id: int) -> FollowUp | None:
    """Get a follow-up by ID, excluding soft-deleted records."""
    return (
        db.query(FollowUp)
        .filter(FollowUp.id == followup_id, FollowUp.deleted_at.is_(None))
        .first()
    )


def create_followup(
    db: Session, lead_id: int, followup_data: dict, current_user: User
) -> FollowUp:
    """Create a new follow-up record and sync the lead's status, intention_level, and updated_at."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    followup = FollowUp(
        lead_id=lead_id,
        followup_type=followup_data["followup_type"],
        content=followup_data["content"],
        intention_level=followup_data.get("intention_level"),
        next_followup_at=followup_data.get("next_followup_at"),
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )

    db.add(followup)

    # Sync lead: update status, updated_at, and optionally intention_level
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.deleted_at.is_(None)).first()
    if lead:
        lead.updated_at = now
        # Rule 1: auto-transition "new" → "following" on first follow-up
        if lead.status == "new":
            lead.status = "following"
        # Rule 2: sync intention_level if provided
        if followup_data.get("intention_level") is not None:
            lead.intention_level = followup_data["intention_level"]

    db.commit()
    db.refresh(followup)
    return followup


def delete_followup(db: Session, followup: FollowUp) -> None:
    """Soft-delete a follow-up by setting deleted_at."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    followup.deleted_at = now
    followup.updated_at = now
    db.commit()
