from __future__ import annotations

import json
from pathlib import Path

from roborouter_contracts import (
    CompatibilityQuery,
    CompatibilityRecord,
    EvaluationEnvironmentSpec,
    EvaluationJob,
    ExecutablePolicySpec,
    RobotProfile,
    Rollout,
    TaskProfile,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "packages" / "contracts" / "generated" / "schema.json"


def main() -> None:
    models = [
        RobotProfile,
        TaskProfile,
        ExecutablePolicySpec,
        CompatibilityQuery,
        CompatibilityRecord,
        EvaluationEnvironmentSpec,
        EvaluationJob,
        Rollout,
    ]
    schema = {model.__name__: model.model_json_schema() for model in models}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
