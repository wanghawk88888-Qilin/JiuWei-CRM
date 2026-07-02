from pydantic import BaseModel, Field


# -- Status and intention level constants ---------------------------------

VALID_LEAD_STATUSES = {"new", "consulted", "following", "high_intent", "enrolled", "invalid"}
VALID_INTENTION_LEVELS = {"low", "medium", "high"}


# -- Create ----------------------------------------------------------------

class LeadCreate(BaseModel):
    name: str
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
    status: str = "new"
    intention_level: str | None = None
    owner_id: int | None = None
    remark: str | None = None
    ai_summary: str | None = None
    ai_course_suggestion: str | None = None
    tags: str | None = None


# -- Update ----------------------------------------------------------------

class LeadUpdate(BaseModel):
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
    status: str | None = None
    intention_level: str | None = None
    owner_id: int | None = None
    remark: str | None = None
    ai_summary: str | None = None
    ai_course_suggestion: str | None = None
    tags: str | None = None


# -- Response --------------------------------------------------------------

class LeadResponse(BaseModel):
    id: int
    name: str
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
    status: str
    intention_level: str | None = None
    owner_id: int | None = None
    remark: str | None = None
    ai_summary: str | None = None
    ai_course_suggestion: str | None = None
    tags: str | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class LeadListItem(BaseModel):
    """Lightweight schema for list endpoint — excludes detail-only fields."""

    id: int
    name: str
    phone: str | None = None
    wechat: str | None = None
    source_id: int | None = None
    intended_course_id: int | None = None
    status: str
    intention_level: str | None = None
    owner_id: int | None = None
    last_followup_by: int | None = None
    last_followup_by_name: str | None = None
    last_followup_at: str | None = None
    next_followup_at: str | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    items: list[LeadListItem]
    total: int
    page: int
    page_size: int
