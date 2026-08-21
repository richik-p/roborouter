from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path("/tmp/roborouter-api-test.sqlite3")
TEST_DB.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB}"
os.environ["WORKER_BOOTSTRAP_TOKEN"] = "rrw_test-credential.test-worker-secret"
os.environ["WORKER_BOOTSTRAP_ID"] = "test-gpu"
os.environ["AUTO_CREATE_SCHEMA"] = "true"
os.environ["S3_VERIFY_UPLOADS"] = "false"
os.environ["S3_PUBLIC_ENDPOINT_URL"] = "https://artifacts.example.test"
