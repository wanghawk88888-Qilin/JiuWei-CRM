"""Resume batch import service.

Pipeline for one batch:

    upload  -> save every file + ImportLog(pending), return batch_id
    parse   -> per-file, fully isolated:
                   text extract -> rule parse -> validate
                   -> confidence / conflict -> duplicate check -> LeadDraft
    review  -> humans fix needs_review drafts (see lead_draft_service)
    confirm -> create a Lead for every `ready` draft, idempotently

Two rules drive every design decision here:

1.  **Never guess.** A draft only becomes `ready` when BOTH the name and the
    phone were extracted with high confidence and the phone is not already in
    the CRM. Anything else goes to a human.
2.  **Never let one file sink the batch.** Each file is parsed in its own
    try/except with its own transaction boundary; a failure rolls back that
    file only and records a reason.
"""

import datetime
import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import SessionLocal
from app.models.import_log import ImportLog
from app.models.lead import Lead
from app.models.lead_draft import LeadDraft
from app.models.resume_import_batch import ResumeImportBatch
from app.models.user import User
from app.services import lead_draft_service, resume_field_rules
from app.services.llm_extract_service import enhance_resume_extract
from app.services.resume_import_service import (
    ALLOWED_EXTENSIONS,
    handle_temp_file_deletion,
    save_temp_file,
)
from app.services.resume_parser_service import ResumeParseError, parse_resume_text

logger = logging.getLogger(__name__)

# -- Draft statuses used by the batch flow ----------------------------------

STATUS_READY = "ready"
STATUS_NEEDS_REVIEW = "needs_review"
STATUS_DUPLICATE = "duplicate"
STATUS_FAILED = "failed"
STATUS_CONFIRMED = "confirmed"
STATUS_CONFIRMING = "confirming"
STATUS_DISCARDED = "discarded"

# Statuses a human can still act on.
ACTIONABLE_DRAFT_STATUSES = (STATUS_READY, STATUS_NEEDS_REVIEW, STATUS_DUPLICATE)

# -- Batch statuses ---------------------------------------------------------

BATCH_PROCESSING = "processing"
BATCH_READY = "ready"
BATCH_PARTIALLY_READY = "partially_ready"
BATCH_COMPLETED = "completed"
BATCH_FAILED = "failed"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def max_file_size_bytes() -> int:
    return settings.RESUME_MAX_FILE_SIZE_MB * 1024 * 1024


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def build_phone_index(db: Session) -> dict[str, dict]:
    """Map every active Lead's normalised phone to its identity.

    Existing rows may hold phones in whatever shape they were entered, so both
    sides are normalised before comparison. The index is rebuilt per batch run
    and per confirm call — small CRMs make this cheap and always-fresh.
    """
    index: dict[str, dict] = {}
    rows = (
        db.query(Lead.id, Lead.name, Lead.phone)
        .filter(Lead.deleted_at.is_(None), Lead.phone.isnot(None))
        .all()
    )
    for lead_id, name, phone in rows:
        normalized = resume_field_rules.normalize_phone(phone) or (phone or "").strip()
        if not normalized:
            continue
        # Keep the earliest lead when duplicates already exist in the data.
        index.setdefault(
            normalized,
            {"existing_lead_id": lead_id, "existing_lead_name": name,
             "existing_phone": phone},
        )
    return index


def find_duplicate_lead(db: Session, phone: str | None) -> dict | None:
    """Look up a single phone against the existing Leads."""
    normalized = resume_field_rules.normalize_phone(phone)
    if not normalized:
        return None
    return build_phone_index(db).get(normalized)


# ---------------------------------------------------------------------------
# Draft status resolution
# ---------------------------------------------------------------------------

def resolve_draft_status(profile: dict, duplicate: dict | None) -> str:
    """Decide a draft's status from its extraction confidence + duplicate check.

    A duplicate phone always wins: we must never create a second Lead for a
    number the CRM already knows.
    """
    if duplicate:
        return STATUS_DUPLICATE
    if profile.get("auto_confirmable"):
        return STATUS_READY
    return STATUS_NEEDS_REVIEW


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

class BatchValidationError(ValueError):
    """Raised for whole-batch rejections (too many files, empty upload)."""

    def __init__(self, error_code: str, message: str):
        super().__init__(f"{error_code}|{message}")
        self.error_code = error_code
        self.message = message


