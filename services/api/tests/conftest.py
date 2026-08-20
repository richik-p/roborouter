from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path("/tmp/roborouter-api-test.sqlite3")
TEST_DB.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB}"
os.environ["WORKER_TOKEN"] = "test-worker-token"
os.environ["AUTO_CREATE_SCHEMA"] = "true"
