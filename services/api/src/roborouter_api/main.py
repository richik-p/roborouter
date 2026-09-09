from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from roborouter_contracts import (
    Artifact,
    CompatibilityQuery,
    CompatibilityRecord,
    EvaluationEnvironmentSpec,
    EvaluationJob,
    EvaluationJobCreate,
    EvaluationState,
    ExecutablePolicySpec,
    RobotProfile,
    Rollout,
    TaskProfile,
    WorkerCapabilities,
)
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .compatibility import RULESET_REVISION, evaluate
from .database import get_session
from .db_models import (
    ArtifactRow,
    CompatibilityRow,
    EnvironmentRow,
    EvaluationJobRow,
    PolicyRow,
    RobotRow,
    RolloutRow,
    TaskRow,
    WorkerRow,
)
from .launch_auth import LaunchPrincipal, launch_principal
from .seed import seed_database
from .settings import get_settings
from .worker_auth import WorkerPrincipal, require_worker_scope

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await seed_database()
    yield


app = FastAPI(
    title="RoboRouter control plane",
    version="0.1.0",
    description="Evidence-aware robot policy discovery, compatibility, and evaluation API.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

Session = Annotated[AsyncSession, Depends(get_session)]
Launch = Annotated[LaunchPrincipal | None, Depends(launch_principal)]


class PolicyListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ExecutablePolicySpec]
    total: int


class RobotListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[RobotProfile]
    total: int


class TaskListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[TaskProfile]
    total: int


class EnvironmentListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[EvaluationEnvironmentSpec]
    total: int


class RolloutListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[Rollout]
    total: int


class WorkerCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rollouts: list[Rollout] = Field(min_length=1)


class WorkerFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["infrastructure", "invalid_request", "policy"]
    detail: str
    retry_safe: bool = False


class ArtifactPresignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal[
        "video",
        "observation_trace",
        "predicted_action_trace",
        "executed_action_trace",
        "log",
        "config",
    ]
    filename: str = Field(min_length=1, max_length=180)
    media_type: str = Field(min_length=1, max_length=180)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    size_bytes: int = Field(ge=0)


class ArtifactUploadGrant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    artifact: Artifact
    upload_url: str
    required_headers: dict[str, str]


def _job(row: EvaluationJobRow) -> EvaluationJob:
    return EvaluationJob(
        id=row.job_id,
        request=EvaluationJobCreate.model_validate(row.request),
        state=EvaluationState(row.state),
        created_at=row.created_at,
        updated_at=row.updated_at,
        worker_id=row.worker_id,
        lease_expires_at=row.lease_expires_at,
        failure_kind=row.failure_kind,
        failure_detail=row.failure_detail,
        retry_safe=row.retry_safe,
    )


ACTIVE_EVALUATION_STATES = (
    EvaluationState.QUEUED.value,
    EvaluationState.CLAIMED.value,
    EvaluationState.RUNNING.value,
)


async def _count_jobs(session: AsyncSession, *conditions) -> int:
    statement = select(func.count()).select_from(EvaluationJobRow).where(*conditions)
    return int(await session.scalar(statement) or 0)


async def _enforce_launch_quotas(session: AsyncSession, launch: LaunchPrincipal | None, now: datetime) -> None:
    """Apply the global active-job cap and the per-key quotas before queueing a job.

    The counts are advisory under concurrent requests: the cap bounds spend, it is not
    a strict invariant. Operators skip per-key quotas but never the global cap.
    """
    active = await _count_jobs(session, EvaluationJobRow.state.in_(ACTIVE_EVALUATION_STATES))
    if active >= settings.max_active_evaluations:
        raise HTTPException(status_code=429, detail="evaluation capacity is full; retry when a running job completes")
    if launch is None or launch.is_operator:
        return
    owned = EvaluationJobRow.launch_credential_id == launch.credential_id
    owned_active = await _count_jobs(session, owned, EvaluationJobRow.state.in_(ACTIVE_EVALUATION_STATES))
    if owned_active >= launch.concurrent_limit:
        raise HTTPException(
            status_code=429,
            detail=(
                f"this launch key already has {owned_active} active evaluation(s); "
                f"its limit is {launch.concurrent_limit}"
            ),
        )
    recent = await _count_jobs(session, owned, EvaluationJobRow.created_at >= now - timedelta(days=1))
    if recent >= launch.daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"this launch key reached its 24-hour limit of {launch.daily_limit} evaluations",
        )


