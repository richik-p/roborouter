from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from roborouter_contracts import EvaluationJob, EvaluationJobCreate, EvaluationState
from roborouter_worker.adapter import HarnessAdapter, HarnessError, _select_summary


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


def _job(seeds: list[int]) -> EvaluationJob:
    return EvaluationJob(
        id="eval-test",
        request=EvaluationJobCreate(
            policy_id="pi05-libero",
            policy_revision="lerobot-pi05-libero-finetuned",
            environment_id="vla-eval-libero-object",
            environment_revision="vla-eval-0.4.0-lerobot-0.6.0-libero-2a4566009395",
            task_profile_id="libero-object-pick-place",
            task_revision="2026-08-20.1",
            seeds=seeds,
        ),
        state=EvaluationState.CLAIMED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


UPSTREAM_OBJECT_YAML = (
    "server:\n  url: ws://localhost:8000\n"
    "docker:\n  image: ghcr.io/allenai/vla-evaluation-harness/libero:latest\n"
    "benchmarks:\n  - benchmark: vla_eval.benchmarks.libero.benchmark:LIBEROBenchmark\n"
    "    subname: libero_object\n    episodes_per_task: 50\n"
    "    params:\n      suite: libero_object\n      seed: 7\n      num_steps_wait: 10\n"
)


def test_materialized_environment_bounds_the_run_to_one_seed(tmp_path: Path) -> None:
    source = tmp_path / "object.yaml"
    source.write_text(UPSTREAM_OBJECT_YAML)
    adapter = HarnessAdapter(tmp_path, tmp_path / "output", episodes_per_task=2)

    materialized = adapter.materialize_environment_config(source, tmp_path, seed=11, episodes_per_task=2)

    payload = yaml.safe_load(materialized.read_text())
    entry = payload["benchmarks"][0]
    assert materialized.name == "roborouter-environment-seed11.yaml"
    assert entry["params"]["seed"] == 11
    assert entry["episodes_per_task"] == 2
    assert entry["params"]["suite"] == "libero_object"
    digest = "sha256:2a4566009395888ae3904bde87cffceea7526e2e0f0667b933cae0e8e6134413"
    assert payload["docker"]["image"].endswith(f"@{digest}")
    assert HarnessAdapter.health_url(materialized) == "http://localhost:8000/health"


def test_select_summary_prefers_the_payload_with_a_success_rate() -> None:
    nested = {"benchmarks": [{"name": "libero_object", "success_rate": 0.9, "num_episodes": 10}]}
    flat = {"success_rate": 1.0, "num_episodes": 10}
    aggregate = {"benchmark": "LIBEROBenchmark", "mean_success": 1.0, "num_episodes_total": 1, "num_errors": 0, "seed": 7}
    assert _select_summary([{"episode": 0, "success": True}, flat]) is flat
    assert _select_summary([nested])["success_rate"] == 0.9
    assert _select_summary([{"sid": "x", "steps": 111}, aggregate]) is aggregate


def test_map_results_reads_the_v040_aggregate_format(tmp_path: Path) -> None:
    adapter = HarnessAdapter(tmp_path, tmp_path / "output")
    seed_dir = tmp_path / "seed-7"
    seed_dir.mkdir()
    (seed_dir / "LIBEROBenchmark_aggregate.json").write_text(
        '{"benchmark": "LIBEROBenchmark", "harness_version": "0.8.0", "seed": 7, "protocol_version": 1,'
        ' "mean_success": 0.9, "num_episodes_total": 10, "num_errors": 0, "tasks": [{"episodes": [{"steps": 111}]}]}'
    )
    [rollout] = adapter._map_results(_job([7]), {7: (seed_dir, 500)})
    assert rollout.success is False
    assert rollout.metrics["success_rate"] == 0.9
    assert rollout.metrics["mean_success"] == 0.9
    assert rollout.metrics["num_episodes_total"] == 10
    assert "protocol_version" not in rollout.metrics


def test_map_results_emits_one_rollout_per_seed_with_duration(tmp_path: Path) -> None:
    adapter = HarnessAdapter(tmp_path, tmp_path / "output", episodes_per_task=1)
    runs = {}
    for seed, rate in ((7, 1.0), (8, 0.5)):
        seed_dir = tmp_path / f"seed-{seed}"
        seed_dir.mkdir()
        (seed_dir / "roborouter-environment-seed7.yaml").write_text("ignored: true\n")
        (seed_dir / "summary.json").write_text(f'{{"success_rate": {rate}, "num_episodes": 10, "seed": {seed}}}')
        runs[seed] = (seed_dir, 1234 + seed)

    rollouts = adapter._map_results(_job([7, 8]), runs)

    assert [r.seed for r in rollouts] == [7, 8]
    assert [r.success for r in rollouts] == [True, False]
    assert rollouts[0].duration_ms == 1241
    assert rollouts[1].metrics["success_rate"] == 0.5
    assert "seed" not in rollouts[0].metrics
    assert rollouts[0].runtime_identity["episodes_per_task"] == "1"
    assert rollouts[0].runtime_identity["checkpoint"].endswith("@8e174154ef5f6c60a8da12ae99c303d8963138c1")


def test_map_results_refuses_a_seed_without_results(tmp_path: Path) -> None:
    adapter = HarnessAdapter(tmp_path, tmp_path / "output")
    empty = tmp_path / "seed-7"
    empty.mkdir()
    with pytest.raises(HarnessError, match="no readable JSON result"):
        adapter._map_results(_job([7]), {7: (empty, 10)})
