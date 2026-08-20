from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml
from huggingface_hub import snapshot_download
from roborouter_contracts import EvaluationJob, Rollout


class HarnessError(RuntimeError):
    pass


POLICY_CONFIGS = {
    "pi05-libero": "configs/model_servers/lerobot/pi05_libero.yaml",
    "molmoact2-libero": "configs/model_servers/lerobot/molmoact2_libero.yaml",
}

ENVIRONMENT_CONFIGS = {
    "vla-eval-libero-object": "configs/benchmarks/libero/object.yaml",
    "vla-eval-libero-goal": "configs/benchmarks/libero/goal.yaml",
}

CHECKPOINTS = {
    "pi05-libero": (
        "lerobot/pi05_libero_finetuned_v044",
        "8e174154ef5f6c60a8da12ae99c303d8963138c1",
    ),
    "molmoact2-libero": (
        "allenai/MolmoAct2-LIBERO",
        "0d24a92bd1faf321ef497c3bbd5681af97c65aa2",
    ),
}

HARNESS_REVISION = "2680ab2fafe981c2dba63c6c1a4e7bb4415dbb56"
LEROBOT_REVISION = "v0.6.0"
LIBERO_IMAGE_DIGEST = "sha256:2a4566009395888ae3904bde87cffceea7526e2e0f0667b933cae0e8e6134413"


