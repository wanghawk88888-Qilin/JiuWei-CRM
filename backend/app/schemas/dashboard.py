from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    total_leads: int
    today_new_leads: int
    pending_followups: int
    enrolled_leads: int


class TodayFollowUpItem(BaseModel):
    lead_id: int
    lead_name: str
    phone: str | None = None
    status: str
    intention_level: str | None = None
    next_followup_at: str | None = None
    owner_id: int | None = None
    intended_course_name: str | None = None
    latest_followup_content: str | None = None
    followup_priority: str = "today"  # "overdue" | "today" | "upcoming"

    model_config = {"from_attributes": True}


class RecentLeadItem(BaseModel):
    id: int
    name: str
    phone: str | None = None
    status: str
    intention_level: str | None = None
    owner_id: int | None = None
    created_at: str

    model_config = {"from_attributes": True}
