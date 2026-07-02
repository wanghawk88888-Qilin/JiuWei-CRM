import datetime

from sqlalchemy.orm import Session

from app.models.lead_source import LeadSource
from app.models.course import Course
from app.models.system_setting import SystemSetting


def list_lead_sources(db: Session) -> list[LeadSource]:
    """Return all active lead sources."""
    return db.query(LeadSource).filter(LeadSource.is_active == 1).order_by(LeadSource.id).all()


def list_courses(db: Session) -> list[Course]:
    """Return all active courses."""
    return db.query(Course).filter(Course.is_active == 1).order_by(Course.id).all()


def list_system_settings(db: Session) -> list[SystemSetting]:
    """Return all system settings (admin only)."""
    return db.query(SystemSetting).order_by(SystemSetting.id).all()


def init_default_configs(db: Session) -> None:
    """Initialize default configuration data if tables are empty.

    This function is idempotent — it only inserts when the target table is empty,
    so it can be called on every app startup without duplicating data.
    """

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # -- Lead Sources ---------------------------------------------------------

    if db.query(LeadSource).count() == 0:
        default_sources = [
            LeadSource(name="手工录入", description="手动创建线索", is_active=1, created_at=now, updated_at=now),
            LeadSource(name="简历上传", description="简历文件导入", is_active=1, created_at=now, updated_at=now),
            LeadSource(name="微信", description="微信渠道", is_active=1, created_at=now, updated_at=now),
            LeadSource(name="官网", description="官方网站", is_active=1, created_at=now, updated_at=now),
            LeadSource(name="其他", description="其他渠道", is_active=1, created_at=now, updated_at=now),
        ]
        db.add_all(default_sources)
        db.commit()

    # -- Courses --------------------------------------------------------------

    if db.query(Course).count() == 0:
        default_courses = [
            Course(name="AI智能应用开发工程师", description="AI智能应用开发方向", is_active=1, created_at=now, updated_at=now),
            Course(name="AI测试开发工程师", description="AI测试开发方向", is_active=1, created_at=now, updated_at=now),
            Course(name="待确认", description="待确认课程方向", is_active=1, created_at=now, updated_at=now),
        ]
        db.add_all(default_courses)
        db.commit()

    # -- System Settings ------------------------------------------------------

    if db.query(SystemSetting).count() == 0:
        default_settings = [
            SystemSetting(
                setting_key="resume_temp_retention_enabled",
                setting_value="false",
                description="是否启用简历临时文件保留",
                created_at=now,
                updated_at=now,
            ),
            SystemSetting(
                setting_key="resume_temp_retention_days",
                setting_value="0",
                description="简历临时文件保留天数",
                created_at=now,
                updated_at=now,
            ),
            SystemSetting(
                setting_key="default_llm_enabled",
                setting_value="false",
                description="是否启用默认LLM",
                created_at=now,
                updated_at=now,
            ),
        ]
        db.add_all(default_settings)
        db.commit()
