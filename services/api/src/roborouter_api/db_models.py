from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PolicyRow(Base):
    __tablename__ = "policies"
    __table_args__ = (UniqueConstraint("policy_id", "revision"),)

    pk: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[str] = mapped_column(String(120), index=True)
    revision: Mapped[str] = mapped_column(String(180))
    name: Mapped[str] = mapped_column(String(180), index=True)
    family: Mapped[str] = mapped_column(String(120), index=True)
    robot_classes: Mapped[list[str]] = mapped_column(JSON)
    task_families: Mapped[list[str]] = mapped_column(JSON)
    runtime_adapter: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    evidence_level: Mapped[str] = mapped_column(String(80), index=True)
    spec: Mapped[dict[str, Any]] = mapped_column(JSON)


class RobotRow(Base):
    __tablename__ = "robot_profiles"
    __table_args__ = (UniqueConstraint("profile_id", "revision"),)

    pk: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[str] = mapped_column(String(120), index=True)
    revision: Mapped[str] = mapped_column(String(120))
    spec: Mapped[dict[str, Any]] = mapped_column(JSON)


class TaskRow(Base):
    __tablename__ = "task_profiles"
    __table_args__ = (UniqueConstraint("profile_id", "revision"),)

    pk: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[str] = mapped_column(String(120), index=True)
    revision: Mapped[str] = mapped_column(String(120))
    spec: Mapped[dict[str, Any]] = mapped_column(JSON)


class EnvironmentRow(Base):
    __tablename__ = "evaluation_environments"
    __table_args__ = (UniqueConstraint("environment_id", "revision"),)

    pk: Mapped[int] = mapped_column(primary_key=True)
    environment_id: Mapped[str] = mapped_column(String(120), index=True)
    revision: Mapped[str] = mapped_column(String(180))
    spec: Mapped[dict[str, Any]] = mapped_column(JSON)


class CompatibilityRow(Base):
    __tablename__ = "compatibility_records"
    __table_args__ = (UniqueConstraint("cache_key"),)

    pk: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[str] = mapped_column(String(120), unique=True)
    cache_key: Mapped[str] = mapped_column(String(600))
    record: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EvaluationJobRow(Base):
    __tablename__ = "evaluation_jobs"

    job_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    state: Mapped[str] = mapped_column(String(40), index=True)
    request: Mapped[dict[str, Any]] = mapped_column(JSON)
    worker_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_kind: Mapped[str | None] = mapped_column(String(80), nullable=True)
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_safe: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RolloutRow(Base):
    __tablename__ = "rollouts"

    rollout_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    evaluation_job_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    spec: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ArtifactRow(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_job_id",
            "kind",
            "filename",
            "sha256",
            "size_bytes",
            "media_type",
            name="uq_artifact_job_identity",
        ),
    )

    artifact_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    evaluation_job_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_jobs.job_id", ondelete="CASCADE"),
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(80))
    filename: Mapped[str] = mapped_column(String(180))
    object_key: Mapped[str] = mapped_column(String(700), unique=True)
    uri: Mapped[str] = mapped_column(String(800), unique=True)
    media_type: Mapped[str] = mapped_column(String(180))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    state: Mapped[str] = mapped_column(String(40), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkerRow(Base):
    __tablename__ = "workers"

    worker_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
