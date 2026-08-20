from __future__ import annotations

import hashlib

from roborouter_contracts import (
    CompatibilityRecord,
    CompatibilityStatus,
    ExecutablePolicySpec,
    RobotProfile,
    SupportedPaths,
    TaskProfile,
)

RULESET_REVISION = "compat-v0.1.0"


def _id(*values: str) -> str:
    digest = hashlib.sha256("|".join(values).encode()).hexdigest()[:20]
    return f"compat-{digest}"


def evaluate(policy: ExecutablePolicySpec, robot: RobotProfile, task: TaskProfile) -> CompatibilityRecord:
    missing: list[str] = []
    reasons: list[str] = []

    if robot.robot_class not in policy.robot_classes:
        reasons.append("ROBOT_CLASS_MISMATCH")
    if task.task_family not in policy.task_families:
        reasons.append("TASK_FAMILY_MISMATCH")

    robot_sensor_types = {sensor.type for sensor in robot.sensors}
    for sensor_type in policy.observations.sensor_types:
        if sensor_type not in robot_sensor_types:
            missing.append(f"sensor:{sensor_type}")
            reasons.append("MISSING_REQUIRED_SENSOR")

    camera_names = {sensor.semantic_name for sensor in robot.sensors if sensor.semantic_name}
    for camera in policy.observations.cameras:
        if camera not in camera_names:
            missing.append(f"camera:{camera}")
            reasons.append("MISSING_CAMERA_MAPPING")

    surface = None
    if policy.actions:
        surface = next(
            (item for item in robot.control_surfaces if item.schema_id == policy.actions.schema_id),
            None,
        )
        if surface is None:
            missing.append(f"control_surface:{policy.actions.schema_id}")
            reasons.append("ACTION_SCHEMA_MISMATCH")
        elif policy.actions.dimensions and surface.dimensions != policy.actions.dimensions:
            missing.append(f"action_dimensions:{policy.actions.dimensions}")
            reasons.append("ACTION_DIMENSION_MISMATCH")
        elif policy.actions.expected_rate_hz and surface.rate_hz and surface.rate_hz < policy.actions.expected_rate_hz:
            missing.append(f"control_rate_hz:{policy.actions.expected_rate_hz}")
            reasons.append("CONTROL_RATE_TOO_LOW")
    else:
        reasons.append("ACTION_SEMANTICS_UNKNOWN")

    evidence = policy.evidence[0] if policy.evidence else None
    hard_mismatch = any(
        code in reasons
        for code in (
            "ROBOT_CLASS_MISMATCH",
            "TASK_FAMILY_MISMATCH",
            "MISSING_REQUIRED_SENSOR",
            "MISSING_CAMERA_MAPPING",
            "ACTION_SCHEMA_MISMATCH",
            "ACTION_DIMENSION_MISMATCH",
            "CONTROL_RATE_TOO_LOW",
        )
    )

    if hard_mismatch:
        status = CompatibilityStatus.INCOMPATIBLE
        score = 0
        explanation = "The policy does not satisfy this robot/task interface."
    elif policy.runtime is None or policy.actions is None:
        status = CompatibilityStatus.RESEARCH_ONLY
        score = 35
        explanation = "The family is relevant, but no exact runnable checkpoint and action contract is cataloged."
        reasons.append("NO_EXECUTABLE_SPEC")
    elif policy.source.checkpoint is None:
        status = CompatibilityStatus.FINE_TUNE_REQUIRED
        score = 45
        explanation = "The runtime is known, but no matching checkpoint is available."
        reasons.append("NO_MATCHING_CHECKPOINT_FOR_ROBOT")
    elif evidence and evidence.level in {"SIM_VERIFIED", "UPSTREAM_REPRODUCTION"}:
        status = CompatibilityStatus.SIM_VERIFIED
        score = 90 if evidence.exact_runtime_match else 75
        explanation = "The exact cataloged execution path has simulation evidence."
        reasons.append("EXACT_SIM_PATH_AVAILABLE")
    else:
        status = CompatibilityStatus.UNKNOWN
        score = 50
        explanation = "The interface is structurally plausible, but evidence is insufficient."
        reasons.append("INSUFFICIENT_EVIDENCE")

    return CompatibilityRecord(
        id=_id(
            policy.id,
            policy.revision,
            robot.id,
            robot.revision,
            task.id,
            task.revision,
            RULESET_REVISION,
        ),
        ruleset_revision=RULESET_REVISION,
        policy_id=policy.id,
        policy_revision=policy.revision,
        robot_profile_id=robot.id,
        robot_revision=robot.revision,
        task_profile_id=task.id,
        task_revision=task.revision,
        status=status,
        reason_codes=sorted(set(reasons)),
        explanation=explanation,
        missing_requirements=sorted(set(missing)),
        best_evidence=evidence,
        supported_paths=SupportedPaths(
            simulate=status == CompatibilityStatus.SIM_VERIFIED,
            shadow=False,
            actuate=False,
        ),
        score=score,
    )
