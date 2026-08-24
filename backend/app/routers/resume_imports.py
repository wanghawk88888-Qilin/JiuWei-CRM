"""Resume import router — single-file upload and v0.2.1 batch import."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.resume_batch import BatchConfirmRequest
from app.services import resume_batch_service, resume_import_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/resume-imports", tags=["resume-imports"])


# ---------------------------------------------------------------------------
# Single resume (v0.1 — unchanged behaviour)
# ---------------------------------------------------------------------------

@router.post("")
def upload_and_parse_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a .docx or .pdf resume, parse it, and create a LeadDraft.

    Supported file types: .docx, .pdf
    Max file size: 10 MB
    """
    try:
        result = resume_import_service.process_resume_import(
            db, file, current_user
        )
    except ValueError as e:
        error_str = str(e)
        if "|" in error_str:
            error_code, message = error_str.split("|", 1)
        else:
            error_code, message = "INTERNAL_ERROR", error_str
        return {
            "success": False,
            "error_code": error_code,
            "message": message,
        }
    except Exception:
        logger.exception("Unexpected error in resume import")
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "简历导入处理失败",
        }

    return {
        "success": True,
        "data": result,
        "message": "简历解析完成",
    }


# ---------------------------------------------------------------------------
# Batch import (v0.2.1)
# ---------------------------------------------------------------------------

@router.post("/batch")
def upload_resume_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload up to RESUME_BATCH_MAX_FILES resumes at once.

    Files are persisted synchronously so the response is immediate, then parsed
    in a lightweight background task. Poll ``GET /batches/{batch_id}`` for
    progress — the batch leaves ``processing`` once every file is done.

    A rejected file (wrong type, oversized, corrupt) never fails the batch; it
    is recorded with its own error code and the other files carry on.
    """
    try:
        batch = resume_batch_service.create_batch(db, files, current_user)
    except resume_batch_service.BatchValidationError as e:
        return {
            "success": False,
            "error_code": e.error_code,
            "message": e.message,
        }
    except Exception:
        logger.exception("Unexpected error creating resume batch")
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "批量上传失败",
        }

    background_tasks.add_task(resume_batch_service.process_batch_files, batch.id)

    return {
        "success": True,
        "data": {
            "batch_id": batch.id,
            "batch_no": batch.batch_no,
            "total": batch.total_files,
            "status": batch.status,
        },
        "message": "批量上传成功，正在解析",
    }


@router.get("/batches")
def list_resume_batches(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List recent batches visible to the current user."""
    limit = max(1, min(limit, 100))
    return {
        "success": True,
        "data": resume_batch_service.list_batches(db, current_user, limit),
        "message": "ok",
    }


@router.get("/batches/{batch_id}")
def get_resume_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch summary plus the per-file parse result."""
    batch = resume_batch_service.get_batch(db, batch_id)
    if batch is None:
        return {
            "success": False,
            "error_code": "BATCH_NOT_FOUND",
            "message": "批次不存在",
        }
    if not resume_batch_service.check_batch_access(batch, current_user):
        return {
            "success": False,
            "error_code": "FORBIDDEN",
            "message": "无权限访问该批次",
        }

    return {
        "success": True,
        "data": resume_batch_service.build_batch_detail(db, batch),
        "message": "ok",
    }


@router.post("/batches/{batch_id}/confirm")
def confirm_resume_batch(
    batch_id: int,
    body: BatchConfirmRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Lead for every `ready` draft in the batch.

    Idempotent: clicking twice never produces a second Lead. Drafts that are
    duplicates, failures, or still awaiting review are skipped and reported.
    """
    batch = resume_batch_service.get_batch(db, batch_id)
    if batch is None:
        return {
            "success": False,
            "error_code": "BATCH_NOT_FOUND",
            "message": "批次不存在",
        }
    if not resume_batch_service.check_batch_access(batch, current_user):
        return {
            "success": False,
            "error_code": "FORBIDDEN",
            "message": "无权限操作该批次",
        }
    if batch.status == resume_batch_service.BATCH_PROCESSING:
        return {
            "success": False,
            "error_code": "BATCH_STILL_PROCESSING",
            "message": "批次仍在解析中，请稍后再试",
        }

    defaults = body.model_dump(exclude_none=True) if body else {}
    try:
        result = resume_batch_service.confirm_batch(db, batch, current_user, defaults)
    except Exception:
        logger.exception("Unexpected error confirming batch %s", batch_id)
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "批量确认失败",
        }

    return {
        "success": True,
        "data": result,
        "message": f"已生成 {result['confirmed_count']} 条正式线索",
    }


@router.get("/batch-limits")
def get_batch_limits(current_user: User = Depends(get_current_user)):
    """Upload limits, so the UI can validate before sending anything."""
    return {
        "success": True,
        "data": {
            "max_files": settings.RESUME_BATCH_MAX_FILES,
            "max_file_size_mb": settings.RESUME_MAX_FILE_SIZE_MB,
            "allowed_extensions": sorted(resume_import_service.ALLOWED_EXTENSIONS),
        },
        "message": "ok",
    }
