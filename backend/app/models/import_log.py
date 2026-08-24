import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ImportLog(Base):
    __tablename__ = "import_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # v0.2.1: NULL for single-file imports, set for batch imports.
    batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temp_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parse_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # v0.2.1: stable machine-readable reason, e.g. PDF_NO_EXTRACTABLE_TEXT.
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extracted_text_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    temp_file_expires_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_deleted_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(
        String(50), nullable=False, default=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    updated_at: Mapped[str] = mapped_column(
        String(50), nullable=False, default=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
