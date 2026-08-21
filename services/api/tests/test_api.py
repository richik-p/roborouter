from fastapi.testclient import TestClient
from roborouter_api.main import app


def test_catalog_compatibility_rollout_and_job_flow() -> None:
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200

        policies = client.get("/v0/policies").json()
        assert policies["total"] >= 20

        compatibility = client.post(
            "/v0/compatibility/queries",
            json={
                "robot_profile_id": "sim-libero-panda",
                "robot_revision": "2026-08-20.1",
                "task_profile_id": "libero-object-pick-place",
                "task_revision": "2026-08-20.1",
                "policy_ids": ["pi05-libero"],
            },
        )
        assert compatibility.status_code == 200
        assert compatibility.json()[0]["status"] == "SIM_VERIFIED"

        rollout = client.get("/v0/rollouts/rollout-upstream-pi05-libero-object")
        assert rollout.status_code == 200
        assert "not a RoboRouter-executed episode" in rollout.json()["evidence_note"]

        created = client.post(
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
        assert created.status_code == 201
        assert created.json()["state"] == "QUEUED"

        claim = client.post(
            "/private/workers/claim",
            headers={"Authorization": "Bearer test-worker-token"},
            json={
                "worker_id": "test-gpu",
                "cuda": True,
                "gpu_name": "test",
                "vram_gb": 80,
                "adapters": ["vla_eval_lerobot"],
                "environments": ["vla-eval-libero-object"],
            },
        )
        assert claim.status_code == 200
        assert claim.json()["id"] == created.json()["id"]

        grant = client.post(
            f"/private/workers/jobs/{created.json()['id']}/artifacts/presign",
            headers={"Authorization": "Bearer test-worker-token"},
            json={
                "worker_id": "test-gpu",
                "kind": "log",
                "filename": "result.log",
                "media_type": "text/plain",
                "sha256": "a" * 64,
                "size_bytes": 12,
            },
        )
        assert grant.status_code == 200
        assert grant.json()["artifact"]["uri"].startswith("s3://roborouter-artifacts/jobs/")
        assert grant.json()["upload_url"].startswith("https://artifacts.example.test/")
        assert "X-Amz-Signature" in grant.json()["upload_url"]
        assert grant.json()["required_headers"]["x-amz-meta-sha256"] == "a" * 64

        repeated_grant = client.post(
            f"/private/workers/jobs/{created.json()['id']}/artifacts/presign",
            headers={"Authorization": "Bearer test-worker-token"},
            json={
                "worker_id": "test-gpu",
                "kind": "log",
                "filename": "result.log",
                "media_type": "text/plain",
                "sha256": "a" * 64,
                "size_bytes": 12,
            },
        )
        assert repeated_grant.status_code == 200
        assert repeated_grant.json()["artifact"] == grant.json()["artifact"]

        heartbeat = client.post(
            f"/private/workers/jobs/{created.json()['id']}/heartbeat",
            headers={"Authorization": "Bearer test-worker-token"},
            params={"worker_id": "test-gpu"},
        )
        assert heartbeat.status_code == 200
        assert heartbeat.json()["state"] == "RUNNING"

        rollout_payload = rollout.json()
        rollout_payload.update(
            {
                "id": f"rollout-{created.json()['id']}",
                "evaluation_job_id": created.json()["id"],
                "artifacts": [grant.json()["artifact"]],
                "evidence_note": "Executed by the test evaluation worker.",
            }
        )
        ungranted_artifact = {**grant.json()["artifact"], "id": "artifact-not-granted"}
        rejected = client.post(
            f"/private/workers/jobs/{created.json()['id']}/complete",
            headers={"Authorization": "Bearer test-worker-token"},
            json={"worker_id": "test-gpu", "rollouts": [{**rollout_payload, "artifacts": [ungranted_artifact]}]},
        )
        assert rejected.status_code == 422

        completion_payload = {"worker_id": "test-gpu", "rollouts": [rollout_payload]}
        completed = client.post(
            f"/private/workers/jobs/{created.json()['id']}/complete",
            headers={"Authorization": "Bearer test-worker-token"},
            json=completion_payload,
        )
        assert completed.status_code == 200
        assert completed.json()["state"] == "SUCCEEDED"

        repeated = client.post(
            f"/private/workers/jobs/{created.json()['id']}/complete",
            headers={"Authorization": "Bearer test-worker-token"},
            json=completion_payload,
        )
        assert repeated.status_code == 200
        assert repeated.json()["state"] == "SUCCEEDED"


def test_worker_token_is_required() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/private/workers/register",
            json={
                "worker_id": "unauthorized",
                "cuda": False,
                "adapters": [],
                "environments": [],
            },
        )
        assert response.status_code == 401


def test_queued_evaluation_can_be_canceled() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/v0/evaluations",
            json={
                "policy_id": "pi05-libero",
                "policy_revision": "lerobot-pi05-libero-finetuned",
                "environment_id": "vla-eval-libero-object",
                "environment_revision": "vla-eval-0.4.0-lerobot-0.6.0-libero-2a4566009395",
                "task_profile_id": "libero-object-pick-place",
                "task_revision": "2026-08-20.1",
                "seeds": [11],
            },
        )
        assert created.status_code == 201

        canceled = client.post(f"/v0/evaluations/{created.json()['id']}/cancel")
        assert canceled.status_code == 200
        assert canceled.json()["state"] == "CANCELED"

        fetched = client.get(f"/v0/evaluations/{created.json()['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["state"] == "CANCELED"
