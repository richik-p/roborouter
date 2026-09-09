from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://roborouter:roborouter@localhost:5432/roborouter"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_public_endpoint_url: str | None = None
    s3_access_key: str = "roborouter"
    s3_secret_key: str = "roborouter-local-only"
    s3_bucket: str = "roborouter-artifacts"
    s3_verify_uploads: bool = True
    worker_bootstrap_token: str | None = None
    worker_bootstrap_id: str = "local-worker"
    worker_lease_seconds: int = 90
    auto_create_schema: bool = False
    catalog_root: Path = Path(__file__).resolve().parents[4] / "catalog"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Evaluation launches are closed by default: a launch key (rrl_...) is required to
    # queue or cancel jobs. "open" keeps the pre-beta behavior for local exploration.
    evaluation_access: Literal["key", "open"] = "key"
    launch_bootstrap_token: str | None = None
    launch_bootstrap_role: Literal["user", "operator"] = "operator"
    launch_default_concurrent_limit: int = 1
    launch_default_daily_limit: int = 5
    # Spend guards that apply to every launch, operators included.
    max_active_evaluations: int = 4
    max_seeds_per_evaluation: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
