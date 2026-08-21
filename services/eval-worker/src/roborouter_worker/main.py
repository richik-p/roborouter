from __future__ import annotations

import asyncio
import hashlib
import logging
import mimetypes
from contextlib import suppress
from pathlib import Path

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict
from roborouter_contracts import Artifact, EvaluationJob, WorkerCapabilities

from .adapter import HarnessAdapter, HarnessError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("roborouter-worker")


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_base_url: str = "http://localhost:8000"
    worker_token: str = "local-worker-token-change-me"
    worker_id: str = "worker-local"
    gpu_name: str | None = None
    vram_gb: int | None = None
    vla_eval_root: Path = Path("vendor/vla-evaluation-harness")
    worker_output_root: Path = Path("artifacts/worker")
    poll_seconds: float = 5.0
    heartbeat_seconds: float = 25.0


def _artifact_kind(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in {".mp4", ".webm"}:
        return "video"
    if suffix in {".json", ".jsonl"}:
        return "observation_trace"
    if suffix in {".yaml", ".yml"}:
        return "config"
    if suffix in {".log", ".txt"}:
        return "log"
    return None


async def upload_artifacts(
    client: httpx.AsyncClient,
    settings: WorkerSettings,
    adapter: HarnessAdapter,
    job: EvaluationJob,
) -> list[Artifact]:
    artifacts: list[Artifact] = []
    async with httpx.AsyncClient(timeout=300) as upload_client:
        for path in sorted(adapter.output_dir(job).rglob("*")):
            kind = _artifact_kind(path) if path.is_file() else None
            if kind is None:
                continue
            content = path.read_bytes()
            media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            grant_response = await client.post(
                f"/private/workers/jobs/{job.id}/artifacts/presign",
                json={
                    "kind": kind,
                    "filename": path.name,
                    "media_type": media_type,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "size_bytes": len(content),
                },
            )
            grant_response.raise_for_status()
            grant = grant_response.json()
            uploaded = await upload_client.put(
                grant["upload_url"],
                content=content,
                headers=grant["required_headers"],
            )
            uploaded.raise_for_status()
            artifacts.append(Artifact.model_validate(grant["artifact"]))
    return artifacts


async def maintain_lease(
    client: httpx.AsyncClient,
    settings: WorkerSettings,
    job: EvaluationJob,
    stop: asyncio.Event,
) -> None:
    while not stop.is_set():
        response = await client.post(
            f"/private/workers/jobs/{job.id}/heartbeat",
        )
        response.raise_for_status()
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.heartbeat_seconds)
        except TimeoutError:
            continue


async def evaluation_was_canceled(client: httpx.AsyncClient, job: EvaluationJob) -> bool:
    try:
        response = await client.get(f"/v0/evaluations/{job.id}")
        response.raise_for_status()
    except httpx.HTTPError:
        return False
    return response.json().get("state") == "CANCELED"


async def work_forever(settings: WorkerSettings) -> None:
    headers = {"Authorization": f"Bearer {settings.worker_token}"}
    capabilities = WorkerCapabilities(
        worker_id=settings.worker_id,
        cuda=settings.gpu_name is not None,
        gpu_name=settings.gpu_name,
        vram_gb=settings.vram_gb,
        adapters=["vla_eval_lerobot"],
        environments=["vla-eval-libero-object", "vla-eval-libero-goal"],
    )
    adapter = HarnessAdapter(settings.vla_eval_root, settings.worker_output_root)
    async with httpx.AsyncClient(base_url=settings.api_base_url, headers=headers, timeout=30) as client:
        response = await client.post("/private/workers/register", json=capabilities.model_dump(mode="json"))
        response.raise_for_status()
        logger.info("registered worker %s", settings.worker_id)
        while True:
            response = await client.post("/private/workers/claim", json=capabilities.model_dump(mode="json"))
            response.raise_for_status()
            if response.json() is None:
                await asyncio.sleep(settings.poll_seconds)
                continue
            job = EvaluationJob.model_validate(response.json())
            logger.info("claimed %s", job.id)
            lease_stop = asyncio.Event()
            lease_task = asyncio.create_task(maintain_lease(client, settings, job, lease_stop))
            evaluation_task = asyncio.create_task(adapter.run(job))
            try:
                done, _ = await asyncio.wait(
                    {evaluation_task, lease_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if lease_task in done:
                    lease_task.result()
                    raise HarnessError("evaluation lease ended before the harness completed")
                rollouts = evaluation_task.result()
                artifacts = await upload_artifacts(client, settings, adapter, job)
                if lease_task.done():
                    lease_task.result()
                rollouts = [rollout.model_copy(update={"artifacts": artifacts}) for rollout in rollouts]
                result = await client.post(
                    f"/private/workers/jobs/{job.id}/complete",
                    json={
                        "rollouts": [item.model_dump(mode="json") for item in rollouts],
                    },
                )
                result.raise_for_status()
                logger.info("completed %s", job.id)
            except (HarnessError, httpx.HTTPError, OSError) as exc:
                logger.exception("evaluation %s failed", job.id)
                if not evaluation_task.done():
                    evaluation_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await evaluation_task
                if await evaluation_was_canceled(client, job):
                    logger.info("evaluation %s was canceled by the control plane", job.id)
                    continue
                failure = await client.post(
                    f"/private/workers/jobs/{job.id}/fail",
                    json={
                        "kind": "infrastructure",
                        "detail": str(exc),
                        "retry_safe": False,
                    },
                )
                failure.raise_for_status()
            finally:
                lease_stop.set()
                try:
                    await lease_task
                except httpx.HTTPError:
                    logger.exception("lease heartbeat stopped for %s", job.id)


def run() -> None:
    asyncio.run(work_forever(WorkerSettings()))


if __name__ == "__main__":
    run()
