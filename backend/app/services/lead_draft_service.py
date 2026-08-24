"""Lead draft service — query, edit, confirm, and discard lead drafts."""

import datetime
import logging

from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.lead_draft import LeadDraft
from app.models.user import User
from app.services import resume_field_rules

logger = logging.getLogger(__name__)

# Statuses that may still be confirmed into a formal Lead.
# `pending` is the legacy single-import status and must keep working.
CONFIRMABLE_STATUSES = ("pending", "ready", "needs_review")
# Statuses a human may still edit or discard.
EDITABLE_STATUSES = ("pending", "ready", "needs_review", "duplicate")

# Fields a consultant may correct during human review.
EDITABLE_FIELDS = (
    "name", "phone", "wechat", "email", "gender", "age", "education",
    "school", "major", "graduation_time", "city", "work_years",
    "latest_company", "latest_position", "skills",
)


def get_lead_draft_by_id(db: Session, draft_id: int) -> LeadDraft | None:
    """Get a lead draft by ID."""
    return db.query(LeadDraft).filter(LeadDraft.id == draft_id).first()


def check_draft_access(draft: LeadDraft, current_user: User) -> bool:
    """Return True if current_user can access the given draft.

    - admin / manager: can access all drafts.
    - counselor: can only access drafts they created.
    """
    if current_user.role in ("admin", "manager"):
        return True
    return draft.created_by == current_user.id


def confirm_draft(
    db: Session,
    draft: LeadDraft,
    confirm_data: dict,
    current_user: User,
) -> Lead:
    """Confirm a lead draft and create a formal Lead.

    Rules:
        - Fields in confirm_data take precedence over draft fields.
        - name defaults to "未命名线索" if empty.
        - counselor: owner_id is forced to current_user.id.
        - admin/manager: can use the owner_id from confirm_data.
        - draft status is updated to 'confirmed' and confirmed_lead_id is set.

    Returns the newly created Lead.
    """
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Merge: confirm_data fields (non-None) override draft fields
    lead_data: dict = {
        "name": draft.name,
        "phone": draft.phone,
        "wechat": draft.wechat,
        "email": draft.email,
        "gender": draft.gender,
        "age": draft.age,
        "education": draft.education,
        "school": draft.school,
        "major": draft.major,
        "city": draft.city,
        "work_years": draft.work_years,
        "latest_company": draft.latest_company,
        "latest_position": draft.latest_position,
        "ai_summary": draft.ai_summary,
        "ai_course_suggestion": draft.ai_course_suggestion,
    }

    # Override with confirm_data (only non-None fields)
    for key, value in confirm_data.items():
        if value is not None:
            # Map request field names to lead field names
            if key == "current_job":
                lead_data["current_job"] = value
            elif key in lead_data:
                lead_data[key] = value
            elif key not in ("source_id", "intended_course_id", "owner_id", "remark"):
                # Skip unknown keys
                pass

    # Set name default
    if not lead_data.get("name"):
        lead_data["name"] = "未命名线索"

    # Set source_id, intended_course_id, owner_id, remark from confirm_data
    source_id = confirm_data.get("source_id") or 2  # Default: 简历上传
    intended_course_id = confirm_data.get("intended_course_id")
    owner_id = confirm_data.get("owner_id")
    remark = confirm_data.get("remark") or "由简历导入生成"

    # Owner assignment
    if current_user.role == "counselor":
        owner_id = current_user.id
    elif owner_id is None:
        owner_id = current_user.id

    # Create Lead
    lead = Lead(
        name=lead_data["name"],
        phone=lead_data.get("phone"),
        wechat=lead_data.get("wechat"),
        email=lead_data.get("email"),
        gender=lead_data.get("gender"),
        age=lead_data.get("age"),
        education=lead_data.get("education"),
        school=lead_data.get("school"),
        major=lead_data.get("major"),
        city=lead_data.get("city"),
        work_years=lead_data.get("work_years"),
        latest_company=lead_data.get("latest_company"),
        latest_position=lead_data.get("latest_position"),
        intended_course_id=intended_course_id,
        source_id=source_id,
        status="new",
        owner_id=owner_id,
        remark=remark,
        ai_summary=lead_data.get("ai_summary"),
        ai_course_suggestion=lead_data.get("ai_course_suggestion"),
        created_at=now,
        updated_at=now,
    )

    db.add(lead)
    db.commit()
    db.refresh(lead)

    # Update draft status
    draft.status = "confirmed"
    draft.confirmed_lead_id = lead.id
    draft.name = lead_data["name"]  # Sync back the final name
    draft.updated_at = now
    db.commit()

    return lead


def discard_draft(
    db: Session,
    draft: LeadDraft,
) -> None:
    """Discard a lead draft by setting status to 'discarded'."""
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    draft.status = "discarded"
    draft.updated_at = now
    db.commit()


def update_draft(
    db: Session,
    draft: LeadDraft,
    update_data: dict,
) -> LeadDraft:
    """Apply a human review edit to a draft and re-resolve its status.

    A draft is only promoted to `ready` when it now carries a name AND a valid
    mainland mobile number AND that number is not already in the CRM. Because a
    person supplied the values, the confidence flags for the fields they filled
    in are raised and the matching conflicts cleared.

    Batch drafts only — legacy `pending` drafts keep their status so the
    single-resume flow behaves exactly as before.
    """
    # Imported here to avoid a circular import at module load time.
    from app.services.resume_batch_service import (
        STATUS_DUPLICATE,
        STATUS_NEEDS_REVIEW,
        STATUS_READY,
        find_duplicate_lead,
    )

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conflicts = resume_field_rules.load_conflicts(draft.conflict_flags)

    for field in EDITABLE_FIELDS:
        if field not in update_data:
            continue
        value = update_data[field]
        if isinstance(value, str):
            value = value.strip() or None

        if field == "name" and value:
            value = resume_field_rules.normalize_name(value)
            draft.name_confidence = resume_field_rules.CONF_HIGH
            conflicts.pop("name", None)
        elif field == "phone" and value:
            normalized = resume_field_rules.normalize_phone(value)
            # Keep what the human typed if it is not a mainland mobile; the
            # status resolution below will hold the draft in review.
            value = normalized or value
            if normalized:
                draft.phone_confidence = resume_field_rules.CONF_HIGH
                conflicts.pop("phone", None)

        setattr(draft, field, value)

    draft.conflict_flags = resume_field_rules.dump_conflicts(conflicts)

    # Legacy single-import drafts keep the original two-state behaviour.
    if draft.status != "pending":
        has_name = bool(draft.name and draft.name.strip())
        has_phone = resume_field_rules.is_valid_phone(draft.phone)

        if not (has_name and has_phone):
            draft.status = STATUS_NEEDS_REVIEW
            draft.duplicate_lead_id = None
        else:
            duplicate = find_duplicate_lead(db, draft.phone)
            if duplicate:
                draft.status = STATUS_DUPLICATE
                draft.duplicate_lead_id = duplicate["existing_lead_id"]
            else:
                draft.status = STATUS_READY
                draft.duplicate_lead_id = None

    draft.updated_at = now
    db.commit()
    db.refresh(draft)
    return draft
