# TLS control plane and NVIDIA worker runbook

## Outcome

At the end of this runbook:

- the RoboRouter app and API are reachable through public TLS;
- PostgreSQL, MinIO, API, and web ports remain bound to loopback;
- a single outbound-only NVIDIA worker is registered with a unique smoke token;
- one π₀.₅/LIBERO Object Rollout has durable, hash-verified artifacts;
- π₀.₅ and MolmoAct2 have completed a matched one-seed LIBERO Goal comparison.

This is a supervised engineering smoke deployment, not a public beta. The app host is
password-protected, the worker host exposes no RoboRouter inbound port, and the
artifact bucket remains private.

## Single-box variant (first run, 2026-10-02)

The first real run used one GPU host for everything, with no DNS, TLS, or public
ports: API on `127.0.0.1:8800` (the harness's model server owns 8000), PostgreSQL
and the S3 store in Docker on loopback, and the worker on the same host pointed at
`http://127.0.0.1:8800`. Phases 2 and 3 below apply unchanged. Two things learned:

- **π₀.₅ needs gated access.** LeRobot's π₀.₅ loads `google/paligemma-3b-pt-224`,
  which is gated. Accept the terms with the Hugging Face account that will run the
  worker, create a read token, and export it as `HF_TOKEN` in the worker's
  environment. Without it the model server exits at load.
- **Worker knobs.** `EPISODES_PER_TASK` (default 1) bounds each seed's run;
  `SERVER_READY_TIMEOUT_S` (default 1800) bounds the cold-start wait.

## Required inputs

Prepare these values before provisioning:

```text
CONTROL_PLANE_IP       public IPv4 address of the CPU/control-plane host
APP_DOMAIN             for example app.roborouter.example
WORKER_DOMAIN          for example worker.roborouter.example
ARTIFACT_DOMAIN        for example artifacts.roborouter.example
OPERATOR_USERNAME      HTTP basic-auth username for the smoke UI
OPERATOR_PASSWORD      generated high-entropy password, stored outside Git
GPU_SSH_TARGET         for example ubuntu@gpu-host.example
```

Create DNS `A`/`AAAA` records for all three domains pointing to the control-plane
host. Open TCP 80/443 publicly for certificate issuance and HTTPS. Restrict SSH to
your source IP. Do not open 3000, 5432, 8000, 9000, or 9001.

Use Ubuntu 24.04 LTS or another Docker-supported Linux release. Docker's official
Ubuntu installation instructions and firewall caveats are the source of truth:
https://docs.docker.com/engine/install/ubuntu/

## Phase 1 — control-plane host

### 1. Clone and verify the repository

```bash
sudo install -d -o "$USER" -g "$USER" /opt/roborouter
git clone git@github.com:richik-p/roborouter.git /opt/roborouter
cd /opt/roborouter
git switch main
git pull --ff-only
git status --short
git log -1 --oneline
```

The status output must be empty. Record the commit ID in the evaluation evidence.

Install Node.js 22, Python 3.11, `uv`, Docker Engine with Compose, and Caddy from
their official repositories. Avoid convenience installation scripts on a persistent
host. Confirm:

```bash
node --version
python3.11 --version
uv --version
docker version
docker compose version
caddy version
```

### 2. Install and verify application dependencies

```bash
cd /opt/roborouter
npm ci
uv sync --all-packages --dev --frozen
make check
```

Do not continue if generated OpenAPI/TypeScript files drift or if any test/build
fails.

### 3. Configure secrets

Generate the password and token interactively. Do not place either value in shell
history, issue comments, CI output, or Git. For example, run `openssl rand -hex 32`
and copy each result directly into a password manager.

Create `/opt/roborouter/.env`, mode `0600`:

```dotenv
DATABASE_URL=postgresql+asyncpg://roborouter:<database-password>@127.0.0.1:5432/roborouter
POSTGRES_PASSWORD=<same-database-password>
S3_ENDPOINT_URL=http://127.0.0.1:9000
S3_PUBLIC_ENDPOINT_URL=https://<ARTIFACT_DOMAIN>
S3_ACCESS_KEY=roborouter
S3_SECRET_KEY=<minio-password>
MINIO_ROOT_USER=roborouter
MINIO_ROOT_PASSWORD=<same-minio-password>
S3_BUCKET=roborouter-artifacts
S3_VERIFY_UPLOADS=true
AUTO_CREATE_SCHEMA=false
CORS_ORIGINS=["https://<APP_DOMAIN>"]
EVALUATION_ACCESS=key
MAX_ACTIVE_EVALUATIONS=1
MAX_SEEDS_PER_EVALUATION=10
```

Replace the matching development passwords in `infra/compose.yml` through a local
Compose override or a deployment secret mechanism. Do not commit the override. The
checked-in values are development-only.

### 4. Start persistence, migrate, and seed

```bash
cd /opt/roborouter
docker compose \
  -f infra/compose.yml \
  -f infra/compose.production.yml \
  up -d --wait postgres minio
docker compose \
  -f infra/compose.yml \
  -f infra/compose.production.yml \
  run --rm minio-init
uv run alembic upgrade head
uv run alembic check
uv run roborouter-seed
```

Create a credential specifically for this worker. The raw token is printed once;
copy it directly into the password manager and the worker host's secret file:

```bash
uv run roborouter-worker-credentials create \
  --worker-id gpu-worker-01 \
  --label libero-smoke-01 \
  --ttl-days 30
uv run roborouter-worker-credentials list --worker-id gpu-worker-01
```

Do not place the printed token in the control-plane `.env`. The API stores only its
SHA-256 digest. To revoke it, run
`uv run roborouter-worker-credentials revoke <credential-id>`; any lease owned by
that exact credential is failed and cannot be completed with a different token.

Evaluation launches are closed by default (`EVALUATION_ACCESS=key`). Create the
operator launch key that the smoke UI and `curl` requests will present, and store it
the same way:

```bash
uv run roborouter-launch-credentials create \
  --role operator \
  --label smoke-operator \
  --ttl-days 30
uv run roborouter-launch-credentials list
```

Per-user keys for invited testers use `--role user` with explicit
`--concurrent-limit` and `--daily-limit`; `revoke <credential-id>` cancels that key's
in-flight jobs. `MAX_ACTIVE_EVALUATIONS=1` keeps the single smoke worker from ever
holding a backlog.

Verify only loopback listeners exist:

```bash
ss -lnt | grep -E ':(5432|9000|9001) '
docker compose -f infra/compose.yml ps
```

### 5. Build the web app for the same-origin API route

The Caddy topology below serves the UI and `/v0` API from `APP_DOMAIN`, avoiding
cross-origin browser credentials.

```bash
cd /opt/roborouter
NEXT_PUBLIC_API_BASE_URL="https://<APP_DOMAIN>" \
NEXT_PUBLIC_SITE_URL="https://<APP_DOMAIN>" \
npm run build
```

### 6. Run API and web as services

Install the reviewed systemd templates:

```bash
sudo install -d -m 0750 -o root -g roborouter /etc/roborouter
sudo install -m 0644 infra/systemd/roborouter-api.service /etc/systemd/system/
sudo install -m 0644 infra/systemd/roborouter-web.service /etc/systemd/system/
sudo install -m 0640 -o root -g roborouter .env /etc/roborouter/control-plane.env
sudo systemctl daemon-reload
sudo systemctl enable --now roborouter-api roborouter-web
sudo systemctl status roborouter-api roborouter-web --no-pager
```

Run both as an unprivileged `roborouter` service account, set `Restart=on-failure`,
and use `UMask=0077`. The checked-in units also enable basic systemd filesystem and
privilege hardening. Never put a worker token directly in a unit file.

Check locally before adding TLS:

```bash
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:3000/
```

### 7. Terminate TLS with Caddy

Caddy obtains and renews certificates automatically when DNS points to the host and
ports 80/443 are reachable. See https://caddyserver.com/docs/quick-starts/reverse-proxy.

Generate the operator password hash with `caddy hash-password`. Install the reviewed
[`../../infra/caddy/Caddyfile.example`](../../infra/caddy/Caddyfile.example) and give
the Caddy service a protected environment file:

```bash
sudo install -m 0644 infra/caddy/Caddyfile.example /etc/caddy/Caddyfile
sudo install -m 0640 -o root -g caddy /dev/null /etc/roborouter/caddy.env
sudoedit /etc/roborouter/caddy.env
sudo systemctl edit caddy
```

The Caddy environment file must define `APP_DOMAIN`, `WORKER_DOMAIN`,
`ARTIFACT_DOMAIN`, `OPERATOR_USERNAME`, and `OPERATOR_PASSWORD_HASH`. The systemd
override created by `systemctl edit caddy` must contain:

```ini
[Service]
EnvironmentFile=/etc/roborouter/caddy.env
```

Validate and reload:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' \
  https://<WORKER_DOMAIN>/v0/evaluations/not-a-real-id
```

The last request should reach FastAPI and return its JSON 404, proving TLS routing.
Confirm an unrelated path on `WORKER_DOMAIN` returns Caddy's 404. Confirm
`APP_DOMAIN` challenges for the operator password.

## Phase 2 — NVIDIA Linux worker

### 1. Select and inspect the machine

For the first reproduction, match the upstream evidence as closely as practical: an
H100 80 GB worker is the lowest-ambiguity choice. Reserve at least 150 GB of free
disk for the two checkpoints, Python environments, Docker image, and retained
artifacts. Record provider, instance type, region, GPU, disk, OS image, and hourly
cost before launch.

Use a provider NVIDIA image with the driver already installed when available. Verify:

```bash
nvidia-smi
uname -a
lsb_release -a
df -h
```

### 2. Install Docker and the NVIDIA container runtime

Install Docker from the official repository. Then install/configure NVIDIA Container
Toolkit following
https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html:

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker info
```

Run NVIDIA's documented sample GPU container for the installed driver/CUDA range.
The `nvidia-smi` output inside the container must show the same GPU and driver.

### 3. Clone exact source revisions

```bash
sudo install -d -o "$USER" -g "$USER" /opt/roborouter
git clone git@github.com:richik-p/roborouter.git /opt/roborouter
cd /opt/roborouter
git checkout <CONTROL_PLANE_COMMIT>

git clone --branch v0.4.0 --depth 1 \
  https://github.com/allenai/vla-evaluation-harness.git \
  vendor/vla-evaluation-harness
git -C vendor/vla-evaluation-harness rev-parse HEAD
git -C vendor/vla-evaluation-harness status --short
```

Required harness commit:
`2680ab2fafe981c2dba63c6c1a4e7bb4415dbb56`. The status must be empty; the worker
refuses a different or dirty checkout.

Install both workspaces:

```bash
uv sync --all-packages --dev --frozen
cd vendor/vla-evaluation-harness
uv sync --python 3.11 --all-extras --dev
cd /opt/roborouter
```

Ensure the harness executable is visible to the worker:

```bash
export PATH="/opt/roborouter/vendor/vla-evaluation-harness/.venv/bin:$PATH"
vla-eval --help
```

### 4. Pull the exact benchmark image

```bash
docker pull \
  ghcr.io/allenai/vla-evaluation-harness/libero@sha256:2a4566009395888ae3904bde87cffceea7526e2e0f0667b933cae0e8e6134413
docker image inspect \
  ghcr.io/allenai/vla-evaluation-harness/libero@sha256:2a4566009395888ae3904bde87cffceea7526e2e0f0667b933cae0e8e6134413
```

Record the resolved image ID and architecture. Do not substitute `latest`.

### 5. Run upstream checks before RoboRouter

Use the pinned harness's documented `vla-eval test`/health workflow. Start π₀.₅ with
`configs/model_servers/lerobot/pi05_libero.yaml`, wait for its health endpoint, and
run the LIBERO smoke configuration. Preserve raw output under a dated evidence
directory outside the Git worktree. Stop here if the upstream path fails; RoboRouter
cannot make a broken upstream runtime valid.

### 6. Configure the outbound worker

Create `/opt/roborouter/.env.worker`, mode `0600`:

```dotenv
API_BASE_URL=https://<WORKER_DOMAIN>
WORKER_TOKEN=<rrw_... token printed once by the control-plane credential command>
WORKER_ID=gpu-worker-01
GPU_NAME=<exact nvidia-smi name>
VRAM_GB=<integer GiB>
VLA_EVAL_ROOT=/opt/roborouter/vendor/vla-evaluation-harness
WORKER_OUTPUT_ROOT=/var/lib/roborouter-worker/artifacts
POLL_SECONDS=5
HEARTBEAT_SECONDS=25
```

Start once in the foreground:

```bash
cd /opt/roborouter
set -a
. ./.env.worker
set +a
export PATH="/opt/roborouter/vendor/vla-evaluation-harness/.venv/bin:$PATH"
uv run roborouter-worker
```

Confirm registration in control-plane logs. Then install the same command as an
unprivileged systemd service using the checked-in template:

```bash
sudo install -d -m 0750 -o root -g roborouter-worker /etc/roborouter
sudo install -m 0640 -o root -g roborouter-worker .env.worker /etc/roborouter/worker.env
sudo install -m 0644 infra/systemd/roborouter-worker.service /etc/systemd/system/
sudo install -d -m 0750 -o roborouter-worker -g roborouter-worker /var/lib/roborouter-worker
sudo systemctl daemon-reload
sudo systemctl enable --now roborouter-worker
sudo systemctl status roborouter-worker --no-pager
```

The worker needs outbound TCP 443 and registry/model-download access; it needs no
inbound application port.

## Phase 3 — one π₀.₅/LIBERO Object episode

### 1. Create the job

Use the password-protected web policy page (paste the launch key into its
**Access key** field), or make the exact same request while letting `curl` prompt
for the operator password:

```bash
curl --user <OPERATOR_USERNAME> \
  --header 'Authorization: Bearer <LAUNCH_KEY>' \
  --header 'Content-Type: application/json' \
  --data '{
    "policy_id":"pi05-libero",
    "policy_revision":"lerobot-pi05-libero-finetuned",
    "environment_id":"vla-eval-libero-object",
    "environment_revision":"vla-eval-0.4.0-lerobot-0.6.0-libero-2a4566009395",
    "task_profile_id":"libero-object-pick-place",
    "task_revision":"2026-08-20.1",
    "seeds":[7]
  }' \
  https://<APP_DOMAIN>/v0/evaluations
```

Save the returned evaluation ID. Observe `QUEUED → CLAIMED → RUNNING → SUCCEEDED`.
If cancellation is necessary:

```bash
curl --user <OPERATOR_USERNAME> --request POST \
  --header 'Authorization: Bearer <LAUNCH_KEY>' \
  https://<APP_DOMAIN>/v0/evaluations/<EVALUATION_ID>/cancel
```

Cancellation must stop lease renewal and terminate the local harness subprocess. It
must not create a successful Rollout.

### 2. Verify evidence

- One Rollout exists for seed `7`.
- `runtime_identity` contains harness commit, LeRobot tag, model commit, and container
  digest.
- At least the log/config artifacts exist; recordings/traces are retained when the
  harness emits them.
- Every API artifact ID, byte count, media type, and SHA-256 matches the private
  object.
- Replaying the identical completion changes neither Rollout count nor artifact IDs.
- A robot-task failure is `SUCCEEDED` infrastructure with `success=false`; only
  infrastructure/runtime failures set the job to `FAILED`.

Complete the evidence record in `docs/plans/remote-evaluation.md` before marking
M0-03 or M2-03 complete.

## Phase 4 — matched π₀.₅ versus MolmoAct2

Use the same worker class and these identities for both jobs:

```text
Environment: vla-eval-libero-goal
Revision:    vla-eval-0.4.0-lerobot-0.6.0-libero-2a4566009395
Task:        libero-goal-interaction
Task rev:    2026-08-20.1
Seed list:   [7]
Evaluator:   libero.environment-predicate.v1
Actions:     manipulation.ee_delta_pose.v1
```

Queue π₀.₅, allow it to complete, then queue MolmoAct2. Sequential execution avoids
mixing model memory/resource conditions. Record model-load time separately from
episode duration. A result is matched only if the identities above and the observed
worker class are identical.

The current Compare page can launch both jobs but still needs the result-side-by-side
work described in `docs/plans/security-and-browser-e2e.md`. Until then, query
`GET /v0/rollouts`, select both evaluation IDs, and compare metrics/artifacts without
calling the UI a finished leaderboard.

## Shutdown and cost control

After evidence is uploaded and verified:

1. stop the worker service;
2. confirm no evaluation remains `CLAIMED` or `RUNNING`;
3. preserve the evidence record and hashes;
4. terminate the billable GPU instance rather than merely logging out;
5. rotate/revoke the smoke worker token and the smoke launch key;
6. keep PostgreSQL/MinIO backups before changing revisions.
