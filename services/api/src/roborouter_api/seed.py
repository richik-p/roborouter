from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from roborouter_contracts import Rollout
from sqlalchemy import select

from .catalog import load_catalog
from .database import SessionLocal, engine
from .db_models import Base, EnvironmentRow, PolicyRow, RobotRow, RolloutRow, TaskRow, WorkerCredentialRow
from .settings import get_settings
from .worker_auth import WORKER_SCOPES, hash_worker_token, parse_worker_token


def _json(model):
    return model.model_dump(mode="json", by_alias=True)


async def seed_database() -> None:
    settings = get_settings()
    policies, robots, tasks, environments = load_catalog(settings.catalog_root)
    if settings.auto_create_schema:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        if settings.worker_bootstrap_token:
            credential_id = parse_worker_token(settings.worker_bootstrap_token)
            if credential_id is None:
                raise RuntimeError("WORKER_BOOTSTRAP_TOKEN must use the rrw_<credential-id>.<secret> format")
            credential = await session.get(WorkerCredentialRow, credential_id)
            expected_hash = hash_worker_token(settings.worker_bootstrap_token)
            if credential is None:
                session.add(
                    WorkerCredentialRow(
                        credential_id=credential_id,
                        worker_id=settings.worker_bootstrap_id,
                        token_hash=expected_hash,
                        scopes=sorted(WORKER_SCOPES),
                        label="bootstrap",
                        created_at=datetime.now(UTC),
                        expires_at=None,
                        revoked_at=None,
                        last_used_at=None,
                    )
                )
            elif credential.worker_id != settings.worker_bootstrap_id or credential.token_hash != expected_hash:
                raise RuntimeError("bootstrap worker credential conflicts with the stored identity")

        for policy in policies:
            existing = await session.scalar(
                select(PolicyRow).where(
                    PolicyRow.policy_id == policy.id,
                    PolicyRow.revision == policy.revision,
                )
            )
            if existing is None:
                session.add(
                    PolicyRow(
                        policy_id=policy.id,
                        revision=policy.revision,
                        name=policy.name,
                        family=policy.family,
                        robot_classes=policy.robot_classes,
                        task_families=policy.task_families,
                        runtime_adapter=policy.runtime.adapter if policy.runtime else None,
                        evidence_level=policy.evidence[0].level.value if policy.evidence else "UNKNOWN",
                        spec=_json(policy),
                    )
                )
        for robot in robots:
            existing = await session.scalar(
                select(RobotRow).where(RobotRow.profile_id == robot.id, RobotRow.revision == robot.revision)
            )
            if existing is None:
                session.add(RobotRow(profile_id=robot.id, revision=robot.revision, spec=_json(robot)))
        for task in tasks:
            existing = await session.scalar(
                select(TaskRow).where(TaskRow.profile_id == task.id, TaskRow.revision == task.revision)
            )
            if existing is None:
                session.add(TaskRow(profile_id=task.id, revision=task.revision, spec=_json(task)))
        for env in environments:
            existing = await session.scalar(
                select(EnvironmentRow).where(
                    EnvironmentRow.environment_id == env.id,
                    EnvironmentRow.revision == env.revision,
                )
            )
            if existing is None:
                session.add(EnvironmentRow(environment_id=env.id, revision=env.revision, spec=_json(env)))

        fixture = Rollout(
            id="rollout-upstream-pi05-libero-object",
            mode="sim",
            policy_spec_id="pi05-libero",
            policy_revision="lerobot-pi05-libero-finetuned",
            robot_profile_id="sim-libero-panda",
            robot_revision="2026-08-20.1",
            task_profile_id="libero-object-pick-place",
            task_revision="2026-08-20.1",
            environment_id="vla-eval-libero-object",
            environment_revision="vla-eval-0.4.0-lerobot-0.6.0-libero-2a4566009395",
            seed=7,
            started_at=datetime(2026, 8, 20, tzinfo=UTC),
            duration_ms=0,
            success=True,
            metrics={"upstream_success_rate": 1.0, "episodes": 100},
            runtime_identity={
                "checkpoint": "lerobot/pi05_libero_finetuned_v044",
                "checkpoint_revision": "8e174154ef5f6c60a8da12ae99c303d8963138c1",
                "harness_revision": "2680ab2fafe981c2dba63c6c1a4e7bb4415dbb56",
                "container_digest": "sha256:2a4566009395888ae3904bde87cffceea7526e2e0f0667b933cae0e8e6134413",
                "lerobot": "0.6.0",
                "vla_eval": "0.4.0",
                "benchmark": "LIBERO Object",
            },
            evidence_note=(
                "Upstream aggregate reproduction fixture, not a RoboRouter-executed episode. "
                "The vla-eval reproduction report records 100/100 LIBERO Object successes."
            ),
        )
        matched_goal_fixtures = [
            Rollout(
                id="rollout-upstream-pi05-libero-goal",
                mode="sim",
                policy_spec_id="pi05-libero",
                policy_revision="lerobot-pi05-libero-finetuned",
                robot_profile_id="sim-libero-panda",
                robot_revision="2026-08-20.1",
                task_profile_id="libero-goal-interaction",
                task_revision="2026-08-20.1",
                environment_id="vla-eval-libero-goal",
                environment_revision="vla-eval-0.4.0-lerobot-0.6.0-libero-2a4566009395",
                seed=7,
                started_at=datetime(2026, 8, 20, 0, 1, tzinfo=UTC),
                duration_ms=0,
                success=True,
                metrics={"upstream_success_rate": 0.98, "episodes": 100},
                runtime_identity={
                    "checkpoint": "lerobot/pi05_libero_finetuned_v044",
                    "checkpoint_revision": "8e174154ef5f6c60a8da12ae99c303d8963138c1",
                    "harness_revision": "2680ab2fafe981c2dba63c6c1a4e7bb4415dbb56",
                    "container_digest": "sha256:2a4566009395888ae3904bde87cffceea7526e2e0f0667b933cae0e8e6134413",
                    "lerobot": "0.6.0",
                    "vla_eval": "0.4.0",
                    "benchmark": "LIBERO Goal",
                    "protocol": "upstream reproduction aggregate",
                },
                evidence_note=(
                    "Upstream aggregate reproduction fixture, not a RoboRouter-executed episode. "
                    "It is matched to the MolmoAct2 fixture by environment revision, task revision, seed, and protocol."
                ),
            ),
            Rollout(
                id="rollout-upstream-molmoact2-libero-goal",
                mode="sim",
                policy_spec_id="molmoact2-libero",
                policy_revision="allenai-molmoact2-libero",
                robot_profile_id="sim-libero-panda",
                robot_revision="2026-08-20.1",
                task_profile_id="libero-goal-interaction",
                task_revision="2026-08-20.1",
                environment_id="vla-eval-libero-goal",
                environment_revision="vla-eval-0.4.0-lerobot-0.6.0-libero-2a4566009395",
                seed=7,
                started_at=datetime(2026, 8, 20, 0, 2, tzinfo=UTC),
                duration_ms=0,
                success=True,
                metrics={"upstream_success_rate": 0.97, "episodes": 100},
                runtime_identity={
                    "checkpoint": "allenai/MolmoAct2-LIBERO",
                    "checkpoint_revision": "0d24a92bd1faf321ef497c3bbd5681af97c65aa2",
                    "harness_revision": "2680ab2fafe981c2dba63c6c1a4e7bb4415dbb56",
                    "container_digest": "sha256:2a4566009395888ae3904bde87cffceea7526e2e0f0667b933cae0e8e6134413",
                    "lerobot": "0.6.0",
                    "vla_eval": "0.4.0",
                    "benchmark": "LIBERO Goal",
                    "protocol": "upstream reproduction aggregate",
                },
                evidence_note=(
                    "Upstream aggregate reproduction fixture, not a RoboRouter-executed episode. "
                    "It is matched to the π₀.₅ fixture by environment revision, task revision, seed, and protocol."
                ),
            ),
        ]
        for rollout in [fixture, *matched_goal_fixtures]:
            existing_rollout = await session.get(RolloutRow, rollout.id)
            if existing_rollout is None:
                session.add(
                    RolloutRow(
                        rollout_id=rollout.id,
                        evaluation_job_id=None,
                        spec=_json(rollout),
                        created_at=rollout.started_at,
                    )
                )
        await session.commit()


def run() -> None:
    asyncio.run(seed_database())


if __name__ == "__main__":
    run()