def create_batch(
    db: Session,
    files: list[UploadFile],
    current_user: User,
) -> ResumeImportBatch:
    """Persist the uploaded files and create the batch + one ImportLog per file.

    Files that fail validation (wrong type, too large) still get an ImportLog
    so the consultant can see exactly which upload was rejected and why.
    """
    if not files:
        raise BatchValidationError("NO_FILES_UPLOADED", "请至少选择一个文件")

    limit = settings.RESUME_BATCH_MAX_FILES
    if len(files) > limit:
        raise BatchValidationError(
            "BATCH_FILE_LIMIT_EXCEEDED",
            f"单次最多上传 {limit} 个文件，本次选择了 {len(files)} 个",
        )

    now = _now()
    batch = ResumeImportBatch(
        batch_no=f"RB{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                 f"{uuid.uuid4().hex[:6].upper()}",
        total_files=len(files),
        status=BATCH_PROCESSING,
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    for upload in files:
        filename = upload.filename or "unknown"
        ext = Path(filename).suffix.lower()

        import_log = ImportLog(
            batch_id=batch.id,
            file_name=filename[:255],
            file_type=ext.lstrip(".")[:20] or "unknown",
            parse_status="pending",
            created_by=current_user.id,
            created_at=now,
            updated_at=now,
        )

        if ext not in ALLOWED_EXTENSIONS:
            import_log.parse_status = STATUS_FAILED
            import_log.error_code = "INVALID_FILE_TYPE"
            import_log.parse_error = f"不支持的文件类型: {ext or '未知'}"
            db.add(import_log)
            db.commit()
            continue

        try:
            temp_path, _original, file_size = save_temp_file(upload)
        except Exception as exc:  # noqa: BLE001 — one file must not sink the batch
            logger.exception("Failed to persist uploaded file %s", filename)
            import_log.parse_status = STATUS_FAILED
            import_log.error_code = "FILE_SAVE_FAILED"
            import_log.parse_error = str(exc)[:500]
            db.add(import_log)
            db.commit()
            continue

        if file_size > max_file_size_bytes():
            import_log.parse_status = STATUS_FAILED
            import_log.error_code = "FILE_TOO_LARGE"
            import_log.parse_error = (
                f"文件超过 {settings.RESUME_MAX_FILE_SIZE_MB}MB 限制"
            )
            import_log.file_size = file_size
            import_log.temp_file_path = temp_path
            db.add(import_log)
            db.commit()
            handle_temp_file_deletion(db, import_log)
            continue

        import_log.file_size = file_size
        import_log.temp_file_path = temp_path
        db.add(import_log)
        db.commit()

    refresh_batch_counters(db, batch)
    return batch


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def process_batch_files(batch_id: int) -> None:
    """Parse every pending file of a batch. Safe to run as a background task.

    Opens its own session because the request-scoped one is already closed by
    the time FastAPI runs background tasks.
    """
    db = SessionLocal()
    try:
        batch = db.query(ResumeImportBatch).filter(
            ResumeImportBatch.id == batch_id
        ).first()
        if batch is None:
            logger.error("Batch %s disappeared before processing", batch_id)
            return

        pending_logs = (
            db.query(ImportLog)
            .filter(ImportLog.batch_id == batch_id, ImportLog.parse_status == "pending")
            .order_by(ImportLog.id)
            .all()
        )

        # Phones already claimed inside this same batch, so two copies of the
        # same resume do not both become `ready`.
        phone_index = build_phone_index(db)
        seen_in_batch: dict[str, int] = {}

        for import_log in pending_logs:
            try:
                process_single_file(db, batch, import_log, phone_index, seen_in_batch)
            except Exception as exc:  # noqa: BLE001 — isolate this file only
                logger.exception(
                    "Unhandled error parsing file %s (import_log=%s)",
                    import_log.file_name,
                    import_log.id,
                )
                db.rollback()
                _mark_log_failed(db, import_log, "INTERNAL_ERROR", str(exc)[:500])

        refresh_batch_counters(db, batch)
    finally:
        db.close()


def _mark_log_failed(
    db: Session, import_log: ImportLog, error_code: str, message: str
) -> None:
    """Record a per-file failure without touching the rest of the batch."""
    try:
        import_log.parse_status = STATUS_FAILED
        import_log.error_code = error_code
        import_log.parse_error = message
        import_log.updated_at = _now()
        db.commit()
        handle_temp_file_deletion(db, import_log)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to record failure for import_log=%s", import_log.id)
        db.rollback()


def process_single_file(
    db: Session,
    batch: ResumeImportBatch,
    import_log: ImportLog,
    phone_index: dict[str, dict],
    seen_in_batch: dict[str, int],
) -> LeadDraft | None:
    """Parse one file and create its LeadDraft. Errors are contained here."""
    now = _now()

    if not import_log.temp_file_path:
        _mark_log_failed(db, import_log, "FILE_MISSING", "临时文件不存在")
        return None

    # 1. Text extraction
    try:
        text = parse_resume_text(import_log.temp_file_path, import_log.file_type)
    except ResumeParseError as exc:
        _mark_log_failed(db, import_log, exc.error_code, exc.message)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.exception("Text extraction failed for %s", import_log.file_name)
        db.rollback()
        _mark_log_failed(db, import_log, "PARSE_FAILED", str(exc)[:500])
        return None

    # 2-4. Rule parse -> validate -> confidence / conflict detection
    profile = resume_field_rules.extract_profile(text)

    # 5. AI enhancement — no-op in v0.2.1, kept as the extension point.
    ai_result = enhance_resume_extract(text)

    # 6. Duplicate detection against existing Leads and against this batch.
    duplicate = None
    if profile["phone"]:
        duplicate = phone_index.get(profile["phone"])
        if duplicate is None and profile["phone"] in seen_in_batch:
            duplicate = {
                "existing_lead_id": None,
                "existing_lead_name": None,
                "existing_phone": profile["phone"],
                "in_batch_draft_id": seen_in_batch[profile["phone"]],
            }

    status = resolve_draft_status(profile, duplicate)

    draft = LeadDraft(
        import_log_id=import_log.id,
        batch_id=batch.id,
        name=profile["name"],
        phone=profile["phone"],
        wechat=profile["wechat"],
        email=profile["email"],
        gender=profile["gender"],
        age=profile["age"],
        education=profile["education"],
        school=profile["school"],
        major=profile["major"],
        graduation_time=profile["graduation_time"],
        city=profile["city"],
        work_years=profile["work_years"],
        latest_company=profile["latest_company"],
        latest_position=profile["latest_position"],
        skills=profile["skills"],
        ai_summary=ai_result.get("ai_summary"),
        ai_course_suggestion=ai_result.get("ai_course_suggestion"),
        raw_text_excerpt=text[:1000],
        status=status,
        name_confidence=profile["name_confidence"],
        phone_confidence=profile["phone_confidence"],
        conflict_flags=resume_field_rules.dump_conflicts(profile["conflicts"]),
        duplicate_lead_id=(duplicate or {}).get("existing_lead_id"),
        created_by=import_log.created_by,
        created_at=now,
        updated_at=now,
    )
    db.add(draft)

    import_log.parse_status = "parsed"
    import_log.error_code = None
    import_log.parse_error = None
    import_log.extracted_text_length = len(text)
    import_log.llm_used = int(ai_result.get("llm_used", False))
    import_log.llm_provider = ai_result.get("llm_provider")
    import_log.updated_at = now
    db.commit()
    db.refresh(draft)

    if profile["phone"] and profile["phone"] not in seen_in_batch:
        seen_in_batch[profile["phone"]] = draft.id

    # 7. Temp file handling per the existing retention policy.
    handle_temp_file_deletion(db, import_log)
    return draft


# ---------------------------------------------------------------------------
# Counters and batch status
# ---------------------------------------------------------------------------

def refresh_batch_counters(db: Session, batch: ResumeImportBatch) -> ResumeImportBatch:
    """Recompute the batch's counters and overall status from its children."""
    logs = db.query(ImportLog).filter(ImportLog.batch_id == batch.id).all()
    drafts = db.query(LeadDraft).filter(LeadDraft.batch_id == batch.id).all()

    by_status: dict[str, int] = {}
    for draft in drafts:
        by_status[draft.status] = by_status.get(draft.status, 0) + 1

    failed_files = sum(1 for log in logs if log.parse_status == STATUS_FAILED)
    pending_files = sum(1 for log in logs if log.parse_status == "pending")

    batch.total_files = len(logs) or batch.total_files
    batch.parsed_count = len(drafts)
    batch.ready_count = by_status.get(STATUS_READY, 0)
    batch.needs_review_count = by_status.get(STATUS_NEEDS_REVIEW, 0)
    batch.duplicate_count = by_status.get(STATUS_DUPLICATE, 0)
    batch.failed_count = failed_files
    batch.confirmed_count = by_status.get(STATUS_CONFIRMED, 0)

    if pending_files:
        batch.status = BATCH_PROCESSING
    elif failed_files == batch.total_files and batch.total_files > 0:
        batch.status = BATCH_FAILED
    elif batch.ready_count == 0 and batch.needs_review_count == 0:
        # Nothing left for a human to act on.
        batch.status = (
            BATCH_COMPLETED
            if batch.confirmed_count or batch.duplicate_count
            else BATCH_FAILED
        )
    elif (
        batch.ready_count == batch.total_files
        and batch.needs_review_count == 0
        and batch.duplicate_count == 0
        and failed_files == 0
    ):
        batch.status = BATCH_READY
    else:
        batch.status = BATCH_PARTIALLY_READY

    batch.updated_at = _now()
    db.commit()
    db.refresh(batch)
    return batch


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

def check_batch_access(batch: ResumeImportBatch, current_user: User) -> bool:
    """admin/manager see every batch; a counselor sees only their own."""
    if current_user.role in ("admin", "manager"):
        return True
    return batch.created_by == current_user.id


def get_batch(db: Session, batch_id: int) -> ResumeImportBatch | None:
    return (
        db.query(ResumeImportBatch)
        .filter(ResumeImportBatch.id == batch_id)
        .first()
    )


# ---------------------------------------------------------------------------
# Batch detail view
# ---------------------------------------------------------------------------

def build_batch_detail(db: Session, batch: ResumeImportBatch) -> dict:
    """Assemble the batch summary plus one row per uploaded file."""
    logs = (
        db.query(ImportLog)
        .filter(ImportLog.batch_id == batch.id)
        .order_by(ImportLog.id)
        .all()
    )
    drafts = db.query(LeadDraft).filter(LeadDraft.batch_id == batch.id).all()
    drafts_by_log = {d.import_log_id: d for d in drafts}

    duplicate_lead_ids = {
        d.duplicate_lead_id for d in drafts if d.duplicate_lead_id is not None
    }
    leads_by_id: dict[int, Lead] = {}
    if duplicate_lead_ids:
        for lead in db.query(Lead).filter(Lead.id.in_(duplicate_lead_ids)).all():
            leads_by_id[lead.id] = lead

    items: list[dict] = []
    for log in logs:
        draft = drafts_by_log.get(log.id)
        item: dict = {
            "import_log_id": log.id,
            "file_name": log.file_name,
            "file_type": log.file_type,
            "file_size": log.file_size,
            "parse_status": log.parse_status,
            "error_code": log.error_code,
            "error_message": log.parse_error,
            "lead_draft_id": None,
            "status": STATUS_FAILED if log.parse_status == STATUS_FAILED else log.parse_status,
            "name": None,
            "phone": None,
            "email": None,
            "education": None,
            "school": None,
            "major": None,
            "name_confidence": None,
            "phone_confidence": None,
            "conflicts": {},
            "duplicate": None,
            "confirmed_lead_id": None,
        }

        if draft is not None:
            conflicts = resume_field_rules.load_conflicts(draft.conflict_flags)
            item.update(
                {
                    "lead_draft_id": draft.id,
                    "status": draft.status,
                    "name": draft.name,
                    "phone": draft.phone,
                    "email": draft.email,
                    "education": draft.education,
                    "school": draft.school,
                    "major": draft.major,
                    "name_confidence": draft.name_confidence,
                    "phone_confidence": draft.phone_confidence,
                    "conflicts": conflicts,
                    "confirmed_lead_id": draft.confirmed_lead_id,
                }
            )
            if draft.status == STATUS_DUPLICATE:
                existing = leads_by_id.get(draft.duplicate_lead_id or -1)
                item["duplicate"] = {
                    "existing_lead_id": draft.duplicate_lead_id,
                    "existing_lead_name": existing.name if existing else None,
                    "existing_phone": existing.phone if existing else draft.phone,
                    # No matching Lead means the clash is with another file in
                    # this very batch.
                    "in_batch": draft.duplicate_lead_id is None,
                }

        items.append(item)

    return {
        "batch": {
            "id": batch.id,
            "batch_no": batch.batch_no,
            "status": batch.status,
            "total_files": batch.total_files,
            "parsed_count": batch.parsed_count,
            "ready_count": batch.ready_count,
            "needs_review_count": batch.needs_review_count,
            "duplicate_count": batch.duplicate_count,
            "failed_count": batch.failed_count,
            "confirmed_count": batch.confirmed_count,
            "created_by": batch.created_by,
            "created_at": batch.created_at,
            "updated_at": batch.updated_at,
        },
        "items": items,
    }


def list_batches(db: Session, current_user: User, limit: int = 20) -> list[dict]:
    """Recent batches visible to the current user."""
    query = db.query(ResumeImportBatch)
    if current_user.role not in ("admin", "manager"):
        query = query.filter(ResumeImportBatch.created_by == current_user.id)
    batches = query.order_by(ResumeImportBatch.id.desc()).limit(limit).all()
    return [
        {
            "id": b.id,
            "batch_no": b.batch_no,
            "status": b.status,
            "total_files": b.total_files,
            "ready_count": b.ready_count,
            "needs_review_count": b.needs_review_count,
            "duplicate_count": b.duplicate_count,
            "failed_count": b.failed_count,
            "confirmed_count": b.confirmed_count,
            "created_at": b.created_at,
        }
        for b in batches
    ]


# ---------------------------------------------------------------------------
# Confirm
# ---------------------------------------------------------------------------

def confirm_batch(
    db: Session,
    batch: ResumeImportBatch,
    current_user: User,
    defaults: dict | None = None,
) -> dict:
    """Create a Lead for every `ready` draft in the batch.

    Idempotency (P0): each draft is claimed with a conditional UPDATE that only
    succeeds while it is still `ready` and has no `confirmed_lead_id`. A second
    click therefore claims nothing and creates nothing. Duplicates and failures
    are never confirmed.
    """
    defaults = defaults or {}
    created: list[dict] = []
    skipped: list[dict] = []

    draft_ids = [
        row[0]
        for row in db.query(LeadDraft.id)
        .filter(
            LeadDraft.batch_id == batch.id,
            LeadDraft.status == STATUS_READY,
            LeadDraft.confirmed_lead_id.is_(None),
        )
        .order_by(LeadDraft.id)
        .all()
    ]

    for draft_id in draft_ids:
        # Atomic claim — the guard against double submission.
        claimed = (
            db.query(LeadDraft)
            .filter(
                LeadDraft.id == draft_id,
                LeadDraft.status == STATUS_READY,
                LeadDraft.confirmed_lead_id.is_(None),
            )
            .update({"status": STATUS_CONFIRMING}, synchronize_session=False)
        )
        db.commit()
        if claimed == 0:
            skipped.append({"lead_draft_id": draft_id, "reason": "ALREADY_CONFIRMED"})
            continue

        draft = db.query(LeadDraft).filter(LeadDraft.id == draft_id).first()
        if draft is None:
            continue

        try:
            # Re-validate against live data: a Lead with this phone may have
            # been created by someone else since the batch was parsed.
            if not draft.name or not resume_field_rules.is_valid_phone(draft.phone):
                draft.status = STATUS_NEEDS_REVIEW
                draft.updated_at = _now()
                db.commit()
                skipped.append(
                    {"lead_draft_id": draft_id, "reason": "INCOMPLETE_REQUIRED_FIELDS"}
                )
                continue

            duplicate = find_duplicate_lead(db, draft.phone)
            if duplicate:
                draft.status = STATUS_DUPLICATE
                draft.duplicate_lead_id = duplicate["existing_lead_id"]
                draft.updated_at = _now()
                db.commit()
                skipped.append(
                    {
                        "lead_draft_id": draft_id,
                        "reason": "DUPLICATE_PHONE",
                        "existing_lead_id": duplicate["existing_lead_id"],
                    }
                )
                continue

            # confirm_draft sets status=confirmed and confirmed_lead_id.
            lead = lead_draft_service.confirm_draft(db, draft, dict(defaults), current_user)
            created.append({"lead_draft_id": draft_id, "lead_id": lead.id})
        except Exception as exc:  # noqa: BLE001 — isolate this draft only
            logger.exception("Failed to confirm draft %s", draft_id)
            db.rollback()
            db.query(LeadDraft).filter(
                LeadDraft.id == draft_id, LeadDraft.confirmed_lead_id.is_(None)
            ).update({"status": STATUS_READY}, synchronize_session=False)
            db.commit()
            skipped.append(
                {"lead_draft_id": draft_id, "reason": "CONFIRM_FAILED",
                 "message": str(exc)[:200]}
            )

    refresh_batch_counters(db, batch)

    return {
        "batch_id": batch.id,
        "confirmed_count": len(created),
        "skipped_count": len(skipped),
        "created": created,
        "skipped": skipped,
        "batch_status": batch.status,
    }
