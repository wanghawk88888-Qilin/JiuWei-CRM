from pydantic import BaseModel


class ResumeImportResponse(BaseModel):
    import_log_id: int
    lead_draft_id: int
    parse_status: str
    draft: dict | None = None

    model_config = {"from_attributes": True}
