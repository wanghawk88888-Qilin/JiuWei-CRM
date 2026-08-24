from pydantic import BaseModel


class ResumeImportResponse(BaseModel):
    import_log_id: int
    lead_draft_id: int
    parse_status: str
    draft: dict | None = None

    model_config = {"from_attributes": True}


class LeadDraftResponse(BaseModel):
    id: int
    import_log_id: int | None = None
    batch_id: int | None = None
    name: str | None = None
    phone: str | None = None
    wechat: str | None = None
    email: str | None = None
    gender: str | None = None
    age: int | None = None
    education: str | None = None
    school: str | None = None
    major: str | None = None
    graduation_time: str | None = None
    city: str | None = None
    work_years: str | None = None
    latest_company: str | None = None
    latest_position: str | None = None
    skills: str | None = None
    ai_summary: str | None = None
    ai_course_suggestion: str | None = None
    raw_text_excerpt: str | None = None
    status: str
    confirmed_lead_id: int | None = None
    name_confidence: str | None = None
    phone_confidence: str | None = None
    conflict_flags: str | None = None
    duplicate_lead_id: int | None = None
    created_by: int | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class LeadDraftUpdateRequest(BaseModel):
    """Human review correction. Only the fields sent are applied."""

    name: str | None = None
    phone: str | None = None
    wechat: str | None = None
    email: str | None = None
    gender: str | None = None
    age: int | None = None
    education: str | None = None
    school: str | None = None
    major: str | None = None
    graduation_time: str | None = None
    city: str | None = None
    work_years: str | None = None
    latest_company: str | None = None
    latest_position: str | None = None
    skills: str | None = None


class LeadDraftConfirmRequest(BaseModel):
    name: str | None = None
    phone: str | None = None
    wechat: str | None = None
    email: str | None = None
    gender: str | None = None
    age: int | None = None
    education: str | None = None
    school: str | None = None
    major: str | None = None
    city: str | None = None
    current_job: str | None = None
    work_years: str | None = None
    latest_company: str | None = None
    latest_position: str | None = None
    intended_course_id: int | None = None
    source_id: int | None = None
    owner_id: int | None = None
    remark: str | None = None
