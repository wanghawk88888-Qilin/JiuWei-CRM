"""Resume import service — orchestrates the full resume upload → parse → draft pipeline."""

import datetime
import logging
import os
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.import_log import ImportLog
from app.models.lead_draft import LeadDraft
from app.models.user import User
from app.services.llm_extract_service import enhance_resume_extract
from app.services.resume_extract_service import extract_all
from app.services.resume_parser_service import ResumeParseError, parse_resume_text

logger = logging.getLogger(__name__)

# Supported file extensions. .doc is deliberately excluded: the current image
# has no stable converter for the legacy binary format, and v0.2.1 does not
# add heavyweight system dependencies.
ALLOWED_EXTENSIONS = {".docx", ".pdf"}

# Maximum file size, driven by settings so the single and batch paths agree.
MAX_FILE_SIZE = settings.RESUME_MAX_FILE_SIZE_MB * 1024 * 1024


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file type and size.

    Raises ValueError with a standard error_code message if invalid.
    """
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("INVALID_FILE_TYPE|文件类型不支持")

    # Check file size by reading the content
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise ValueError("FILE_TOO_LARGE|文件过大")


def save_temp_file(file: UploadFile) -> tuple[str, str, int]:
    """Save uploaded file to the temp upload directory.

    Returns (file_path, original_filename, file_size).
    """
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    original_filename = file.filename or "unknown"
    # Format: timestamp_uuid_original_filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    unique_name = f"{timestamp}_{uuid.uuid4().hex[:8]}_{original_filename}"
    file_path = upload_dir / unique_name

    content = file.file.read()
    file_size = len(content)

    with open(file_path, "wb") as f:
        f.write(content)

    return str(file_path), original_filename, file_size


def handle_temp_file_deletion(
    db: Session, import_log: ImportLog
) -> None:
    """Handle temp file according to system retention policy.

    - If TEMP_FILE_RETENTION_DAYS == 0: delete immediately, mark as deleted.
    - If TEMP_FILE_RETENTION_DAYS > 0: set expiration timestamp.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    retention_days = settings.TEMP_FILE_RETENTION_DAYS

    if retention_days == 0:
        # Delete immediately
        if import_log.temp_file_path and os.path.exists(import_log.temp_file_path):
            try:
                os.remove(import_log.temp_file_path)
            except OSError as e:
                logger.warning(f"Failed to delete temp file {import_log.temp_file_path}: {e}")
        import_log.file_deleted_at = now.strftime("%Y-%m-%d %H:%M:%S")
        # Keep a terminal 'failed' status: it is the only record of *why* a
        # file could not be imported. Overwriting it would lose that reason.
        if import_log.parse_status != "failed":
            import_log.parse_status = "deleted"
    else:
        # Keep for N days
        expires_at = now + datetime.timedelta(days=retention_days)
        import_log.temp_file_expires_at = expires_at.strftime("%Y-%m-%d %H:%M:%S")

    import_log.updated_at = now.strftime("%Y-%m-%d %H:%M:%S")
    db.commit()


def process_resume_import(
    db: Session,
    file: UploadFile,
    current_user: User,
) -> dict:
    """Run the complete resume import pipeline.

    Steps:
        1. Validate & save file
        2. Write ImportLog (pending)
        3. Parse text
        4. Rule-based extraction
        5. AI enhancement (placeholder)
        6. Create LeadDraft
        7. Update ImportLog (parsed/deleted)
        8. Handle temp file per retention policy

    Returns a dict with import_log_id, lead_draft_id, parse_status, and draft info.
    """
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # 1. Validate & save
    validate_file(file)
    temp_path, original_name, file_size = save_temp_file(file)
    ext = Path(original_name).suffix.lower().lstrip(".")

    # 2. Create ImportLog (pending)
    import_log = ImportLog(
        file_name=original_name,
        file_type=ext,
        file_size=file_size,
        temp_file_path=temp_path,
        parse_status="pending",
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(import_log)
    db.commit()
    db.refresh(import_log)

    extracted_text = ""
    parse_status = "parsed"
    parse_error = None
    error_code = None

    # 3. Parse text
    try:
        extracted_text = parse_resume_text(temp_path, ext)
    except ResumeParseError as e:
        logger.warning("Resume parsing failed: %s", e)
        parse_status = "failed"
        parse_error = e.message
        error_code = e.error_code
    except Exception as e:
        logger.exception("Resume parsing failed")
        parse_status = "failed"
        parse_error = str(e)
        error_code = "PARSE_FAILED"

    # 4. Rule-based extraction (even if parsing partially succeeded)
    extraction: dict = {}
    if extracted_text:
        extraction = extract_all(extracted_text)

    # 5. AI enhancement (placeholder)
    ai_result: dict = {}
    if extracted_text:
        ai_result = enhance_resume_extract(extracted_text)

    # 6. Create LeadDraft
    draft = LeadDraft(
        import_log_id=import_log.id,
        name=extraction.get("name"),
        phone=extraction.get("phone"),
        email=extraction.get("email"),
        education=extraction.get("education"),
        skills=extraction.get("skills"),
        ai_summary=ai_result.get("ai_summary"),
        ai_course_suggestion=ai_result.get("ai_course_suggestion"),
        raw_text_excerpt=extracted_text[:1000] if extracted_text else None,
        status="pending",
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    # 7. Update ImportLog
    import_log.parse_status = parse_status
    import_log.parse_error = parse_error
    import_log.error_code = error_code
    import_log.extracted_text_length = len(extracted_text) if extracted_text else 0
    import_log.llm_used = int(ai_result.get("llm_used", False))
    import_log.llm_provider = ai_result.get("llm_provider")
    import_log.updated_at = now
    db.commit()

    # 8. Handle temp file
    handle_temp_file_deletion(db, import_log)

    return {
        "import_log_id": import_log.id,
        "lead_draft_id": draft.id,
        "parse_status": import_log.parse_status,
        "draft": {
            "id": draft.id,
            "name": draft.name,
            "phone": draft.phone,
            "email": draft.email,
            "education": draft.education,
            "school": draft.school,
            "major": draft.major,
            "skills": draft.skills,
            "ai_summary": draft.ai_summary,
            "ai_course_suggestion": draft.ai_course_suggestion,
            "status": draft.status,
        },
    }
