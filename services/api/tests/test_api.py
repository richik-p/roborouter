import asyncio
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from roborouter_api.database import SessionLocal
from roborouter_api.db_models import WorkerCredentialRow
from roborouter_api.main import app
from roborouter_api.worker_credentials import create_worker_credential, revoke_worker_credential


def _evaluation_payload(seed: int) -> dict:
    return {
        "policy_id": "pi05-libero",
        "policy_revision": "lerobot-pi05-libero-finetuned",
        "environment_id": "vla-eval-libero-object",
        "environment_revision": "vla-eval-0.4.0-lerobot-0.6.0-libero-2a4566009395",
        "task_profile_id": "libero-object-pick-place",
        "task_revision": "2026-08-20.1",
        "seeds": [seed],
    }


def _capabilities(worker_id: str) -> dict:
    return {
        "worker_id": worker_id,
        "cuda": True,
        "gpu_name": "test",
        "vram_gb": 80,
        "adapters": ["vla_eval_lerobot"],
        "environments": ["vla-eval-libero-object"],
    }


async def _expire_credential(credential_id: str) -> None:
    async with SessionLocal() as session:
        row = await session.get(WorkerCredentialRow, credential_id)
        assert row is not None
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()


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
            headers={"Authorization": "Bearer rrw_test-credential.test-worker-secret"},
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
            headers={"Authorization": "Bearer rrw_test-credential.test-worker-secret"},
            json={
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
            headers={"Authorization": "Bearer rrw_test-credential.test-worker-secret"},
            json={
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
            headers={"Authorization": "Bearer rrw_test-credential.test-worker-secret"},
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
            headers={"Authorization": "Bearer rrw_test-credential.test-worker-secret"},
            json={"rollouts": [{**rollout_payload, "artifacts": [ungranted_artifact]}]},
        )
        assert rejected.status_code == 422

        completion_payload = {"rollouts": [rollout_payload]}
        completed = client.post(
            f"/private/workers/jobs/{created.json()['id']}/complete",
            headers={"Authorization": "Bearer rrw_test-credential.test-worker-secret"},
            json=completion_payload,
        )
        assert completed.status_code == 200
        assert completed.json()["state"] == "SUCCEEDED"

        repeated = client.post(
            f"/private/workers/jobs/{created.json()['id']}/complete",
            headers={"Authorization": "Bearer rrw_test-credential.test-worker-secret"},
            json=completion_payload,
        )
        assert repeated.status_code == 200
        assert repeated.json()["state"] == "SUCCEEDED"

        evaluation_rollouts = client.get(f"/v0/evaluations/{created.json()['id']}/rollouts")
        assert evaluation_rollouts.status_code == 200
        assert evaluation_rollouts.json()["items"][0]["id"] == rollout_payload["id"]

        filtered_rollouts = client.get(
            "/v0/rollouts",
            params={"policy_id": "pi05-libero", "environment_id": "vla-eval-libero-object"},
        )
        assert filtered_rollouts.status_code == 200
        assert all(item["policy_spec_id"] == "pi05-libero" for item in filtered_rollouts.json()["items"])


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
        malformed = client.post(
            "/private/workers/register",
            headers={"Authorization": "Bearer not-a-worker-token"},
            json=_capabilities("unauthorized"),
        )
        assert malformed.status_code == 401
        unknown = client.post(
            "/private/workers/register",
            headers={"Authorization": "Bearer rrw_unknown.unknown-secret"},
            json=_capabilities("unauthorized"),
        )
        assert unknown.status_code == 401


def test_worker_credentials_are_scoped_and_bound_to_claimed_jobs() -> None:
    other_token = "rrw_other-credential.other-secret"
    limited_token = "rrw_limited-credential.limited-secret"
    revoked_token = "rrw_revoked-credential.revoked-secret"
    expired_token = "rrw_expired-credential.expired-secret"
    with TestClient(app) as client:
        asyncio.run(
            create_worker_credential(
                "other-gpu",
                credential_id="other-credential",
                token=other_token,
            )
        )
        asyncio.run(
            create_worker_credential(
                "limited-gpu",
                credential_id="limited-credential",
                token=limited_token,
                scopes=["worker:register"],
            )
        )
        asyncio.run(
            create_worker_credential(
                "revoked-gpu",
                credential_id="revoked-credential",
                token=revoked_token,
            )
        )
        asyncio.run(revoke_worker_credential("revoked-credential"))
        asyncio.run(
            create_worker_credential(
                "expired-gpu",
                credential_id="expired-credential",
                token=expired_token,
                ttl_days=1,
            )
        )
        asyncio.run(_expire_credential("expired-credential"))

        created = client.post("/v0/evaluations", json=_evaluation_payload(19))
        assert created.status_code == 201
        claimed = client.post(
            "/private/workers/claim",
            headers={"Authorization": "Bearer rrw_test-credential.test-worker-secret"},
            json=_capabilities("test-gpu"),
        )
        assert claimed.status_code == 200
        assert claimed.json()["id"] == created.json()["id"]

        wrong_owner = client.post(
            f"/private/workers/jobs/{created.json()['id']}/heartbeat",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert wrong_owner.status_code == 409

        scope_denied = client.post(
            "/private/workers/claim",
            headers={"Authorization": f"Bearer {limited_token}"},
            json=_capabilities("limited-gpu"),
        )
        assert scope_denied.status_code == 403

        revoked = client.post(
            "/private/workers/register",
            headers={"Authorization": f"Bearer {revoked_token}"},
            json=_capabilities("revoked-gpu"),
        )
        assert revoked.status_code == 401

        expired = client.post(
            "/private/workers/register",
            headers={"Authorization": f"Bearer {expired_token}"},
            json=_capabilities("expired-gpu"),
        )
        assert expired.status_code == 401

        identity_mismatch = client.post(
            "/private/workers/register",
            headers={"Authorization": f"Bearer {other_token}"},
            json=_capabilities("somebody-else"),
        )
        assert identity_mismatch.status_code == 403


def test_revoking_a_credential_terminates_its_active_lease() -> None:
    token = "rrw_revocable-credential.revocable-secret"
    with TestClient(app) as client:
        asyncio.run(
            create_worker_credential(
                "revocable-gpu",
                credential_id="revocable-credential",
                token=token,
            )
        )
        created = client.post("/v0/evaluations", json=_evaluation_payload(23))
        assert created.status_code == 201
        claimed = client.post(
            "/private/workers/claim",
            headers={"Authorization": f"Bearer {token}"},
            json=_capabilities("revocable-gpu"),
        )
        assert claimed.status_code == 200
        assert claimed.json()["id"] == created.json()["id"]

        asyncio.run(revoke_worker_credential("revocable-credential"))
        terminated = client.get(f"/v0/evaluations/{created.json()['id']}")
        assert terminated.status_code == 200
        assert terminated.json()["state"] == "FAILED"
        assert terminated.json()["failure_detail"] == "worker credential revoked"

        rejected_heartbeat = client.post(
            f"/private/workers/jobs/{created.json()['id']}/heartbeat",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rejected_heartbeat.status_code == 401


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
