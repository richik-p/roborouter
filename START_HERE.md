# Start Here

This file is the human operator checklist before handing RoboRouter to Codex.

## 1. What is already decided

Do not reopen these choices casually during the first build phase:

- RoboRouter is **not limited to robot arms**.
- The product is broad in **discovery and data model**, but narrow in **initial physical execution support**.
- A user starts from their **robot and use case**, not from a raw model name.
- Policy integration and robot/hardware integration are separate layers.
- The canonical runnable object is an **ExecutablePolicySpec**, not just model weights.
- Compatibility must be evidence-backed and graded, not a boolean marketing badge.
- Simulation/replay is the no-hardware acquisition path.
- The first physical pilot uses an **external collaborator's existing working robot**.
- Shadow mode precedes real actuation.
- The robot-side runtime is the physical safety authority.
- Use XPolicyLab/LeRobot/ROS2/PX4 where they solve existing layers; do not rebuild them for branding.
- Do not invent a new universal network protocol for the MVP.
- Do not add billing, a marketplace, Kubernetes, creator payouts, or sophisticated GPU multiplexing before product usage justifies them.

See [`docs/DECISIONS.md`](docs/DECISIONS.md).

## 2. Put this folder into a GitHub repository

Recommended repository name:

```text
roborouter
```

Keep all documentation committed from day one. These files are the persistent product context for coding agents and human collaborators.

## 3. Before asking Codex to implement

Open the repository in Codex and paste the prompt in [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md).

The **first Codex pass should not implement the product**. It should:

1. read all source-of-truth documents;
2. identify contradictions or missing decisions;
3. inspect the current upstream libraries named in the research notes;
4. propose an implementation structure;
5. convert `docs/ROADMAP.md` into scoped GitHub issues/milestones;
6. identify the smallest end-to-end vertical slice;
7. report back before large implementation begins.

This avoids building a polished version of the wrong architecture.

## 4. Your parallel human task: find one pilot robot

While the first software milestones are being built, find **one connection with an existing working robot**.

Best pilot characteristics:

- already controllable programmatically;
- ROS 2, LeRobot, or a documented vendor SDK is available;
- at least one camera or relevant sensor is available;
- physical e-stop/manual recovery exists;
- an existing policy or scripted controller already works;
- the owner is willing to supervise a short integration session;
- an Ubuntu/Linux companion machine is available if possible.

Ask only for:

```text
Robot model:
Middleware/interface: ROS 2 / LeRobot / PX4 / vendor SDK / other
Sensors/cameras:
Current working policy/controller:
Compute attached to robot:
Remote access constraints:
```

Do **not** require the collaborator to fine-tune π0.5 or GR00T for the first pilot.

## 5. The first three proofs

### Proof A — Catalog

A stranger can search for something like:

> “language-conditioned single-arm pick-and-place”

or

> “UAV language navigation”

and get a small, understandable, evidence-qualified set of model options.

### Proof B — No-hardware evaluation

A stranger can compare two policies in a supported simulator and receive:

- rollout videos;
- result metrics;
- exact policy/runtime identity;
- a saved Rollout page.

### Proof C — External robot

A collaborator can connect a robot, run diagnostics, execute a known-good policy in shadow mode, then perform one supervised physical task through RoboRouter.

If these three work, the project is real enough to show publicly.

## 6. What not to optimize yet

Ignore early temptation to optimize:

- GPU gross margin;
- automatic model-quality routing;
- hundreds of models;
- dozens of hardware vendors;
- production enterprise SSO;
- training orchestration;
- multi-LoRA serving;
- global edge routing;
- billing.

The first question is whether people want the compatibility/discovery/evaluation/execution workflow.

## 7. Definition of “ready to invite users”

Invite external users when all of these are true:

- at least 20 curated policies have useful metadata;
- at least 2 model families can be evaluated through the same UX;
- at least 1 non-manipulation domain is represented in discovery and simulation, ideally UAV;
- Rollout pages are reproducible enough to debug results;
- one external robot integration works in shadow mode;
- real actuation requires explicit local arming;
- the website has a visible **Become a pilot** call to action;
- the project clearly labels simulated, real-world, fine-tune-required, and unverified compatibility differently.
