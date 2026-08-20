from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://roborouter:roborouter@localhost:5432/roborouter"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "roborouter"
    s3_secret_key: str = "roborouter-local-only"
    s3_bucket: str = "roborouter-artifacts"
    worker_token: str = "local-worker-token-change-me"
    worker_lease_seconds: int = 90
    auto_create_schema: bool = False
    catalog_root: Path = Path(__file__).resolve().parents[4] / "catalog"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
