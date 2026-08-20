# Core Data Model

This document describes product semantics. It is not yet a frozen database schema.

## Design rules

- Core objects are versioned.
- Execution-critical identity is immutable at a given revision.
- Compatibility stores evidence, not just derived booleans.
- Robot-specific low-level semantics stay explicit.
- Unknown fields should remain unknown rather than inferred aggressively.

---

# 1. RobotProfile

Describes a robot instance or reusable robot configuration as exposed to RoboRouter.

Example:

```yaml
id: lab/franka-3
revision: 1
robot_class: manipulator.single_arm
manufacturer: Franka
model: Panda

middleware:
  type: ros2

sensors:
  - id: scene
    type: vision.rgb
    resolution: [1280, 720]
    rate_hz: 30
  - id: wrist
    type: vision.rgb
    resolution: [640, 480]
    rate_hz: 30
  - id: joints
    type: proprioception.joint_position
    dimensions: 7

control_surfaces:
  - schema: manipulation.joint_position.v1
    dimensions: 8
    rate_hz: 20
  - schema: manipulation.ee_delta_pose.v1
    rate_hz: 20

safety_capabilities:
  hardware_estop: true
  local_limits: true
```

For a UAV:

```yaml
robot_class: aerial.multirotor
middleware:
  type: px4_ros2

sensors:
  - {id: front, type: vision.rgb}
  - {id: imu, type: inertial.imu}
  - {id: gps, type: navigation.gnss}

control_surfaces:
  - schema: aerial.position_setpoint.v1
  - schema: aerial.body_velocity.v1
```

## Important fields

- identity/manufacturer/model;
- robot class;
- middleware/adapter family;
- sensors;
- state channels;
- control surfaces;
- local control rates;
- safety capabilities;
- environment constraints;
- evidence/provenance for autodetected fields.

---

# 2. TaskProfile

Describes desired behavior independently of any one policy.

```yaml
domain: manipulation
task_family: pick_and_place

requirements:
  language_conditioned: true
  object_generalization: true

inputs_expected:
  human_prompt: true

environment:
  workspace: tabletop

constraints:
  max_episode_s: 45
```

Aerial example:

```yaml
domain: aerial_navigation
task_family: language_goal_navigation
requirements:
  obstacle_avoidance: true
  landing: true
```

TaskProfiles power search and compatibility, but should not imply that model capability is proven unless evidence exists.

---

# 3. ExecutablePolicySpec

The exact runnable policy identity.

```yaml
id: physical-intelligence/pi05-droid
revision: <immutable-content-or-source-revision>
family: pi0.5
role: policy

source:
  repo: ...
  checkpoint: ...

runtime:
  adapter: xpolicylab | lerobot | openpi_native | other
  framework: ...
  engine_revision: ...

observations:
  cameras:
    - semantic_name: scene
      transform: ...
    - semantic_name: wrist
      transform: ...
  state_schema: ...

preprocessing:
  image_pipeline_revision: ...
  prompt_pipeline_revision: ...

normalization:
  state_stats_id: ...
  action_stats_id: ...

actions:
  schema: manipulation.ee_delta_pose.v1
  horizon: ...
  dimensions: ...
  gripper_convention: ...

control:
  expected_rate_hz: ...
  chunk_execution: ...

availability:
  weights: open | gated | closed
  code: open | closed

license:
  identifier: ...
  notes: ...
```

## Why this exists

Two deployments with the same named weights may not be physically equivalent if preprocessing, normalization, decoding, controller mapping, or runtime semantics differ.

RoboRouter should make exact execution identity reproducible.

---

# 4. CompatibilityRecord

A relation between:

```text
ExecutablePolicySpec
+ RobotProfile
+ TaskProfile
+ optional bridge
+ evaluation/execution context
```

Example:

```yaml
status: FINE_TUNE_REQUIRED
reason_codes:
  - NO_MATCHING_CHECKPOINT_FOR_ROBOT

policy_id: ...
robot_profile_id: ...
task_profile_id: ...

requirements:
  sensors: satisfied
  action_surface: structurally_supported
  checkpoint: missing

best_available_evidence:
  level: SIM_VERIFIED_OTHER_EMBODIMENT
  source: ...
  checked_at: 2026-08-19

supported_paths:
  simulate: true
  shadow: false
  actuate: false
```

## Recommended status vocabulary

- `NATIVE_REAL_VERIFIED`
- `BRIDGED_REAL_VERIFIED`
- `SIM_VERIFIED`
- `FINE_TUNE_REQUIRED`
- `RESEARCH_ONLY`
- `UNKNOWN`
- `INCOMPATIBLE`

The enum may evolve, but evidence must remain first-class.

---

# 5. Rollout

A Rollout records one episode/evaluation execution.

```yaml
id: rr_rollout_...
mode: sim | shadow | actuate

policy_spec_id: ...
robot_profile_id: ...
task_profile_id: ...
compatibility_record_id: ...

environment:
  id: ...
  revision: ...
  seed: ...

timing:
  started_at: ...
  duration_ms: ...
  inference_latency_ms: ...

artifacts:
  video: ...
  observation_trace: ...
  predicted_action_trace: ...
  executed_action_trace: ...

safety:
  rejected_actions: 0
  clamps: 0
  fault_events: []

outcome:
  success: true
  metrics: {...}
  evaluator: ...
```

A Rollout is useful even when no physical robot exists.

---

# 6. ControlSurface

A versioned semantic command interface.

Do not treat schemas below as final, but preserve the pattern:

```text
manipulation.joint_position.v1
manipulation.joint_velocity.v1
manipulation.ee_absolute_pose.v1
manipulation.ee_delta_pose.v1
mobile.base_velocity.v1
aerial.position_setpoint.v1
aerial.body_velocity.v1
```

Each schema should define:

- coordinate/reference frame;
- dimensions/fields;
- units;
- valid rate range;
- timestamp/TTL semantics where relevant;
- safety-relevant limits that the local runtime may impose.

---

# 7. BridgeSpec

A bridge is an explicit transformation between compatible semantic interfaces, for example:

```text
policy EE delta pose
        ↓
validated IK/controller bridge
        ↓
robot joint position surface
```

A bridge must not exist only as undocumented glue code. Store:

- input/output schemas;
- version;
- assumptions;
- robot applicability;
- evidence;
- safety constraints.

---

# 8. Evidence

Compatibility and performance claims should point to structured evidence:

- upstream documentation;
- upstream model card;
- reproducible simulator evaluation;
- external real-robot demo;
- RoboRouter shadow rollout;
- RoboRouter physical rollout;
- third-party benchmark result.

Record:

- source;
- date checked;
- exact revisions where possible;
- whether evidence is simulation or physical;
- whether it matches the exact robot profile or only a related embodiment.
