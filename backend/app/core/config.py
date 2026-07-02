from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/jiuwei_crm.db"
    JWT_SECRET_KEY: str = "change-me"
    UPLOAD_DIR: str = "./uploads/temp"
    TEMP_FILE_RETENTION_DAYS: int = 0
    CORS_ORIGINS: str = "http://localhost:3000"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
