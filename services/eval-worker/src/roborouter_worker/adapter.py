from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
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
DEFAULT_SERVER_URL = "ws://localhost:8000"


class HarnessAdapter:
    def __init__(
        self,
        root: Path,
        output_root: Path,
        *,
        episodes_per_task: int = 1,
        server_ready_timeout_s: float = 1800.0,
        server_port: int = 8000,
    ) -> None:
        self.root = root.resolve()
        self.output_root = output_root.resolve()
        if episodes_per_task <= 0:
            raise ValueError("episodes_per_task must be positive")
        if not 1 <= server_port <= 65535:
            raise ValueError("server_port must be a TCP port")
        self.episodes_per_task = episodes_per_task
        self.server_ready_timeout_s = server_ready_timeout_s
        self.server_port = server_port

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
        payload["args"]["port"] = self.server_port
        materialized = output_dir / "roborouter-policy.yaml"
        materialized.write_text(yaml.safe_dump(payload, sort_keys=False))
        return materialized

    def materialize_environment_config(
        self,
        source: Path,
        output_dir: Path,
        *,
        seed: int | None = None,
        episodes_per_task: int | None = None,
    ) -> Path:
        """Pin the benchmark image by digest and bound the run to one seed.

        The harness treats ``seed`` as the master seed of a run, not an episode id, so
        one requested seed becomes one run over the suite's tasks with
        ``episodes_per_task`` episodes each. The upstream config's 50 episodes per task
        would otherwise run unchanged.
        """
        payload = yaml.safe_load(source.read_text())
        image = payload.get("docker", {}).get("image")
        if not isinstance(image, str):
            raise HarnessError("LIBERO environment config has no Docker image")
        repository = image.split("@", 1)[0].removesuffix(":latest")
        payload["docker"]["image"] = f"{repository}@{LIBERO_IMAGE_DIGEST}"
        server = payload.get("server")
        if not isinstance(server, dict):
            server = payload["server"] = {}
        server["url"] = f"ws://127.0.0.1:{self.server_port}"
        benchmarks = payload.get("benchmarks")
        if (seed is not None or episodes_per_task is not None) and not isinstance(benchmarks, list):
            raise HarnessError("environment config has no benchmarks list to bound")
        for entry in benchmarks or []:
            if seed is not None:
                entry.setdefault("params", {})["seed"] = seed
            if episodes_per_task is not None:
                entry["episodes_per_task"] = episodes_per_task
        suffix = "" if seed is None else f"-seed{seed}"
        materialized = output_dir / f"roborouter-environment{suffix}.yaml"
        materialized.write_text(yaml.safe_dump(payload, sort_keys=False))
        return materialized

    @staticmethod
    def health_url(environment_config: Path) -> str:
        payload = yaml.safe_load(environment_config.read_text()) or {}
        url = payload.get("server", {}).get("url") or DEFAULT_SERVER_URL
        parsed = urlparse(url)
        scheme = "https" if parsed.scheme == "wss" else "http"
        return f"{scheme}://{parsed.hostname or 'localhost'}:{parsed.port or 8000}/health"

    @staticmethod
    async def _answers(url: str) -> bool:
        async with httpx.AsyncClient(timeout=3.0) as client:
            try:
                await client.get(url)
                return True
            except httpx.HTTPError:
                return False

    async def assert_port_free(self, url: str) -> None:
        """Refuse to run if some other server already answers where ours will listen.

        The benchmark would otherwise be scored against a model this job did not start
        and would label the result with this job's policy identity.
        """
        if await self._answers(url):
            raise HarnessError(
                f"a model server already answers at {url}; refusing to evaluate against a server this job did not start"
            )

    @staticmethod
    async def stop_process_group(process: asyncio.subprocess.Process, grace_s: float = 10.0) -> None:
        """Terminate a subprocess and everything it spawned (it was started in its own session)."""
        if process.returncode is not None:
            return
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(os.getpgid(process.pid), sig)
            except ProcessLookupError:
                return
            try:
                await asyncio.wait_for(process.wait(), timeout=grace_s)
                return
            except TimeoutError:
                continue

    async def wait_for_server(self, server: asyncio.subprocess.Process, url: str, log_path: Path) -> float:
        """Block until the model server answers ``/health`` or exits.

        The harness client does not retry a refused connection, and a cold start may
        include building the server's own environment and downloading the checkpoint,
        so this wait is long and bounded rather than fixed.
        """
        started = time.monotonic()
        async with httpx.AsyncClient(timeout=5.0) as client:
            while True:
                if server.returncode is not None:
                    raise HarnessError(f"model server exited during startup: {_tail(log_path)}")
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        return time.monotonic() - started
                except httpx.HTTPError:
                    pass
                if time.monotonic() - started > self.server_ready_timeout_s:
                    raise HarnessError(f"model server did not become healthy within {self.server_ready_timeout_s:.0f}s")
                await asyncio.sleep(5)

    async def run(self, job: EvaluationJob) -> list[Rollout]:
        policy_source, environment_source = self.validate(job)
        output_dir = self.output_dir(job)
        output_dir.mkdir(parents=True, exist_ok=False)
        policy_path = await self.materialize_policy_config(job, policy_source, output_dir)
        server_log = output_dir / "model-server.log"
        health = f"http://127.0.0.1:{self.server_port}/health"
        await self.assert_port_free(health)

        with server_log.open("wb") as server_out:
            server = await asyncio.create_subprocess_exec(
                "vla-eval",
                "serve",
                "--config",
                str(policy_path),
                cwd=self.root,
                stdout=server_out,
                stderr=asyncio.subprocess.STDOUT,
                start_new_session=True,
            )
        process: asyncio.subprocess.Process | None = None
        runs: dict[int, tuple[Path, int]] = {}
        try:
            ready_s = await self.wait_for_server(server, health, server_log)
            (output_dir / "model-server-ready.json").write_text(
                json.dumps({"ready_after_s": round(ready_s, 1), "port": self.server_port, "server_pid": server.pid})
            )
            for seed in job.request.seeds:
                seed_dir = output_dir / f"seed-{seed}"
                seed_dir.mkdir()
                environment_path = self.materialize_environment_config(
                    environment_source,
                    seed_dir,
                    seed=seed,
                    episodes_per_task=self.episodes_per_task,
                )
                command = [
                    "vla-eval",
                    "run",
                    "--config",
                    str(environment_path),
                    "--output-dir",
                    str(seed_dir),
                    "--record-video",
                    "--yes",
                ]
                started = time.monotonic()
                process = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=self.root,
                    env={**os.environ, "ROBOROUTER_SEED": str(seed)},
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    start_new_session=True,
                )
                output, _ = await process.communicate()
                (seed_dir / "vla-eval.log").write_bytes(output)
                if process.returncode != 0:
                    raise HarnessError(f"evaluation for seed {seed} failed with exit {process.returncode}")
                runs[seed] = (seed_dir, int((time.monotonic() - started) * 1000))
                process = None
        finally:
            if process is not None:
                await self.stop_process_group(process)
            await self.stop_process_group(server)
            # The next job must not inherit this server: wait for the port to go silent.
            for _ in range(12):
                if not await self._answers(health):
                    break
                await asyncio.sleep(5)
            else:
                raise HarnessError(f"model server still answers at {health} after shutdown; refusing to leave it")

        return self._map_results(job, runs)

    def _map_results(self, job: EvaluationJob, runs: dict[int, tuple[Path, int]]) -> list[Rollout]:
        rollouts: list[Rollout] = []
        for seed in job.request.seeds:
            seed_dir, duration_ms = runs[seed]
            payloads = _read_json_payloads(seed_dir)
            if not payloads:
                raise HarnessError(f"evaluation for seed {seed} produced no readable JSON result")
            summary = _select_summary(payloads)
            success_rate = _success_rate(summary)
            success = bool(summary.get("success", success_rate is not None and success_rate >= 1))
            metrics = {
                key: value
                for key, value in summary.items()
                if isinstance(value, bool | int | float) and key not in {"seed", "protocol_version"}
            }
            if success_rate is not None:
                metrics["success_rate"] = success_rate
            metrics.setdefault("episodes_per_task", self.episodes_per_task)
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
                    duration_ms=duration_ms,
                    success=success,
                    metrics=metrics,
                    # Same keys as the seeded upstream fixtures, so the Compare page's matched-set
                    # identity (harness, container, vla_eval, protocol) applies to real runs too.
                    runtime_identity={
                        "vla_eval": "0.4.0",
                        "harness_revision": HARNESS_REVISION,
                        "lerobot": LEROBOT_REVISION,
                        "container_digest": LIBERO_IMAGE_DIGEST,
                        "checkpoint": CHECKPOINTS[job.request.policy_id][0],
                        "checkpoint_revision": CHECKPOINTS[job.request.policy_id][1],
                        "benchmark": job.request.environment_id,
                        "policy_config": POLICY_CONFIGS[job.request.policy_id],
                        "environment_config": ENVIRONMENT_CONFIGS[job.request.environment_id],
                        "protocol": f"roborouter.seed-run.v1 episodes_per_task={self.episodes_per_task}",
                    },
                    evidence_note=(
                        "Executed by a RoboRouter remote evaluation worker: one harness run per seed "
                        f"with {self.episodes_per_task} episode(s) per task."
                    ),
                )
            )
        return rollouts


def _tail(path: Path, limit: int = 2000) -> str:
    try:
        return path.read_text(errors="replace")[-limit:]
    except OSError:
        return "<no server log>"


def _read_json_payloads(directory: Path) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for path in sorted(directory.rglob("*.json")):
        if path.name == "model-server-ready.json" or path.name.startswith("roborouter-"):
            continue
        try:
            loaded = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(loaded, dict):
            payloads.append(loaded)
    return payloads


RATE_KEYS = ("success_rate", "mean_success")


def _success_rate(summary: dict[str, Any]) -> float | None:
    for key in RATE_KEYS:
        value = summary.get(key)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return float(value)
    return None


def _select_summary(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick the run summary: the first mapping, at most two levels deep, that reports a success rate.

    vla-eval v0.4.0 writes ``<Benchmark>_aggregate.json`` with ``mean_success``; older
    and merged summaries use ``success_rate``.
    """
    for payload in payloads:
        if _success_rate(payload) is not None:
            return payload
    for payload in payloads:
        for value in payload.values():
            if isinstance(value, dict) and _success_rate(value) is not None:
                return value
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and _success_rate(item) is not None:
                        return item
    return payloads[0]
