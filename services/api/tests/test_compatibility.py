from pathlib import Path

from roborouter_api.catalog import load_catalog
from roborouter_api.compatibility import evaluate
from roborouter_contracts import CompatibilityStatus

ROOT = Path(__file__).resolve().parents[3]


def _catalog():
    policies, robots, tasks, _ = load_catalog(ROOT / "catalog")
    return (
        {item.id: item for item in policies},
        {item.id: item for item in robots},
        {item.id: item for item in tasks},
    )


def test_pi05_libero_is_sim_verified() -> None:
    policies, robots, tasks = _catalog()
    record = evaluate(
        policies["pi05-libero"],
        robots["sim-libero-panda"],
        tasks["libero-object-pick-place"],
    )
    assert record.status == CompatibilityStatus.SIM_VERIFIED
    assert record.supported_paths.simulate is True
    assert record.supported_paths.actuate is False
    assert record.score == 90


def test_aerovla_is_research_only_for_uav() -> None:
    policies, robots, tasks = _catalog()
    record = evaluate(
        policies["aerovla"],
        robots["sim-px4-multirotor"],
        tasks["uav-language-navigation"],
    )
    assert record.status == CompatibilityStatus.RESEARCH_ONLY
    assert "NO_EXECUTABLE_SPEC" in record.reason_codes


def test_arm_policy_is_incompatible_with_uav() -> None:
    policies, robots, tasks = _catalog()
    record = evaluate(
        policies["pi05-libero"],
        robots["sim-px4-multirotor"],
        tasks["uav-language-navigation"],
    )
    assert record.status == CompatibilityStatus.INCOMPATIBLE
    assert "ROBOT_CLASS_MISMATCH" in record.reason_codes
    assert "ACTION_SCHEMA_MISMATCH" in record.reason_codes
