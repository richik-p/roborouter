# RoboRouter remote evaluation worker

The worker makes outbound HTTPS requests to the control plane. It never accepts an
inbound job connection. It claims only environments and adapters declared in its
capability record, maintains a lease throughout execution, uploads hashed artifacts
through short-lived scoped URLs, and completes the job idempotently.

## Pinned boundary

- Python: 3.11
- `vla-evaluation-harness`: `v0.4.0` (`2680ab2fafe981c2dba63c6c1a4e7bb4415dbb56`)
- LeRobot: `v0.6.0`
- π₀.₅ checkpoint: `lerobot/pi05_libero_finetuned_v044` at
  `8e174154ef5f6c60a8da12ae99c303d8963138c1`
- first suite: LIBERO Object
- second-family checkpoint: `allenai/MolmoAct2-LIBERO` at
  `0d24a92bd1faf321ef497c3bbd5681af97c65aa2`, LIBERO Goal
- LIBERO image: `ghcr.io/allenai/vla-evaluation-harness/libero` at
  `sha256:2a4566009395888ae3904bde87cffceea7526e2e0f0667b933cae0e8e6134413`

The worker verifies the harness Git commit is clean and rewrites the benchmark config
to use the digest above; a mutable `latest` reference is never executed.

## Remote setup

On a CUDA-capable NVIDIA Linux host, follow the upstream `v0.4.0` installation and
health-check instructions, then make that checkout available to the worker:

```bash
git clone --branch v0.4.0 --depth 1 https://github.com/allenai/vla-evaluation-harness.git vendor/vla-evaluation-harness
uv sync --all-packages --dev
```

On the control-plane host, create this worker's scoped credential first:

```bash
uv run roborouter-worker-credentials create --worker-id gpu-worker-01 --label primary-gpu --ttl-days 30
```

The command prints the raw `rrw_...` token once. Store it outside Git, then configure
that token and the HTTPS API URL in the worker's `.env`:

```dotenv
API_BASE_URL=https://api.example.invalid
WORKER_TOKEN=<scoped-worker-token>
WORKER_ID=gpu-worker-01
GPU_NAME=NVIDIA-H100-80GB-HBM3
VRAM_GB=80
VLA_EVAL_ROOT=vendor/vla-evaluation-harness
WORKER_OUTPUT_ROOT=artifacts/worker
```

Rotate without transferring active leases:

```bash
uv run roborouter-worker-credentials rotate <old-credential-id> \
  --overlap-minutes 15 --ttl-days 30 --label gpu-worker-01-rotation
```

Replace `WORKER_TOKEN` and restart the worker before the printed overlap deadline.
The old token may finish its existing lease during that window; the new token cannot
take the lease over.

Start the process with `make worker`. The adapter refuses missing pinned config files
or an unavailable `vla-eval` executable rather than inferring a runtime path. Before
launch it resolves the checkpoint at the recorded commit and materializes a derived
harness config that points to that immutable local snapshot. The worker control
process uses Python 3.11; the pinned harness's LeRobot PEP 723 model-server script
provisions its declared Python 3.12 runtime independently.

See [`../../docs/plans/remote-evaluation.md`](../../docs/plans/remote-evaluation.md)
for the smoke-run checklist and evidence record.