def _canonical_digest(value: object) -> bytes:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).digest()


def _s3_client(endpoint_url: str | None = None):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
        config=Config(signature_version="s3v4"),
    )


def _artifact(row: ArtifactRow) -> Artifact:
    return Artifact(
        id=row.artifact_id,
        kind=row.kind,
        uri=row.uri,
        media_type=row.media_type,
        sha256=row.sha256,
        size_bytes=row.size_bytes,
    )


async def _verify_uploaded_artifact(row: ArtifactRow) -> None:
    if not settings.s3_verify_uploads:
        return
    try:
        result = await asyncio.to_thread(
            _s3_client().head_object,
            Bucket=settings.s3_bucket,
            Key=row.object_key,
        )
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchKey", "NotFound"}:
            raise HTTPException(status_code=422, detail=f"artifact {row.artifact_id} was not uploaded") from exc
        raise HTTPException(status_code=503, detail="artifact store is unavailable") from exc
    except BotoCoreError as exc:
        raise HTTPException(status_code=503, detail="artifact store is unavailable") from exc
    if (
        result.get("ContentLength") != row.size_bytes
        or result.get("ContentType", "").split(";", 1)[0] != row.media_type
        or result.get("Metadata", {}).get("sha256") != row.sha256
    ):
        raise HTTPException(status_code=422, detail=f"artifact {row.artifact_id} metadata does not match grant")


WorkerRegisterAuth = Annotated[WorkerPrincipal, Depends(require_worker_scope("worker:register"))]
WorkerClaimAuth = Annotated[WorkerPrincipal, Depends(require_worker_scope("job:claim"))]
WorkerHeartbeatAuth = Annotated[WorkerPrincipal, Depends(require_worker_scope("job:heartbeat"))]
WorkerArtifactAuth = Annotated[WorkerPrincipal, Depends(require_worker_scope("artifact:write"))]
WorkerCompleteAuth = Annotated[WorkerPrincipal, Depends(require_worker_scope("job:complete"))]
WorkerFailAuth = Annotated[WorkerPrincipal, Depends(require_worker_scope("job:fail"))]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "ruleset_revision": RULESET_REVISION}


def _current_policy_rows():
    """Select only the newest imported revision of each policy id.

    Older revisions stay in the table so Rollouts keep exact provenance; reads resolve
    the same way as get_policy (highest pk wins).
    """
    newest = select(func.max(PolicyRow.pk)).group_by(PolicyRow.policy_id)
    return select(PolicyRow).where(PolicyRow.pk.in_(newest))


@app.get("/v0/policies", response_model=PolicyListResponse)
async def list_policies(
    session: Session,
    q: str | None = None,
    robot_class: str | None = None,
    task_family: str | None = None,
    executable: bool | None = None,
) -> PolicyListResponse:
    statement = _current_policy_rows()
    if q:
        statement = statement.where(or_(PolicyRow.name.ilike(f"%{q}%"), PolicyRow.family.ilike(f"%{q}%")))
    if executable is True:
        statement = statement.where(PolicyRow.runtime_adapter.is_not(None))
    elif executable is False:
        statement = statement.where(PolicyRow.runtime_adapter.is_(None))
    rows = list((await session.scalars(statement.order_by(PolicyRow.name))).all())
    policies = [ExecutablePolicySpec.model_validate(row.spec) for row in rows]
    if robot_class:
        policies = [item for item in policies if robot_class in item.robot_classes]
    if task_family:
        policies = [item for item in policies if task_family in item.task_families]
    return PolicyListResponse(items=policies, total=len(policies))


@app.get("/v0/policies/{policy_id}", response_model=ExecutablePolicySpec)
async def get_policy(policy_id: str, session: Session) -> ExecutablePolicySpec:
    row = await session.scalar(select(PolicyRow).where(PolicyRow.policy_id == policy_id).order_by(PolicyRow.pk.desc()))
    if row is None:
        raise HTTPException(status_code=404, detail="policy not found")
    return ExecutablePolicySpec.model_validate(row.spec)


