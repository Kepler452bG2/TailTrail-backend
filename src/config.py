from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    DATABASE_URL: Optional[str] = None
    SECRET_KEY: str
    JWT_EXPIRATION: int
    ECHO_SQL: bool = True
    DEBUG_LOGS: bool = True
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET_NAME: str = "tail-trail-bucket"
    AWS_REGION: str = "us-east-1"
    AWS_CLOUDFRONT_URL: Optional[str] = None

    GEMINI_API_KEY: Optional[str] = None

    COMPLAINT_SERVICE_URL: Optional[str] = None
    
    @model_validator(mode="after")
    def fill_database_url(self):
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
