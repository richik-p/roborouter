# RoboRouter

> **Find, evaluate, and run models for your robot.**

RoboRouter is an early-stage developer platform for discovering robot policies, checking whether they are actually compatible with a specific robot and task, comparing them in simulation or replay, and eventually running them through local or remote compute without forcing users to learn each model family's serving stack.

This repository is intentionally **not an SO-101-only or arm-only project**. The product model is designed to extend across single arms, bimanual systems, dexterous hands, mobile manipulators, humanoids, drones/UAVs, rovers, quadrupeds, and future embodiments by separating policy integration from hardware integration.

## Why this exists

Robot foundation-model development is fragmenting quickly. A user may want to try π0.5, GR00T N1.7, SmolVLA, MolmoAct2, a task-specific diffusion policy, a dexterous-hand model, or an aerial VLA, but “the weights are available” does not mean “this model can safely run on my robot.”

Compatibility depends on more than a model name:

- robot embodiment and degrees of freedom;
- available sensors and camera names/configuration;
- state representation;
- action representation and controller semantics;
- preprocessing and normalization/unnormalization;
- control frequency and action-chunk semantics;
- runtime/framework dependencies;
- exact checkpoint revision;
- evidence that the combination has been tested in simulation or on physical hardware.

RoboRouter makes those dependencies explicit rather than hiding them behind a generic `model=` string.

## Product thesis

The product revolves around five objects:

1. **RobotProfile** — what hardware, sensors, middleware, and safe control surfaces exist.
2. **TaskProfile** — what the user is trying to accomplish.
3. **ExecutablePolicySpec** — the exact runnable policy identity, including the transformations around the weights.
4. **CompatibilityRecord** — the evidence-backed relationship between a policy, robot, task, and execution path.
5. **Rollout** — a reproducible record of what happened during simulation, shadow execution, or physical execution.

The initial user experience should be closer to:

> “I have this robot and this task. What can I use?”

than:

> “Here are 400 robotics models.”

## MVP

The first credible public MVP should demonstrate all three of these experiences:

### 1. Discovery

A technical user can filter a curated catalog by:

- robot class;
- task;
- model role;
- required sensors;
- action/control surface;
- language conditioning;
- zero-shot vs fine-tune required;
- simulation vs physical evidence;
- open weights/code/API availability;
- compute requirements;
- license.

### 2. Evaluation without owning a robot

A user can choose compatible policies and run the same task in a supported simulator/evaluation environment, producing comparable videos, metrics, exact revisions, and Rollout objects.

### 3. One external physical-robot pilot

A collaborator installs a lightweight local `rr-agent`, runs a compatibility/diagnostic check, streams observations to a policy runner in **shadow mode**, and then—after local arming and safety checks—executes one known-working policy through RoboRouter.

The first physical pilot should use a robot that already has a working programmatic control interface and at least one known-good policy. The purpose is to validate RoboRouter, not simultaneously prove novel model transfer.

## Architecture in one picture

```text
                         ┌──────────────────────┐
                         │      Web App         │
                         │ Discover / Compare   │
                         │ Robots / Evals       │
                         │ Rollouts             │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │   Control Plane      │
                         │ Catalog / Profiles   │
                         │ Compatibility        │
                         │ Sessions / Rollouts  │
                         └────┬───────────┬─────┘
                              │           │
                    eval path │           │ execution path
                              │           │
                    ┌─────────▼──┐   ┌────▼──────────────┐
                    │ Sim/Eval   │   │ Policy Runners   │
                    │ Envs       │   │ adapter boundary │
                    └────────────┘   └──────┬────────────┘
                                           │
                                      semantic actions
                                           │
                                    ┌──────▼───────┐
                                    │   rr-agent   │
                                    │ LeRobot      │
                                    │ ROS 2        │
                                    │ PX4          │
                                    │ vendor SDK   │
                                    │ local safety │
                                    └──────┬───────┘
                                           │
                                         ROBOT
```

## Key architectural rule

