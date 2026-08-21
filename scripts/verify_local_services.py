from __future__ import annotations

import hashlib
import os

import httpx
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://roborouter:roborouter@localhost:5432/roborouter")
os.environ.setdefault("S3_ENDPOINT_URL", "http://localhost:9000")
os.environ.setdefault("S3_ACCESS_KEY", "roborouter")
os.environ.setdefault("S3_SECRET_KEY", "roborouter-local-only")
os.environ.setdefault("S3_BUCKET", "roborouter-artifacts")
os.environ.setdefault("S3_VERIFY_UPLOADS", "true")
os.environ.setdefault("WORKER_BOOTSTRAP_TOKEN", "rrw_local-integration.local-integration-worker-token")
os.environ.setdefault("WORKER_BOOTSTRAP_ID", "local-integration")
os.environ.setdefault("AUTO_CREATE_SCHEMA", "false")

from roborouter_api.main import app  # noqa: E402


def require_ok(response: httpx.Response) -> dict:
    response.raise_for_status()
    return response.json()


def main() -> None:
    token = os.environ["WORKER_BOOTSTRAP_TOKEN"]
    headers = {"Authorization": f"Bearer {token}"}
    worker_id = os.environ["WORKER_BOOTSTRAP_ID"]
    content = b"RoboRouter PostgreSQL + MinIO integration artifact\n"
    digest = hashlib.sha256(content).hexdigest()

    with TestClient(app) as client:
        created = require_ok(
            client.post(
                "/v0/evaluations",
                json={
                    "policy_id": "pi05-libero",
                    "policy_revision": "lerobot-pi05-libero-finetuned",
                    "environment_id": "vla-eval-libero-object",
                    "environment_revision": "vla-eval-0.4.0-lerobot-0.6.0-libero-2a4566009395",
                    "task_profile_id": "libero-object-pick-place",
                    "task_revision": "2026-08-20.1",
                    "seeds": [7],
                },
            )
        )
        capabilities = {
            "worker_id": worker_id,
            "cuda": True,
            "gpu_name": "integration-fixture",
            "vram_gb": 80,
            "adapters": ["vla_eval_lerobot"],
            "environments": ["vla-eval-libero-object"],
        }
        require_ok(client.post("/private/workers/register", headers=headers, json=capabilities))
        claimed = require_ok(client.post("/private/workers/claim", headers=headers, json=capabilities))
        if claimed["id"] != created["id"]:
            raise RuntimeError("worker claimed a different evaluation")
        require_ok(
            client.post(
                f"/private/workers/jobs/{created['id']}/heartbeat",
                headers=headers,
            )
        )
        grant = require_ok(
            client.post(
                f"/private/workers/jobs/{created['id']}/artifacts/presign",
                headers=headers,
                json={
                    "kind": "log",
                    "filename": "integration.log",
                    "media_type": "text/plain",
                    "sha256": digest,
                    "size_bytes": len(content),
                },
            )
        )
        uploaded = httpx.put(
            grant["upload_url"],
            content=content,
            headers=grant["required_headers"],
            timeout=30,
        )
        uploaded.raise_for_status()

        fixture = require_ok(client.get("/v0/rollouts/rollout-upstream-pi05-libero-object"))
        fixture.update(
            {
                "id": f"rollout-{created['id']}",
                "evaluation_job_id": created["id"],
                "artifacts": [grant["artifact"]],
                "evidence_note": "Executed by the local PostgreSQL and MinIO integration verifier.",
            }
        )
        completion = {"rollouts": [fixture]}
        completed = require_ok(
            client.post(
                f"/private/workers/jobs/{created['id']}/complete",
                headers=headers,
                json=completion,
            )
        )
        if completed["state"] != "SUCCEEDED":
            raise RuntimeError("evaluation did not succeed")
        replayed = require_ok(
            client.post(
                f"/private/workers/jobs/{created['id']}/complete",
                headers=headers,
                json=completion,
            )
        )
        if replayed["state"] != "SUCCEEDED":
            raise RuntimeError("idempotent completion replay failed")
        saved = require_ok(client.get(f"/v0/rollouts/{fixture['id']}"))
        if saved["artifacts"] != [grant["artifact"]]:
            raise RuntimeError("saved Rollout artifact identity changed")

    print(f"Verified PostgreSQL, MinIO upload integrity, and idempotent completion for {created['id']}.")


if __name__ == "__main__":
    main()