@app.get("/v0/robots", response_model=RobotListResponse)
async def list_robots(session: Session) -> RobotListResponse:
    rows = list((await session.scalars(select(RobotRow).order_by(RobotRow.profile_id))).all())
    items = [RobotProfile.model_validate(row.spec) for row in rows]
    return RobotListResponse(items=items, total=len(items))


@app.get("/v0/tasks", response_model=TaskListResponse)
async def list_tasks(session: Session) -> TaskListResponse:
    rows = list((await session.scalars(select(TaskRow).order_by(TaskRow.profile_id))).all())
    items = [TaskProfile.model_validate(row.spec) for row in rows]
    return TaskListResponse(items=items, total=len(items))


@app.get("/v0/environments", response_model=EnvironmentListResponse)
async def list_environments(session: Session) -> EnvironmentListResponse:
    rows = list((await session.scalars(select(EnvironmentRow).order_by(EnvironmentRow.environment_id))).all())
    items = [EvaluationEnvironmentSpec.model_validate(row.spec) for row in rows]
    return EnvironmentListResponse(items=items, total=len(items))


@app.post("/v0/compatibility/queries", response_model=list[CompatibilityRecord])
async def compatibility_query(query: CompatibilityQuery, session: Session) -> list[CompatibilityRecord]:
    robot_row = await session.scalar(
        select(RobotRow).where(
            RobotRow.profile_id == query.robot_profile_id,
            RobotRow.revision == query.robot_revision,
        )
    )
    task_row = await session.scalar(
        select(TaskRow).where(
            TaskRow.profile_id == query.task_profile_id,
            TaskRow.revision == query.task_revision,
        )
    )
    if robot_row is None or task_row is None:
        raise HTTPException(status_code=404, detail="robot or task revision not found")
    robot = RobotProfile.model_validate(robot_row.spec)
    task = TaskProfile.model_validate(task_row.spec)
    statement = _current_policy_rows()
    if query.policy_ids:
        statement = statement.where(PolicyRow.policy_id.in_(query.policy_ids))
    policies = [ExecutablePolicySpec.model_validate(row.spec) for row in (await session.scalars(statement)).all()]
    records = [evaluate(policy, robot, task) for policy in policies]
    for record in records:
        cache_key = "|".join(
            [
                record.policy_id,
                record.policy_revision,
                record.robot_profile_id,
                record.robot_revision,
                record.task_profile_id,
                record.task_revision,
                record.ruleset_revision,
            ]
        )
        existing = await session.scalar(select(CompatibilityRow).where(CompatibilityRow.cache_key == cache_key))
        if existing is None:
            session.add(
                CompatibilityRow(
                    record_id=record.id,
                    cache_key=cache_key,
                    record=record.model_dump(mode="json"),
                    created_at=datetime.now(UTC),
                )
            )
    await session.commit()
    return sorted(records, key=lambda item: item.score, reverse=True)


