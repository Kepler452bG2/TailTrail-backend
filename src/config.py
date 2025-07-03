from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    database_url: Optional[str] = None
    secret_key: str
    jwt_expiration: int
    echo_sql: bool = True
    debug_logs: bool = True
    db_host: str
    db_port: int
    db_user: str
    db_pass: str
    db_name: str

    @model_validator(mode="after")
    def fill_database_url(self):
        if not self.database_url:
            self.database_url = (
                f"postgresql+asyncpg://{self.db_user}:{self.db_pass}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
