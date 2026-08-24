import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LeadDraft(Base):
    __tablename__ = "lead_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_log_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # v0.2.1: NULL for single-file imports, set for batch imports.
    batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    wechat: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    education: Mapped[str | None] = mapped_column(String(100), nullable=True)
    school: Mapped[str | None] = mapped_column(String(255), nullable=True)
    major: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graduation_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    work_years: Mapped[str | None] = mapped_column(String(50), nullable=True)
    latest_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latest_position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_course_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    confirmed_lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # v0.2.1 confidence / conflict metadata. high | medium | low | missing.
    # Only `high` on BOTH name and phone makes a draft auto-confirmable.
    name_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # JSON blob: {"name": {"code": "NAME_CONFLICT", "candidates": [...]}, ...}
    conflict_flags: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Set when this draft's phone already belongs to an existing Lead.
    duplicate_lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(
        String(50), nullable=False, default=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    updated_at: Mapped[str] = mapped_column(
        String(50), nullable=False, default=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
