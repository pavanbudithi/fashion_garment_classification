from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_root: Path = Path(__file__).resolve().parents[2]
    database_url: str = "sqlite:///./data/fash_garm.db"
    upload_dir: Path = Path("./data/uploads")
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"

    def resolved_upload_dir(self) -> Path:
        p = self.upload_dir
        if not p.is_absolute():
            p = (self.project_root / p).resolve()
        return p

    def resolved_database_url(self) -> str:
        if self.database_url.startswith("sqlite:///./"):
            rel = self.database_url.removeprefix("sqlite:///./")
            abs_path = (self.project_root / rel).resolve()
            return f"sqlite:///{abs_path.as_posix()}"
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