**Policy adapters and robot adapters are different layers.**

- Policy adapters answer: *How do I run this model?*
- Robot adapters answer: *How do I observe and safely command this machine?*

Do not create one integration for every `(policy × robot)` pair.

## Existing ecosystems to build on

RoboRouter should deliberately integrate with, rather than replace:

- **XPolicyLab** for a large and rapidly growing policy integration/evaluation layer;
- **Hugging Face LeRobot** for robot abstractions, datasets, policies, and bring-your-own-hardware workflows;
- **ROS 2 / ros2_control** for research/industrial robot hardware and control interfaces;
- **PX4 + ROS 2** for high-level drone control while retaining the flight controller as the local real-time/safety authority;
- **RoboDojo / RoboTwin / other benchmark environments** for reproducible evaluation where useful;
- model-native runtimes when the common layer is missing or materially worse.

See [`docs/research/CURRENT_ECOSYSTEM.md`](docs/research/CURRENT_ECOSYSTEM.md).

## What this project is not yet

The MVP is **not**:

- a GPU marketplace;
- a training-as-a-service company;
- an app store with creator payouts;
- a new universal robot wire protocol;
- a universal low-level action tensor;
- a cross-policy mid-episode failover system;
- a cloud safety controller;
- an autonomous fleet-management system.

Those may become future products only after the initial workflow is proven.

## Read this repository in this order

1. [`START_HERE.md`](START_HERE.md)
2. [`docs/PRODUCT.md`](docs/PRODUCT.md)
3. [`docs/MVP.md`](docs/MVP.md)
4. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
5. [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)
6. [`docs/SAFETY.md`](docs/SAFETY.md)
7. [`docs/DECISIONS.md`](docs/DECISIONS.md)
8. [`docs/research/RESEARCH_INDEX.md`](docs/research/RESEARCH_INDEX.md)
9. [`docs/ROADMAP.md`](docs/ROADMAP.md)
10. [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md)

## Status

**Local implementation baseline, with remote execution awaiting GPU verification.**

The repository now includes:

- immutable Pydantic contracts and generated JSON Schema/OpenAPI/TypeScript types;
- a reviewed 22-policy YAML catalog spanning manipulation and UAV research;
- deterministic, ruleset-versioned compatibility checks;
- a FastAPI/SQLAlchemy control plane with PostgreSQL leases, worker authentication,
  idempotent Rollout ingestion, and scoped S3-compatible artifact uploads;
- an outbound-polling evaluation worker for the pinned `vla-eval` boundary;
- a Next.js product UI for Explore, policy detail, evaluation progress, Rollouts,
  comparison, and pilot boundaries;
- a provenance-labeled upstream π₀.₅/LIBERO fixture, usable without CUDA.

No physical-actuation API exists. The `rr-agent` directory is a deferred safety
boundary, not an executable robot controller.

## Local development

Prerequisites are Node.js 22+, Python 3.11, `uv`, and Docker with Compose.

```bash
cp .env.example .env
npm install
uv sync --all-packages --dev
make db-up
```

Then start the API and web app in separate terminals:

```bash
make api
make web
```

Open [http://localhost:3000](http://localhost:3000). Run the complete local
verification suite with `make check`.

With Docker running, verify the real PostgreSQL and MinIO path—including a signed
artifact upload and idempotent completion replay—with:

```bash
make integration-local
```

The NVIDIA worker setup and remaining provenance pins are documented in
[`services/eval-worker/README.md`](services/eval-worker/README.md) and
[`docs/plans/remote-evaluation.md`](docs/plans/remote-evaluation.md).

## Known validation boundary

The deterministic fixture path and the real local PostgreSQL/MinIO integration have
been verified on this workstation. There is no NVIDIA worker or physical robot. The
remote harness, model snapshots, and LIBERO image are pinned, but the first CUDA smoke
episode has not yet been executed.

Research snapshot: **2026-08-20**. Robotics infrastructure is moving rapidly;
current claims should be reverified before major dependency or product decisions.
