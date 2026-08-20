# External Robot Pilot Plan

## Objective

Validate that RoboRouter can integrate with a robot someone already uses **without requiring us to own or mechanically set up the robot**.

The first pilot is an integration/product test, not a frontier model-performance study.

## Ideal first pilot

Prefer a robot with:

- existing programmatic control;
- existing working task/policy/controller;
- ROS 2, LeRobot, or a documented SDK;
- one or more camera/sensor streams;
- physical e-stop/manual recovery;
- Linux companion machine;
- an owner/operator who can supervise.

Good examples could include a research arm, mobile manipulator, or another stable lab platform.

Avoid making the first pilot a drone unless the collaborator already has a mature safe offboard-control workflow; aerial systems add substantially higher physical-risk and testing overhead.

## Information to request from a candidate

```text
Robot model:
Robot class:
Middleware/interface:
Operating system:
Sensors/cameras:
State topics/APIs:
Command/control interfaces:
Control frequency:
Existing working policy/controller:
Existing simulator/digital twin, if any:
On-robot/near-robot compute:
Network restrictions:
Hardware e-stop/manual override:
Times when supervised testing is possible:
```

## Pilot phases

### Phase 0 — documentation-only

Build a RobotProfile from their existing setup. No software installed.

Deliverable:

- profile reviewed by robot owner;
- known control surface identified;
- one existing policy/controller mapped conceptually.

### Phase 1 — read-only agent

Install `rr-agent` in diagnostic/read-only mode.

It may inspect:

- available middleware;
- sensors;
- state interfaces;
- command interfaces;
- metadata needed to propose the RobotProfile.

It must not actuate.

### Phase 2 — observation streaming

Stream real observations/state to RoboRouter while the robot remains under the owner's normal control or stationary.

Validate:

- timestamps;
- camera mapping;
- state dimensions/units;
- latency;
- network behavior.

### Phase 3 — shadow policy

Run the **existing known-good policy** or another already-compatible policy through the RoboRouter execution path but record actions only.

Compare against the owner's baseline output if possible.

### Phase 4 — local dry-run validation

Before torque/motion enable:

- validate action schema;
- validate units/frames;
- validate limits;
- confirm watchdog/hold path;
- confirm e-stop/manual recovery;
- verify fault/reconnect behavior.

### Phase 5 — supervised actuation

Operator explicitly arms/enables actuation locally.

Run one short, low-risk known task.

Record a Rollout.

### Phase 6 — second policy

Only after the pipeline itself is trusted, compare or integrate another policy family.

## Pilot success criteria

- collaborator does not need to rewrite their hardware stack;
- `rr-agent` can represent the robot accurately;
- shadow mode works reliably;
- a known-good action path survives RoboRouter unchanged enough to execute the known task;
- the Rollout is useful for debugging;
- collaborator says they would use RoboRouter to try another model.

## Outreach message

Use a short, concrete pitch rather than selling a grand platform:

> I'm building RoboRouter, a developer layer for finding and comparing robot policies and running them through existing robot stacks. I'm looking for 3–5 pilot robots. I don't need you to change your hardware setup or train a new model—the first test is to wrap a robot/policy you already know works, run it in shadow mode, and see whether the compatibility + rollout tooling is actually useful. If you have a ROS2, LeRobot, or SDK-controlled robot and are open to a supervised integration session, I'd love to try it with your setup.

## What we offer the pilot

- free integration help;
- a structured RobotProfile;
- model-compatibility report;
- reproducible Rollout/trace tooling;
- early access to comparison/evaluation features;
- public attribution only if they want it.

## What we do not ask for initially

- proprietary training data;
- full raw rollout logging by default;
- cloud control without supervision;
- changing safety systems;
- replacing their controller/middleware;
- buying hardware;
- fine-tuning a frontier model.
