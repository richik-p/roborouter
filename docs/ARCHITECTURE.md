# Architecture

## Design goal

Support many policy families and many robot classes without creating a separate bespoke integration for every pair.

The architecture should remain small enough for one or two engineers during MVP.

## Conceptual layers

```text
                         ┌──────────────────────┐
                         │      Web / CLI       │
                         │ discover / compare   │
                         │ eval / connect       │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │    Control Plane     │
                         │                      │
                         │ Catalog              │
                         │ RobotProfiles        │
                         │ TaskProfiles         │
                         │ Compatibility        │
                         │ Eval jobs            │
                         │ Sessions             │
                         │ Rollouts             │
                         └──────┬────────┬──────┘
                                │        │
                    simulation  │        │ execution assignment
                                │        │
                    ┌───────────▼─┐   ┌──▼────────────────┐
                    │ Eval Worker │   │ Policy Runner      │
                    │             │   │                    │
                    │ simulator   │   │ PolicyAdapter      │
                    │ + policy    │   │ XPolicyLab/native  │
                    └─────────────┘   └─────────┬──────────┘
                                               │
                                        semantic action data
                                               │
                                  outbound secure connection
                                               │
                                    ┌──────────▼─────────┐
                                    │      rr-agent      │
                                    │                    │
                                    │ RobotAdapter       │
                                    │ local action queue │
                                    │ local safety       │
                                    │ diagnostics        │
                                    └──────────┬─────────┘
                                               │
                                             ROBOT
```

## Deployment philosophy

Do not split this into many microservices for the MVP.

A reasonable first implementation may consist of:

1. **web app**;
2. **API/control-plane app**;
3. **GPU/eval worker runtime**;
4. **rr-agent** package/process.

PostgreSQL is the authoritative structured store. Object storage holds videos/artifacts. Add other infrastructure only when measurements justify it.

## Control plane responsibilities

- policy catalog;
- robot/task profiles;
- compatibility computation;
- evidence/provenance;
- evaluation job lifecycle;
- session metadata;
- runner assignment;
- Rollout metadata/indexing;
- authentication later when needed.

The control plane should not sit in a high-frequency physical control loop if avoidable.

## Policy runner responsibilities

A PolicyRunner hosts one or more `PolicyAdapter` implementations.

### PolicyAdapter contract (semantic, not transport-specific)

Conceptually:

```text
load(ExecutablePolicySpec)
reset(context)
infer(Observation) -> ActionChunk | Action
health()
metadata()
```

Exact language/API may evolve.

### Initial adapter strategy

Prefer:

1. XPolicyLab adapter/runtime where it cleanly supports the policy;
2. LeRobot policy interface where convenient;
3. model-native adapter for important gaps.

Do not make RoboRouter's value depend on owning every policy implementation.

## Robot-side architecture

`rr-agent` runs near the robot and owns `RobotAdapter` plus local safety enforcement.

### RobotAdapter contract

Conceptually:

```text
connect()
inspect_capabilities() -> RobotProfile
observe() -> Observation
validate_action(action)
execute(action)
hold()
disarm()
```

Actual adapters may be async or streaming.

### Initial integration families

#### LeRobot

Use the LeRobot `Robot` abstraction when a robot already fits that ecosystem.

#### ROS 2 / ros2_control

Use ROS2 introspection/topics/services/actions/control interfaces rather than creating vendor-specific integrations where an adequate ROS control layer already exists.

#### PX4 + ROS 2

For UAVs, RoboRouter should operate on **high-level control surfaces** (e.g. position/velocity/mission targets) while PX4 retains stabilization, actuator control, failsafe, and other flight-critical loops.

#### Vendor SDK

A thin adapter is acceptable when no common middleware exists, provided the same `RobotProfile/control_surface` semantics are preserved.

## Typed control surfaces

Do not expose one universal low-level robot action type.

Examples:

```text
manipulation.joint_position.v1
manipulation.joint_velocity.v1
manipulation.ee_delta_pose.v1
manipulation.ee_absolute_pose.v1
mobile.base_velocity.v1
aerial.position_setpoint.v1
aerial.body_velocity.v1
```

A policy can be connected to a robot only when:

- the policy output schema matches a robot control surface; or
- a validated deterministic bridge exists and is recorded in the CompatibilityRecord.

## Compatibility engine

Initial implementation should be deterministic/rule-based.

Inputs:

```text
RobotProfile + TaskProfile + ExecutablePolicySpec
```

Checks may include:

- robot class/embodiment constraints;
- required sensors;
- camera count/semantic mapping;
- state keys/dimensions;
- control surface/action schema;
- control rate envelope;
- checkpoint/normalization identity;
- required bridge;
- runtime availability;
- evidence level;
- task capability tags;
- fine-tune requirement.

Output:

```text
CompatibilityRecord
```

Do not hide a missing field by guessing.

## Evaluation path

For simulation, colocating policy and simulator may be preferable to exercising the exact remote network path. The product should record which execution path was used.

A generic evaluation flow:

```text
POST eval
  ↓
resolve policy + environment + task revisions
  ↓
provision worker
  ↓
execute deterministic/seeded episodes where supported
  ↓
store metrics + video + traces
  ↓
create Rollout(s)
  ↓
render result/compare page
```

## Physical execution modes

### Shadow

Observations flow through the real policy path, predicted actions are recorded, **but rr-agent does not actuate**.

### Actuate

Requires explicit local enable/arming. `rr-agent` validates every command against local safety policy before sending it to the hardware/middleware.

### Fault behavior

After serious communication/runtime failure, default to local safe behavior. Do not automatically resume physical motion merely because cloud compute recovered.

Explicit re-arm may be required based on the robot class and fault severity.

## Transport strategy

Do not define the product around one wire transport.

The semantic session should support observations, actions/chunks, acknowledgements, timing, queue state, hold/fault state, and reset/session lifecycle.

Possible transports:

- WebSocket for early remote compatibility;
- framework-native communication where appropriate;
- shared memory for colocated evaluation;
- gRPC/ROS-native integration where useful;
- lower-jitter transports later if measurements justify them.

## Observability

Each Rollout should capture enough data to answer:

- what did the policy see?
- what exact policy/runtime was used?
- what did it predict?
- what was actually executed?
- how late were predictions?
- were actions clamped/rejected?
- what outcome/evaluator result occurred?

This observability is a primary product feature, not merely infrastructure logging.

## Security direction

During MVP:

- external robot connections should be outbound-initiated where possible;
- do not execute arbitrary uploaded Python in trusted runners;
- avoid unsafe checkpoint deserialization paths;
- use versioned/authenticated session identities before external actuation;
- do not persist raw robot observations by default without explicit product policy/consent;
- record whether a session is simulation, shadow, or actuation.

See `docs/SAFETY.md`.