class HarnessAdapter:
    def __init__(self, root: Path, output_root: Path) -> None:
        self.root = root.resolve()
        self.output_root = output_root.resolve()

    def validate(self, job: EvaluationJob) -> tuple[Path, Path]:
        if not self.root.exists():
            raise HarnessError("VLA_EVAL_ROOT does not exist")
        policy_config = POLICY_CONFIGS.get(job.request.policy_id)
        environment_config = ENVIRONMENT_CONFIGS.get(job.request.environment_id)
        if policy_config is None or environment_config is None:
            raise HarnessError("unsupported policy/environment pair")
        policy_path = self.root / policy_config
        environment_path = self.root / environment_config
        if not policy_path.is_file() or not environment_path.is_file():
            raise HarnessError("pinned vla-eval configuration is missing")
        try:
            head = subprocess.run(
                ["git", "-C", str(self.root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            dirty = subprocess.run(
                ["git", "-C", str(self.root), "diff", "--quiet", "HEAD", "--"],
                check=False,
            ).returncode
        except (OSError, subprocess.CalledProcessError) as exc:
            raise HarnessError("cannot verify the vla-eval checkout") from exc
        if head != HARNESS_REVISION or dirty:
            raise HarnessError("vla-eval checkout is not the clean pinned v0.4.0 commit")
        if shutil.which("vla-eval") is None:
            raise HarnessError("vla-eval executable is unavailable")
        return policy_path, environment_path

    def output_dir(self, job: EvaluationJob) -> Path:
        return self.output_root / job.id

    async def materialize_policy_config(self, job: EvaluationJob, source: Path, output_dir: Path) -> Path:
        repo_id, revision = CHECKPOINTS[job.request.policy_id]
        snapshot = await asyncio.to_thread(snapshot_download, repo_id=repo_id, revision=revision)
        payload = yaml.safe_load(source.read_text())
        inherited = payload.get("extends")
        if inherited:
            payload["extends"] = str((source.parent / inherited).resolve())
        payload.setdefault("args", {})["checkpoint"] = str(Path(snapshot).resolve())
        materialized = output_dir / "roborouter-policy.yaml"
        materialized.write_text(yaml.safe_dump(payload, sort_keys=False))
        return materialized

    def materialize_environment_config(self, source: Path, output_dir: Path) -> Path:
        payload = yaml.safe_load(source.read_text())
        image = payload.get("docker", {}).get("image")
        if not isinstance(image, str):
            raise HarnessError("LIBERO environment config has no Docker image")
        repository = image.split("@", 1)[0].removesuffix(":latest")
        payload["docker"]["image"] = f"{repository}@{LIBERO_IMAGE_DIGEST}"
        materialized = output_dir / "roborouter-environment.yaml"
        materialized.write_text(yaml.safe_dump(payload, sort_keys=False))
        return materialized

    async def run(self, job: EvaluationJob) -> list[Rollout]:
        policy_source, environment_source = self.validate(job)
        output_dir = self.output_dir(job)
        output_dir.mkdir(parents=True, exist_ok=False)
        policy_path = await self.materialize_policy_config(job, policy_source, output_dir)
        environment_path = self.materialize_environment_config(environment_source, output_dir)

        server = await asyncio.create_subprocess_exec(
            "vla-eval",
            "serve",
            "--config",
            str(policy_path),
            cwd=self.root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        process: asyncio.subprocess.Process | None = None
        try:
            await asyncio.sleep(5)
            if server.returncode is not None:
                output = await server.stdout.read() if server.stdout else b""
                raise HarnessError(f"model server exited during startup: {output.decode()[-2000:]}")
            command = [
                "vla-eval",
                "run",
                "--config",
                str(environment_path),
                "--output-dir",
                str(output_dir),
                "--yes",
            ]
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=self.root,
                env={**os.environ, "ROBOROUTER_SEEDS": ",".join(map(str, job.request.seeds))},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            output, _ = await process.communicate()
            (output_dir / "vla-eval.log").write_bytes(output)
            if process.returncode != 0:
                raise HarnessError(f"evaluation failed with exit {process.returncode}")
        finally:
            if process is not None and process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=10)
                except TimeoutError:
                    process.kill()
            if server.returncode is None:
                server.terminate()
                try:
                    await asyncio.wait_for(server.wait(), timeout=10)
                except TimeoutError:
                    server.kill()

        result_files = sorted(output_dir.rglob("*.json"))
        if not result_files:
            raise HarnessError("evaluation produced no JSON result")
        return self._map_results(job, result_files)

    def _map_results(self, job: EvaluationJob, result_files: list[Path]) -> list[Rollout]:
        payloads = []
        for path in result_files:
            try:
                payloads.append(json.loads(path.read_text()))
            except (json.JSONDecodeError, OSError):
                continue
        if not payloads:
            raise HarnessError("no readable evaluation result")

        rollouts: list[Rollout] = []
        for index, seed in enumerate(job.request.seeds):
            payload = payloads[min(index, len(payloads) - 1)]
            success = bool(payload.get("success", payload.get("success_rate", 0) >= 1))
            metrics = {key: value for key, value in payload.items() if isinstance(value, (bool, int, float))}
            rollouts.append(
                Rollout(
                    id=f"rollout-{uuid.uuid4()}",
                    evaluation_job_id=job.id,
                    mode="sim",
                    policy_spec_id=job.request.policy_id,
                    policy_revision=job.request.policy_revision,
                    robot_profile_id="sim-libero-panda",
                    robot_revision="2026-08-20.1",
                    task_profile_id=job.request.task_profile_id,
                    task_revision=job.request.task_revision,
                    environment_id=job.request.environment_id,
                    environment_revision=job.request.environment_revision,
                    seed=seed,
                    started_at=datetime.now(UTC),
                    duration_ms=int(payload.get("duration_ms", 0)),
                    success=success,
                    metrics=metrics,
                    runtime_identity={
                        "vla_eval": f"0.4.0@{HARNESS_REVISION}",
                        "lerobot": LEROBOT_REVISION,
                        "container_digest": LIBERO_IMAGE_DIGEST,
                        "checkpoint": (
                            f"{CHECKPOINTS[job.request.policy_id][0]}@{CHECKPOINTS[job.request.policy_id][1]}"
                        ),
                        "policy_config": POLICY_CONFIGS[job.request.policy_id],
                        "environment_config": ENVIRONMENT_CONFIGS[job.request.environment_id],
                    },
                    evidence_note="Executed by a RoboRouter remote evaluation worker.",
                )
            )
        return rollouts
