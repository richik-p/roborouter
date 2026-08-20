from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceLevel(StrEnum):
    NATIVE_REAL_VERIFIED = "NATIVE_REAL_VERIFIED"
    BRIDGED_REAL_VERIFIED = "BRIDGED_REAL_VERIFIED"
    SIM_VERIFIED = "SIM_VERIFIED"
    UPSTREAM_REPRODUCTION = "UPSTREAM_REPRODUCTION"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    UNKNOWN = "UNKNOWN"


class CompatibilityStatus(StrEnum):
    NATIVE_REAL_VERIFIED = "NATIVE_REAL_VERIFIED"
    BRIDGED_REAL_VERIFIED = "BRIDGED_REAL_VERIFIED"
    SIM_VERIFIED = "SIM_VERIFIED"
    FINE_TUNE_REQUIRED = "FINE_TUNE_REQUIRED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    UNKNOWN = "UNKNOWN"
    INCOMPATIBLE = "INCOMPATIBLE"


class EvaluationState(StrEnum):
    QUEUED = "QUEUED"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class Sensor(Contract):
    id: str
    type: str
    semantic_name: str | None = None
    dimensions: int | None = Field(default=None, gt=0)
    resolution: tuple[int, int] | None = None
    rate_hz: float | None = Field(default=None, gt=0)


class ControlSurface(Contract):
    schema_id: str = Field(alias="schema")
    dimensions: int | None = Field(default=None, gt=0)
    rate_hz: float | None = Field(default=None, gt=0)
    frame: str | None = None
    units: list[str] = Field(default_factory=list)


class Evidence(Contract):
    level: EvidenceLevel
    source: HttpUrl
    checked_at: date
    description: str
    exact_robot_match: bool = False
    exact_runtime_match: bool = False


class RobotProfile(Contract):
    id: str
    revision: str
    name: str
    robot_class: str
    manufacturer: str | None = None
    model: str | None = None
    middleware: str
    simulated: bool = False
    sensors: list[Sensor]
    control_surfaces: list[ControlSurface]
    safety_capabilities: dict[str, bool] = Field(default_factory=dict)


class TaskProfile(Contract):
    id: str
    revision: str
    name: str
    domain: str
    task_family: str
    language_conditioned: bool = False
    requirements: list[str] = Field(default_factory=list)
    environment: dict[str, Any] = Field(default_factory=dict)
    max_episode_s: int | None = Field(default=None, gt=0)


class SourceSpec(Contract):
    repository: HttpUrl
    checkpoint: str | None = None
    checkpoint_revision: str | None = None


class RuntimeSpec(Contract):
    adapter: str
    framework: str
    framework_revision: str
    engine_revision: str | None = None
    config: str | None = None


class ObservationRequirements(Contract):
    sensor_types: list[str] = Field(default_factory=list)
    cameras: list[str] = Field(default_factory=list)
    state_schema: str | None = None
    language_prompt: bool = False


class ActionSpec(Contract):
    schema_id: str = Field(alias="schema")
    dimensions: int | None = Field(default=None, gt=0)
    horizon: int | None = Field(default=None, gt=0)
    expected_rate_hz: float | None = Field(default=None, gt=0)
    frame: str | None = None
    normalization_id: str | None = None


class Availability(Contract):
    weights: Literal["open", "gated", "closed", "unavailable"]
    code: Literal["open", "closed", "unavailable"]
    license: str


class ExecutablePolicySpec(Contract):
    id: str
    revision: str
    name: str
    family: str
    role: str = "policy"
    description: str
    robot_classes: list[str]
    task_families: list[str]
    source: SourceSpec
    runtime: RuntimeSpec | None = None
    observations: ObservationRequirements
    actions: ActionSpec | None = None
    availability: Availability
    evidence: list[Evidence]
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def executable_claim_has_identity(self) -> ExecutablePolicySpec:
        if self.runtime is not None and not self.source.checkpoint:
            raise ValueError("an executable runtime requires an exact checkpoint")
        return self


class EvaluationEnvironmentSpec(Contract):
    id: str
    revision: str
    name: str
    benchmark: str
    suite: str
    simulator: str
    container_image: str
    container_digest: str
    robot_profile_id: str
    task_profile_id: str
    action_schema: str
    observation_schema: str
    evaluator: str
    default_seeds: list[int]
    license_requirements: list[str] = Field(default_factory=list)


class BridgeSpec(Contract):
    id: str
    revision: str
    input_schema: str
    output_schema: str
    assumptions: list[str]
    evidence: list[Evidence]


class SupportedPaths(Contract):
    simulate: bool
    shadow: bool = False
    actuate: bool = False


class CompatibilityQuery(Contract):
    robot_profile_id: str
    robot_revision: str
    task_profile_id: str
    task_revision: str
    policy_ids: list[str] | None = None
    minimum_evidence: EvidenceLevel | None = None


class CompatibilityRecord(Contract):
    id: str
    ruleset_revision: str
    policy_id: str
    policy_revision: str
    robot_profile_id: str
    robot_revision: str
    task_profile_id: str
    task_revision: str
    status: CompatibilityStatus
    reason_codes: list[str]
    explanation: str
    missing_requirements: list[str] = Field(default_factory=list)
    best_evidence: Evidence | None = None
    supported_paths: SupportedPaths
    score: int = Field(ge=0, le=100)


class EvaluationJobCreate(Contract):
    policy_id: str
    policy_revision: str
    environment_id: str
    environment_revision: str
    task_profile_id: str
    task_revision: str
    seeds: list[int] = Field(min_length=1, max_length=100)


class EvaluationJob(Contract):
    id: str
    request: EvaluationJobCreate
    state: EvaluationState
    created_at: datetime
    updated_at: datetime
    worker_id: str | None = None
    lease_expires_at: datetime | None = None
    failure_kind: Literal["infrastructure", "invalid_request", "policy", "canceled"] | None = None
    failure_detail: str | None = None
    retry_safe: bool = False


class Artifact(Contract):
    id: str
    kind: Literal[
        "video",
        "observation_trace",
        "predicted_action_trace",
        "executed_action_trace",
        "log",
        "config",
    ]
    uri: str
    media_type: str
    sha256: str
    size_bytes: int = Field(ge=0)


class Rollout(Contract):
    id: str
    evaluation_job_id: str | None = None
    mode: Literal["sim", "shadow", "actuate"]
    policy_spec_id: str
    policy_revision: str
    robot_profile_id: str
    robot_revision: str
    task_profile_id: str
    task_revision: str
    environment_id: str
    environment_revision: str
    seed: int
    started_at: datetime
    duration_ms: int = Field(ge=0)
    success: bool
    metrics: dict[str, float | int | bool]
    runtime_identity: dict[str, str]
    artifacts: list[Artifact] = Field(default_factory=list)
    safety: dict[str, Any] = Field(default_factory=dict)
    evidence_note: str | None = None


class WorkerCapabilities(Contract):
    worker_id: str
    cuda: bool
    gpu_name: str | None = None
    vram_gb: int | None = None
    adapters: list[str]
    environments: list[str]
