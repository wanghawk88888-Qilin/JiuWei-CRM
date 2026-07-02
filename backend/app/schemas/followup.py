from pydantic import BaseModel


# -- Constants ---------------------------------------------------------------

VALID_FOLLOWUP_TYPES = {"phone", "wechat", "offline", "other"}
VALID_INTENTION_LEVELS = {"low", "medium", "high"}


# -- Create ------------------------------------------------------------------

class FollowUpCreate(BaseModel):
    followup_type: str
    content: str
    intention_level: str | None = None
    next_followup_at: str | None = None


# -- Response ----------------------------------------------------------------

class FollowUpResponse(BaseModel):
    id: int
    lead_id: int
    followup_type: str
    content: str
    intention_level: str | None = None
    next_followup_at: str | None = None
    created_by: int
    created_by_name: str = "未知用户"
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class FollowUpListResponse(BaseModel):
    items: list[FollowUpResponse]
    total: int
