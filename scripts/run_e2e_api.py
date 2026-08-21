from __future__ import annotations

import os
from pathlib import Path

import uvicorn


def main() -> None:
    database = Path(os.environ.get("ROBOROUTER_E2E_DATABASE", "/tmp/roborouter-e2e.sqlite3"))
    database.unlink(missing_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{database}"
    os.environ["AUTO_CREATE_SCHEMA"] = "true"
    os.environ["S3_VERIFY_UPLOADS"] = "false"
    os.environ["S3_PUBLIC_ENDPOINT_URL"] = "https://artifacts.example.test"
    os.environ["WORKER_BOOTSTRAP_TOKEN"] = "rrw_e2e-worker.e2e-only-secret"
    os.environ["WORKER_BOOTSTRAP_ID"] = "e2e-worker"
    os.environ["CORS_ORIGINS"] = '["http://127.0.0.1:3100"]'
    uvicorn.run("roborouter_api.main:app", app_dir="services/api/src", host="127.0.0.1", port=8100)


if __name__ == "__main__":
    main()