@app.post("/v0/evaluations", response_model=EvaluationJob, status_code=201)
async def create_evaluation(request: EvaluationJobCreate, session: Session, launch: Launch) -> EvaluationJob:
    if len(request.seeds) > settings.max_seeds_per_evaluation:
        raise HTTPException(
            status_code=422,
            detail=f"at most {settings.max_seeds_per_evaluation} seeds per evaluation",
        )
    policy = await session.scalar(
        select(PolicyRow).where(
            PolicyRow.policy_id == request.policy_id,
            PolicyRow.revision == request.policy_revision,
        )
    )
    environment = await session.scalar(
        select(EnvironmentRow).where(
            EnvironmentRow.environment_id == request.environment_id,
            EnvironmentRow.revision == request.environment_revision,
        )
    )
    task = await session.scalar(
        select(TaskRow).where(
            TaskRow.profile_id == request.task_profile_id,
            TaskRow.revision == request.task_revision,
        )
    )
    if policy is None or environment is None or task is None:
        raise HTTPException(status_code=422, detail="unknown or stale evaluation revision")
    spec = ExecutablePolicySpec.model_validate(policy.spec)
    environment_spec = EvaluationEnvironmentSpec.model_validate(environment.spec)
    task_spec = TaskProfile.model_validate(task.spec)
    if spec.runtime is None:
        raise HTTPException(status_code=422, detail="policy has no executable runtime")
    if environment_spec.task_profile_id != task_spec.id:
        raise HTTPException(status_code=422, detail="task does not belong to evaluation environment")
    if task_spec.task_family not in spec.task_families:
        raise HTTPException(status_code=422, detail="policy does not support the requested task family")
    if spec.actions is None or spec.actions.schema_id != environment_spec.action_schema:
        raise HTTPException(status_code=422, detail="policy action schema does not match environment")
    now = datetime.now(UTC)
    await _enforce_launch_quotas(session, launch, now)
    row = EvaluationJobRow(
        job_id=f"eval-{uuid.uuid4()}",
        state=EvaluationState.QUEUED.value,
        request=request.model_dump(mode="json"),
        worker_id=None,
        launch_credential_id=launch.credential_id if launch is not None else None,
        lease_expires_at=None,
        failure_kind=None,
        failure_detail=None,
        retry_safe=False,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.commit()
    return _job(row)


@app.get("/v0/evaluations/{job_id}", response_model=EvaluationJob)
async def get_evaluation(job_id: str, session: Session) -> EvaluationJob:
    row = await session.get(EvaluationJobRow, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    return _job(row)


@app.post("/v0/evaluations/{job_id}/cancel", response_model=EvaluationJob)
async def cancel_evaluation(job_id: str, session: Session, launch: Launch) -> EvaluationJob:
    row = await session.get(EvaluationJobRow, job_id, with_for_update=True)
    if row is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    if launch is not None and not launch.is_operator and row.launch_credential_id != launch.credential_id:
        raise HTTPException(status_code=403, detail="launch key does not own this evaluation")
    if row.state in {EvaluationState.SUCCEEDED.value, EvaluationState.FAILED.value}:
        raise HTTPException(status_code=409, detail="completed evaluation cannot be canceled")
    row.state = EvaluationState.CANCELED.value
    row.failure_kind = "canceled"
    row.updated_at = datetime.now(UTC)
    await session.commit()
    return _job(row)


@app.get("/v0/rollouts", response_model=RolloutListResponse)
async def list_rollouts(
    session: Session,
    policy_id: str | None = None,
    environment_id: str | None = None,
    task_profile_id: str | None = None,
) -> RolloutListResponse:
    rows = list((await session.scalars(select(RolloutRow).order_by(RolloutRow.created_at.desc()))).all())
    items = [Rollout.model_validate(row.spec) for row in rows]
    if policy_id:
        items = [item for item in items if item.policy_spec_id == policy_id]
    if environment_id:
        items = [item for item in items if item.environment_id == environment_id]
    if task_profile_id:
        items = [item for item in items if item.task_profile_id == task_profile_id]
    return RolloutListResponse(items=items, total=len(items))


@app.get("/v0/evaluations/{job_id}/rollouts", response_model=RolloutListResponse)
async def list_evaluation_rollouts(job_id: str, session: Session) -> RolloutListResponse:
    if await session.get(EvaluationJobRow, job_id) is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    rows = list(
        (
            await session.scalars(
                select(RolloutRow)
                .where(RolloutRow.evaluation_job_id == job_id)
                .order_by(RolloutRow.created_at)
            )
        ).all()
    )
    items = [Rollout.model_validate(row.spec) for row in rows]
    return RolloutListResponse(items=items, total=len(items))


@app.get("/v0/rollouts/{rollout_id}", response_model=Rollout)
async def get_rollout(rollout_id: str, session: Session) -> Rollout:
    row = await session.get(RolloutRow, rollout_id)
    if row is None:
        raise HTTPException(status_code=404, detail="rollout not found")
    return Rollout.model_validate(row.spec)


@app.post("/private/workers/register", response_model=WorkerCapabilities)
async def register_worker(
    capabilities: WorkerCapabilities, principal: WorkerRegisterAuth, session: Session
) -> WorkerCapabilities:
    if principal.worker_id != capabilities.worker_id:
        raise HTTPException(status_code=403, detail="credential cannot register another worker identity")
    row = await session.get(WorkerRow, capabilities.worker_id)
    now = datetime.now(UTC)
    data = capabilities.model_dump(mode="json")
    if row is None:
        session.add(WorkerRow(worker_id=capabilities.worker_id, capabilities=data, last_seen_at=now))
    else:
        row.capabilities = data
        row.last_seen_at = now
    await session.commit()
    return capabilities


@app.post("/private/workers/claim", response_model=EvaluationJob | None)
async def claim_job(
    capabilities: WorkerCapabilities, principal: WorkerClaimAuth, session: Session
) -> EvaluationJob | None:
    if principal.worker_id != capabilities.worker_id:
        raise HTTPException(status_code=403, detail="credential cannot claim for another worker identity")
    now = datetime.now(UTC)
    statement = (
        select(EvaluationJobRow)
        .where(
            or_(
                EvaluationJobRow.state == EvaluationState.QUEUED.value,
                (
                    (EvaluationJobRow.state == EvaluationState.CLAIMED.value)
                    & (EvaluationJobRow.retry_safe.is_(True))
                    & (EvaluationJobRow.lease_expires_at < now)
                ),
            )
        )
        .order_by(EvaluationJobRow.created_at)
        .with_for_update(skip_locked=True)
    )
    for row in (await session.scalars(statement)).all():
        request = EvaluationJobCreate.model_validate(row.request)
        policy_row = await session.scalar(
            select(PolicyRow).where(
                PolicyRow.policy_id == request.policy_id,
                PolicyRow.revision == request.policy_revision,
            )
        )
        if policy_row is None:
            continue
        policy = ExecutablePolicySpec.model_validate(policy_row.spec)
        if policy.runtime is None or policy.runtime.adapter not in capabilities.adapters:
            continue
        if request.environment_id not in capabilities.environments:
            continue
        row.state = EvaluationState.CLAIMED.value
        row.worker_id = capabilities.worker_id
        row.credential_id = principal.credential_id
        row.lease_expires_at = now + timedelta(seconds=settings.worker_lease_seconds)
        row.updated_at = now
        await session.commit()
        return _job(row)
    return None


@app.post("/private/workers/jobs/{job_id}/heartbeat", response_model=EvaluationJob)
async def heartbeat(job_id: str, principal: WorkerHeartbeatAuth, session: Session) -> EvaluationJob:
    row = await session.get(EvaluationJobRow, job_id, with_for_update=True)
    if row is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    if (
        row.worker_id != principal.worker_id
        or row.credential_id != principal.credential_id
        or row.state not in {"CLAIMED", "RUNNING"}
    ):
        raise HTTPException(status_code=409, detail="worker does not own an active lease")
    now = datetime.now(UTC)
    row.state = EvaluationState.RUNNING.value
    row.lease_expires_at = now + timedelta(seconds=settings.worker_lease_seconds)
    row.updated_at = now
    await session.commit()
    return _job(row)


@app.post(
    "/private/workers/jobs/{job_id}/artifacts/presign",
    response_model=ArtifactUploadGrant,
)
async def presign_artifact(
    job_id: str,
    body: ArtifactPresignRequest,
    principal: WorkerArtifactAuth,
    session: Session,
) -> ArtifactUploadGrant:
    row = await session.get(EvaluationJobRow, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    if (
        row.worker_id != principal.worker_id
        or row.credential_id != principal.credential_id
        or row.state not in {"CLAIMED", "RUNNING"}
    ):
        raise HTTPException(status_code=409, detail="worker does not own this evaluation")
    safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", body.filename)
    identity = "|".join([job_id, body.kind, safe_filename, body.media_type, body.sha256, str(body.size_bytes)])
    artifact_id = f"artifact-{hashlib.sha256(identity.encode()).hexdigest()[:32]}"
    key = f"jobs/{job_id}/{artifact_id}/{safe_filename}"
    artifact_row = await session.get(ArtifactRow, artifact_id)
    if artifact_row is None:
        artifact_row = ArtifactRow(
            artifact_id=artifact_id,
            evaluation_job_id=job_id,
            kind=body.kind,
            filename=safe_filename,
            object_key=key,
            uri=f"s3://{settings.s3_bucket}/{key}",
            media_type=body.media_type,
            sha256=body.sha256,
            size_bytes=body.size_bytes,
            state="GRANTED",
            created_at=datetime.now(UTC),
            attached_at=None,
        )
        session.add(artifact_row)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            artifact_row = await session.get(ArtifactRow, artifact_id)
            if artifact_row is None:
                raise HTTPException(status_code=409, detail="artifact grant conflict") from None
    upload_url = _s3_client(settings.s3_public_endpoint_url).generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "ContentType": body.media_type,
            "Metadata": {"sha256": body.sha256},
        },
        ExpiresIn=900,
    )
    return ArtifactUploadGrant(
        artifact=_artifact(artifact_row),
        upload_url=upload_url,
        required_headers={"Content-Type": body.media_type, "x-amz-meta-sha256": body.sha256},
    )


@app.post("/private/workers/jobs/{job_id}/complete", response_model=EvaluationJob)
async def complete_job(
    job_id: str, body: WorkerCompletion, principal: WorkerCompleteAuth, session: Session
) -> EvaluationJob:
    row = await session.get(EvaluationJobRow, job_id, with_for_update=True)
    if row is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    if row.worker_id != principal.worker_id or row.credential_id != principal.credential_id:
        raise HTTPException(status_code=409, detail="worker credential does not own this evaluation")
    if row.state == EvaluationState.SUCCEEDED.value:
        for rollout in body.rollouts:
            existing = await session.get(RolloutRow, rollout.id)
            if (
                rollout.evaluation_job_id != job_id
                or existing is None
                or _canonical_digest(existing.spec) != _canonical_digest(rollout.model_dump(mode="json"))
            ):
                raise HTTPException(status_code=409, detail="completed evaluation content does not match")
        return _job(row)
    if row.state not in {"CLAIMED", "RUNNING"}:
        raise HTTPException(status_code=409, detail="worker does not own this evaluation")
    artifact_rows: dict[str, ArtifactRow] = {}
    for rollout in body.rollouts:
        for item in rollout.artifacts:
            artifact_row = await session.get(ArtifactRow, item.id)
            if (
                artifact_row is None
                or artifact_row.evaluation_job_id != job_id
                or _canonical_digest(_artifact(artifact_row).model_dump(mode="json"))
                != _canonical_digest(item.model_dump(mode="json"))
            ):
                raise HTTPException(status_code=422, detail=f"artifact {item.id} was not granted for this evaluation")
            artifact_rows[item.id] = artifact_row
    if not artifact_rows:
        raise HTTPException(status_code=422, detail="evaluation completion requires at least one granted artifact")
    for artifact_row in artifact_rows.values():
        await _verify_uploaded_artifact(artifact_row)
    for rollout in body.rollouts:
        if rollout.evaluation_job_id != job_id:
            raise HTTPException(status_code=422, detail="rollout job identity mismatch")
        existing = await session.get(RolloutRow, rollout.id)
        if existing is None:
            session.add(
                RolloutRow(
                    rollout_id=rollout.id,
                    evaluation_job_id=job_id,
                    spec=rollout.model_dump(mode="json"),
                    created_at=rollout.started_at,
                )
            )
        elif _canonical_digest(existing.spec) != _canonical_digest(rollout.model_dump(mode="json")):
            raise HTTPException(status_code=409, detail="rollout identity already has different content")
    row.state = EvaluationState.SUCCEEDED.value
    row.updated_at = datetime.now(UTC)
    row.lease_expires_at = None
    for artifact_row in artifact_rows.values():
        artifact_row.state = "ATTACHED"
        artifact_row.attached_at = row.updated_at
    await session.commit()
    return _job(row)


@app.post("/private/workers/jobs/{job_id}/fail", response_model=EvaluationJob)
async def fail_job(job_id: str, body: WorkerFailure, principal: WorkerFailAuth, session: Session) -> EvaluationJob:
    row = await session.get(EvaluationJobRow, job_id, with_for_update=True)
    if row is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    if (
        row.worker_id != principal.worker_id
        or row.credential_id != principal.credential_id
        or row.state not in {"CLAIMED", "RUNNING"}
    ):
        raise HTTPException(status_code=409, detail="worker does not own this evaluation")
    row.state = EvaluationState.FAILED.value
    row.failure_kind = body.kind
    row.failure_detail = body.detail[:4000]
    row.retry_safe = body.retry_safe
    row.lease_expires_at = None
    row.updated_at = datetime.now(UTC)
    await session.commit()
    return _job(row)
