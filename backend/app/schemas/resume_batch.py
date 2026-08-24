from pydantic import BaseModel


class BatchConfirmRequest(BaseModel):
    """Optional defaults applied to every Lead created by a batch confirm."""

    source_id: int | None = None
    owner_id: int | None = None
    remark: str | None = None
    # NOTE: intended_course_id is intentionally absent. v0.2.1 never sets a
    # course from rules; that is reserved for the future AI Course Suggestion.


class BatchUploadResponse(BaseModel):
    batch_id: int
    batch_no: str
    total: int
    status: str


class BatchSummary(BaseModel):
    id: int
    batch_no: str
    status: str
    total_files: int
    parsed_count: int
    ready_count: int
    needs_review_count: int
    duplicate_count: int
    failed_count: int
    confirmed_count: int
    created_by: int | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class BatchItem(BaseModel):
    import_log_id: int
    file_name: str
    file_type: str | None = None
    file_size: int | None = None
    parse_status: str
    error_code: str | None = None
    error_message: str | None = None
    lead_draft_id: int | None = None
    status: str
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    education: str | None = None
    school: str | None = None
    major: str | None = None
    name_confidence: str | None = None
    phone_confidence: str | None = None
    conflicts: dict = {}
    duplicate: dict | None = None
    confirmed_lead_id: int | None = None


class BatchDetailResponse(BaseModel):
    batch: BatchSummary
    items: list[BatchItem]
