from pathlib import Path

import pytest
from pydantic import ValidationError
from roborouter_api.catalog import load_catalog
from roborouter_contracts import ExecutablePolicySpec

ROOT = Path(__file__).resolve().parents[3]


def test_launch_catalog_is_valid_and_broad() -> None:
    policies, robots, tasks, environments = load_catalog(ROOT / "catalog")
    assert len(policies) >= 20
    assert {robot.robot_class for robot in robots} >= {
        "manipulator.single_arm",
        "aerial.multirotor",
    }
    assert {task.domain for task in tasks} >= {"manipulation", "aerial_navigation"}
    assert environments[0].action_schema == "manipulation.ee_delta_pose.v1"


def test_executable_runtime_requires_checkpoint() -> None:
    policies, *_ = load_catalog(ROOT / "catalog")
    data = policies[0].model_dump(mode="json", by_alias=True)
    data["source"]["checkpoint"] = None
    with pytest.raises(ValidationError, match="exact checkpoint"):
        ExecutablePolicySpec.model_validate(data)


def test_contracts_are_immutable() -> None:
    policies, *_ = load_catalog(ROOT / "catalog")
    with pytest.raises(ValidationError):
        policies[0].name = "mutated"  # type: ignore[misc]
