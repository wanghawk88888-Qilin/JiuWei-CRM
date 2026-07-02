"""Resume import router — handles file upload and resume parsing."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.services import resume_import_service

router = APIRouter(prefix="/api/v1/resume-imports", tags=["resume-imports"])


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
        import logging
        logging.getLogger(__name__).exception("Unexpected error in resume import")
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
