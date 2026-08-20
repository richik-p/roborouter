from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from roborouter_contracts import EvaluationJob, EvaluationJobCreate, EvaluationState
from roborouter_worker.adapter import HarnessAdapter, HarnessError


def test_adapter_refuses_unknown_pair(tmp_path: Path) -> None:
    adapter = HarnessAdapter(tmp_path, tmp_path / "output")
    job = EvaluationJob(
        id="eval-test",
        request=EvaluationJobCreate(
            policy_id="unknown",
            policy_revision="1",
            environment_id="unknown",
            environment_revision="1",
            task_profile_id="task",
            task_revision="1",
            seeds=[7],
        ),
        state=EvaluationState.CLAIMED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    with pytest.raises(HarnessError, match="unsupported|does not exist"):
        adapter.validate(job)


@pytest.mark.asyncio
async def test_materialized_config_uses_immutable_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "harness"
    config_dir = root / "configs" / "model_servers" / "lerobot"
    config_dir.mkdir(parents=True)
    (config_dir / "_base.yaml").write_text("args:\n  device: cuda\n")
    source = config_dir / "pi05_libero.yaml"
    source.write_text("extends: _base.yaml\nargs:\n  checkpoint: mutable/main\n")
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()

    def fake_snapshot_download(*, repo_id: str, revision: str) -> str:
        assert repo_id == "lerobot/pi05_libero_finetuned_v044"
        assert revision == "8e174154ef5f6c60a8da12ae99c303d8963138c1"
        return str(snapshot)

    monkeypatch.setattr("roborouter_worker.adapter.snapshot_download", fake_snapshot_download)
    adapter = HarnessAdapter(root, tmp_path / "output")
    output_dir = tmp_path / "job"
    output_dir.mkdir()
    job = EvaluationJob(
        id="eval-test",
        request=EvaluationJobCreate(
            policy_id="pi05-libero",
            policy_revision="lerobot-pi05-libero-finetuned",
            environment_id="vla-eval-libero-object",
            environment_revision="vla-eval-0.4.0-lerobot-0.6.0-libero-2a4566009395",
            task_profile_id="libero-object-pick-place",
            task_revision="2026-08-20.1",
            seeds=[7],
        ),
        state=EvaluationState.CLAIMED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    materialized = await adapter.materialize_policy_config(job, source, output_dir)
    payload = yaml.safe_load(materialized.read_text())
    assert payload["extends"] == str((config_dir / "_base.yaml").resolve())
    assert payload["args"]["checkpoint"] == str(snapshot.resolve())


def test_materialized_environment_uses_digest(tmp_path: Path) -> None:
    source = tmp_path / "object.yaml"
    source.write_text("docker:\n  image: ghcr.io/allenai/vla-evaluation-harness/libero:latest\n")
    adapter = HarnessAdapter(tmp_path, tmp_path / "output")

    materialized = adapter.materialize_environment_config(source, tmp_path)

    payload = yaml.safe_load(materialized.read_text())
    assert payload["docker"]["image"].endswith(
        "@sha256:2a4566009395888ae3904bde87cffceea7526e2e0f0667b933cae0e8e6134413"
    )
