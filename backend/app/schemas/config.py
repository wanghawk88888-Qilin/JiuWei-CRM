from pydantic import BaseModel


class LeadSourceResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_active: int

    model_config = {"from_attributes": True}


class CourseResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_active: int

    model_config = {"from_attributes": True}


class SystemSettingResponse(BaseModel):
    id: int
    setting_key: str
    setting_value: str
    description: str | None = None

    model_config = {"from_attributes": True}
