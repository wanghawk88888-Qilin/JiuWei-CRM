from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/jiuwei_crm.db"
    JWT_SECRET_KEY: str = "change-me"
    UPLOAD_DIR: str = "./uploads/temp"
    TEMP_FILE_RETENTION_DAYS: int = 0
    CORS_ORIGINS: str = "http://localhost:3000"

    # v0.2.1 — Resume batch import limits
    RESUME_MAX_FILE_SIZE_MB: int = 10
    RESUME_BATCH_MAX_FILES: int = 50

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
