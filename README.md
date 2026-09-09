# RoboRouter

[![CI](https://github.com/richik-p/roborouter/actions/workflows/check.yml/badge.svg)](https://github.com/richik-p/roborouter/actions/workflows/check.yml)

**Evidence-aware discovery and evaluation for robot policies.**

RoboRouter helps robotics developers answer a practical question: _which policy can
actually run on this robot, for this task, through this interface, with defensible
evidence?_

The platform combines a reviewed policy catalog, explicit robot and task profiles,
deterministic compatibility rules, reproducible evaluation jobs, and immutable
Rollout records. It is designed for multiple embodiments—including manipulators,
mobile robots, dexterous hands, and UAVs—without treating every robot as the same
action tensor.

> [!IMPORTANT]
> RoboRouter is pre-beta and currently supports simulation evaluation only. No
> physical-actuation API is included.

## What it provides

- A reviewed catalog of robot-policy families with exact checkpoints, runtime
  requirements, interface contracts, licenses, and evidence provenance.
- Explainable compatibility results for a selected robot, task, and policy,
  including missing requirements and supported execution paths.
- Versioned `RobotProfile`, `TaskProfile`, `ExecutablePolicySpec`,
  `CompatibilityRecord`, and `Rollout` contracts.
- PostgreSQL-backed evaluation jobs with leases, heartbeats, cancellation, and
  idempotent completion.
- Outbound-only evaluation workers with scoped, revocable per-worker credentials.
- Launch keys for evaluation access, closed by default, with per-key concurrency
  and daily quotas plus a global active-job cap.
- S3-compatible storage for hashed videos, traces, logs, and configuration
  snapshots.
- A web interface for policy discovery, compatibility analysis, evaluation status,
  Rollout provenance, and matched policy comparisons.

## Current evaluation boundary

The first executable integration targets the
[AllenAI VLA evaluation harness](https://github.com/allenai/vla-evaluation-harness)
with LIBERO through its LeRobot bridge.

The catalog includes executable specifications for:

- π₀.₅ using `lerobot/pi05_libero_finetuned_v044`;
- MolmoAct2 using `allenai/MolmoAct2-LIBERO`.

The application ships with provenance-labeled upstream fixtures, so discovery,
compatibility, Rollout inspection, and matched comparison flows work locally without
a GPU. Real policy execution requires a separately provisioned NVIDIA Linux worker.

## Architecture

```text
Browser ──► Next.js web app ──► FastAPI control plane ──► PostgreSQL
                                      │
                                      ├──► S3-compatible artifact storage
                                      │
                                      ◄── outbound-polling evaluation worker
                                                   │
                                                   └──► pinned simulator/policy runtime
```

Policy adapters and robot adapters are intentionally separate:

- A policy adapter defines how a specific model revision is loaded and executed.
- A robot adapter defines observations, semantic actions, and local safety controls.

Compatibility is graded and evidence-backed. Missing camera mappings, coordinate
frames, normalization identities, action semantics, or control contracts remain
unknown rather than being inferred.

## Repository layout

```text
apps/web/                 Next.js product interface
services/api/             FastAPI control plane and compatibility engine
services/eval-worker/     Remote evaluation worker and harness adapter
packages/contracts/       Pydantic contracts and generated schemas
catalog/                  Reviewed policy, robot, task, and environment definitions
infra/                    Local and production deployment configuration
docs/                     Architecture, safety, research, and product documentation
```

## Quickstart

Prerequisites:

- Node.js 22 or newer
- Python 3.11
- [`uv`](https://docs.astral.sh/uv/)
- Docker with Compose

```bash
git clone git@github.com:richik-p/roborouter.git
cd roborouter
cp .env.example .env
npm ci
uv sync --all-packages --dev
make db-up
```

Start the API and web application in separate terminals:

```bash
make api
```

```bash
make web
```

Open [http://localhost:3000](http://localhost:3000).

## Validation

Run contracts, API and worker tests, schema generation, linting, type checking,
documentation checks, and the production web build:

```bash
make check
```

Run the browser end-to-end suite:

```bash
npx playwright install chromium
make e2e
```

Verify the complete PostgreSQL and MinIO path, including a signed artifact upload
and idempotent completion replay:

```bash
make integration-local
```

## Safety model

RoboRouter does not silently infer control semantics and does not expose physical
actuation in the current release. A future robot-side runtime must retain local
authority for arming, limits, watchdogs, hold behavior, fault handling, and manual
recovery. Cloud connectivity must never be the final motion-safety boundary.

See [Safety](docs/SAFETY.md) for the complete project policy.

## Documentation

- [Product overview](docs/PRODUCT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Data model](docs/DATA_MODEL.md)
- [Catalog format](docs/CATALOG.md)
- [Safety](docs/SAFETY.md)
- [Roadmap](docs/ROADMAP.md)
- [Contributing](CONTRIBUTING.md)

## Project status

RoboRouter is an active pre-beta project. Local fixture workflows, compatibility
evaluation, worker orchestration, artifact persistence, and browser tests are
implemented. Remote CUDA evaluation and physical-robot integrations require
separate hardware validation and are not represented as completed capabilities.
