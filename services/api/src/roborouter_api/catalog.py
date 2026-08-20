from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError
from roborouter_contracts import (
    EvaluationEnvironmentSpec,
    ExecutablePolicySpec,
    RobotProfile,
    TaskProfile,
)


class CatalogError(ValueError):
    pass


def _yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise CatalogError(f"cannot read {path}: {exc}") from exc


def load_catalog(
    root: Path,
) -> tuple[
    list[ExecutablePolicySpec],
    list[RobotProfile],
    list[TaskProfile],
    list[EvaluationEnvironmentSpec],
]:
    try:
        policy_docs = []
        for path in sorted((root / "policies").glob("*.yaml")):
            policy_docs.extend(_yaml(path).get("policies", []))
        policies = [ExecutablePolicySpec.model_validate(item) for item in policy_docs]
        robots = [RobotProfile.model_validate(_yaml(path)) for path in sorted((root / "robots").glob("*.yaml"))]
        tasks = [TaskProfile.model_validate(_yaml(path)) for path in sorted((root / "tasks").glob("*.yaml"))]
        environments = [
            EvaluationEnvironmentSpec.model_validate(_yaml(path))
            for path in sorted((root / "environments").glob("*.yaml"))
        ]
    except ValidationError as exc:
        raise CatalogError(str(exc)) from exc

    for kind, values in (
        ("policy", policies),
        ("robot", robots),
        ("task", tasks),
        ("environment", environments),
    ):
        identities = [(item.id, item.revision) for item in values]
        if len(identities) != len(set(identities)):
            raise CatalogError(f"duplicate {kind} id + revision")
    if len(policies) < 20:
        raise CatalogError("launch catalog must contain at least 20 policies")
    return policies, robots, tasks, environments
