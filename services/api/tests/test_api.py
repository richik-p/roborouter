import asyncio
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from roborouter_api import main as api_main
from roborouter_api.database import SessionLocal
from roborouter_api.db_models import EvaluationJobRow, PolicyRow, WorkerCredentialRow
from roborouter_api.launch_credentials import create_launch_credential, revoke_launch_credential
from roborouter_api.main import app
from roborouter_api.worker_credentials import (
    create_worker_credential,
    revoke_worker_credential,
    rotate_worker_credential,
)
from sqlalchemy import func, select

LAUNCH_HEADERS = {"Authorization": "Bearer rrl_test-launch.test-launch-secret"}


def _launch_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


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

        created = client.post("/v0/evaluations", headers=LAUNCH_HEADERS,
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

        created = client.post("/v0/evaluations", headers=LAUNCH_HEADERS, json=_evaluation_payload(19))
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
        created = client.post("/v0/evaluations", headers=LAUNCH_HEADERS, json=_evaluation_payload(23))
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


def test_rotation_allows_a_bounded_overlap_without_transferring_the_lease() -> None:
    old_token = "rrw_rotation-old.old-secret"
    with TestClient(app) as client:
        asyncio.run(
            create_worker_credential(
                "rotation-gpu",
                credential_id="rotation-old",
                token=old_token,
            )
        )
        created = client.post("/v0/evaluations", headers=LAUNCH_HEADERS, json=_evaluation_payload(29))
        claimed = client.post(
            "/private/workers/claim",
            headers={"Authorization": f"Bearer {old_token}"},
            json=_capabilities("rotation-gpu"),
        )
        assert claimed.status_code == 200
        assert claimed.json()["id"] == created.json()["id"]

        old, new, new_token = asyncio.run(
            rotate_worker_credential(
                "rotation-old",
                overlap_minutes=5,
                ttl_days=30,
                label="rotation-new",
            )
        )
        assert old.expires_at is not None
        assert old.expires_at <= datetime.now(UTC) + timedelta(minutes=5)
        assert new.worker_id == "rotation-gpu"

        old_still_owns_lease = client.post(
            f"/private/workers/jobs/{created.json()['id']}/heartbeat",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert old_still_owns_lease.status_code == 200

        new_cannot_take_over = client.post(
            f"/private/workers/jobs/{created.json()['id']}/heartbeat",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        assert new_cannot_take_over.status_code == 409


def test_queued_evaluation_can_be_canceled() -> None:
    with TestClient(app) as client:
        created = client.post("/v0/evaluations", headers=LAUNCH_HEADERS,
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

        canceled = client.post(f"/v0/evaluations/{created.json()['id']}/cancel", headers=LAUNCH_HEADERS)
        assert canceled.status_code == 200
        assert canceled.json()["state"] == "CANCELED"

        fetched = client.get(f"/v0/evaluations/{created.json()['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["state"] == "CANCELED"


async def _insert_policy_revision(policy_id: str, revision: str, name: str) -> int:
    async with SessionLocal() as session:
        current = await session.scalar(
            select(PolicyRow).where(PolicyRow.policy_id == policy_id).order_by(PolicyRow.pk.desc())
        )
        assert current is not None
        row = PolicyRow(
            policy_id=policy_id,
            revision=revision,
            name=name,
            family=current.family,
            robot_classes=current.robot_classes,
            task_families=current.task_families,
            runtime_adapter=current.runtime_adapter,
            evidence_level=current.evidence_level,
            spec={**current.spec, "revision": revision, "name": name},
        )
        session.add(row)
        await session.commit()
        return row.pk


async def _delete_policy_row(pk: int) -> None:
    async with SessionLocal() as session:
        row = await session.get(PolicyRow, pk)
        if row is not None:
            await session.delete(row)
            await session.commit()


def test_catalog_reads_resolve_to_the_newest_policy_revision() -> None:
    with TestClient(app) as client:
        before = client.get("/v0/policies").json()
        pk = asyncio.run(_insert_policy_revision("openvla", "research-test-newer", "OpenVLA (newer revision)"))
        try:
            listed = client.get("/v0/policies").json()
            assert listed["total"] == before["total"]
            assert [item["revision"] for item in listed["items"] if item["id"] == "openvla"] == ["research-test-newer"]
            assert client.get("/v0/policies/openvla").json()["revision"] == "research-test-newer"

            records = client.post(
                "/v0/compatibility/queries",
                json={
                    "robot_profile_id": "sim-libero-panda",
                    "robot_revision": "2026-08-20.1",
                    "task_profile_id": "libero-object-pick-place",
                    "task_revision": "2026-08-20.1",
                    "policy_ids": ["openvla"],
                },
            ).json()
            assert [record["policy_revision"] for record in records] == ["research-test-newer"]
        finally:
            asyncio.run(_delete_policy_row(pk))


async def _count_active_jobs() -> int:
    async with SessionLocal() as session:
        statement = (
            select(func.count())
            .select_from(EvaluationJobRow)
            .where(EvaluationJobRow.state.in_(["QUEUED", "CLAIMED", "RUNNING"]))
        )
        return int(await session.scalar(statement) or 0)


def test_evaluation_launch_requires_a_valid_launch_key() -> None:
    with TestClient(app) as client:
        assert client.post("/v0/evaluations", json=_evaluation_payload(31)).status_code == 401
        wrong = client.post(
            "/v0/evaluations", headers=_launch_headers("rrl_test-launch.wrong"), json=_evaluation_payload(31)
        )
        assert wrong.status_code == 401
        worker_token = {"Authorization": "Bearer rrw_test-credential.test-worker-secret"}
        assert client.post("/v0/evaluations", headers=worker_token, json=_evaluation_payload(31)).status_code == 401
        too_many = client.post(
            "/v0/evaluations",
            headers=LAUNCH_HEADERS,
            json={**_evaluation_payload(31), "seeds": list(range(11))},
        )
        assert too_many.status_code == 422
        assert "seeds" in too_many.json()["detail"]
        assert client.get("/v0/policies").status_code == 200  # reads stay public


def test_launch_keys_enforce_quotas_and_ownership() -> None:
    with TestClient(app) as client:
        _, alice = asyncio.run(create_launch_credential(role="user", label="alice", concurrent_limit=1, daily_limit=2))
        _, bob = asyncio.run(create_launch_credential(role="user", label="bob", concurrent_limit=5, daily_limit=5))

        first = client.post("/v0/evaluations", headers=_launch_headers(alice), json=_evaluation_payload(41))
        assert first.status_code == 201
        blocked = client.post("/v0/evaluations", headers=_launch_headers(alice), json=_evaluation_payload(42))
        assert blocked.status_code == 429
        assert "active evaluation" in blocked.json()["detail"]

        job_id = first.json()["id"]
        assert client.post(f"/v0/evaluations/{job_id}/cancel", headers=_launch_headers(bob)).status_code == 403
        own = client.post(f"/v0/evaluations/{job_id}/cancel", headers=_launch_headers(alice))
        assert own.status_code == 200
        assert own.json()["state"] == "CANCELED"

        second = client.post("/v0/evaluations", headers=_launch_headers(alice), json=_evaluation_payload(42))
        assert second.status_code == 201
        client.post(f"/v0/evaluations/{second.json()['id']}/cancel", headers=_launch_headers(alice))
        daily = client.post("/v0/evaluations", headers=_launch_headers(alice), json=_evaluation_payload(43))
        assert daily.status_code == 429
        assert "24-hour" in daily.json()["detail"]

        bob_job = client.post("/v0/evaluations", headers=_launch_headers(bob), json=_evaluation_payload(44))
        assert bob_job.status_code == 201
        by_operator = client.post(f"/v0/evaluations/{bob_job.json()['id']}/cancel", headers=LAUNCH_HEADERS)
        assert by_operator.status_code == 200


def test_revoking_a_launch_key_cancels_its_jobs_and_rejects_the_key() -> None:
    with TestClient(app) as client:
        row, token = asyncio.run(
            create_launch_credential(role="user", label="revoked", concurrent_limit=3, daily_limit=5)
        )
        created = client.post("/v0/evaluations", headers=_launch_headers(token), json=_evaluation_payload(51))
        assert created.status_code == 201
        asyncio.run(revoke_launch_credential(row.credential_id))
        job = client.get(f"/v0/evaluations/{created.json()['id']}").json()
        assert job["state"] == "CANCELED"
        assert job["failure_detail"] == "launch key revoked"
        rejected = client.post("/v0/evaluations", headers=_launch_headers(token), json=_evaluation_payload(52))
        assert rejected.status_code == 401


def test_global_active_cap_applies_to_everyone_and_open_mode_skips_the_key(monkeypatch) -> None:
    with TestClient(app) as client:
        monkeypatch.setattr(api_main.settings, "max_active_evaluations", asyncio.run(_count_active_jobs()) + 1)
        allowed = client.post("/v0/evaluations", headers=LAUNCH_HEADERS, json=_evaluation_payload(61))
        assert allowed.status_code == 201
        full = client.post("/v0/evaluations", headers=LAUNCH_HEADERS, json=_evaluation_payload(62))
        assert full.status_code == 429
        assert "capacity" in full.json()["detail"]
        client.post(f"/v0/evaluations/{allowed.json()['id']}/cancel", headers=LAUNCH_HEADERS)

        monkeypatch.setattr(api_main.settings, "evaluation_access", "open")
        anonymous = client.post("/v0/evaluations", json=_evaluation_payload(63))
        assert anonymous.status_code == 201
        assert client.post(f"/v0/evaluations/{anonymous.json()['id']}/cancel").status_code == 200
