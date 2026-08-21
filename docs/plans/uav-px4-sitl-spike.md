# UAV/PX4-SITL reproducibility spike

## Objective

Prove the existing catalog, compatibility, evaluation, and Rollout contracts can
represent an aerial policy without reusing manipulation actions. This milestone is
simulation-only and adds no physical-actuation path.

PX4's current simulation overview and ROS 2 bridge documentation are the upstream
starting points:

- https://docs.px4.io/main/en/simulation/
- https://docs.px4.io/main/en/middleware/uxrce_dds

## Phase 1 — pin a reproducible simulator boundary

1. Select a stable PX4 release and record both tag and commit; do not build from
   mutable `main`.
2. Record Ubuntu, Gazebo, ROS 2, Micro XRCE-DDS Agent, compiler, and Python versions.
3. Build PX4 SITL with the standard Gazebo x500 target and run the upstream smoke
   flight without RoboRouter.
4. Record container image digests or a reproducible host setup, world/model assets,
   initial pose, weather, estimator parameters, seed behavior, and licenses.
5. Restart from a clean environment three times. Stop the spike if initial state or
   results cannot be made deterministic enough to explain.

Typical upstream development commands are:

```bash
git clone --recursive https://github.com/PX4/PX4-Autopilot.git
cd PX4-Autopilot
git checkout <PINNED_TAG_OR_COMMIT>
bash ./Tools/setup/ubuntu.sh
make px4_sitl gz_x500
```

Treat these as a starting point; the evidence record must contain the exact resolved
versions and commands actually used.

## Phase 2 — define aerial contracts

Create a new revision of the existing PX4-SITL RobotProfile with explicit sensors:

- front RGB camera with semantic name and resolution;
- local position and velocity with frame (`NED` or `ENU`) declared;
- attitude representation and quaternion ordering;
- angular/body rates;
- landed/arming/failsafe state.

Choose exactly one high-level v0 control surface for the spike:

```text
aerial.local_position_yaw.v1
or
aerial.body_velocity_yaw_rate_land.v1
```

Specify dimensions, units, coordinate frame, sign conventions, rate, TTL, saturation,
and the discrete landing/hold semantics. Do not reuse
`manipulation.ee_delta_pose.v1`, and do not expose motors, thrust mixing, or raw
actuator controls.

Define:

- an aerial TaskProfile with a bounded language-navigation goal;
- an EvaluationEnvironmentSpec with exact simulator/image/assets/evaluator/seed;
- a BridgeSpec for ROS 2/PX4 messages only if every mapping is explicit;
- compatibility reason codes for missing pose, camera, frame, or action semantics.

Unknown frame, units, or camera identity must produce `UNKNOWN` or `INCOMPATIBLE`,
never a guessed bridge.

## Phase 3 — deterministic echo evaluator

Before AeroVLA, implement an echo/scripted policy that consumes the aerial observation
contract and produces bounded high-level commands. Use it to prove:

- job claim/lease/cancellation works with a non-LIBERO environment;
- observation and predicted-action traces persist as aerial Rollouts;
- task failure is separate from infrastructure failure;
- resetting the same seed restores the same start state;
- timeout or network loss commands local hold/land behavior in simulation.

Run stale-command, frame mismatch, missing-camera, and cancellation tests. No cloud
reconnect may automatically resume a simulated motion command.

## Phase 4 — AeroVLA feasibility gate

Only after the echo path passes:

1. pin the AeroVLA repository, weights, dataset/assets, and TravelUAV/PX4 integration
   revisions;
2. verify the released policy output semantics against the selected high-level
   control surface;
3. document every transform between policy outputs, world/body frames, and PX4
   commands;
4. run the model-native example before adding a RoboRouter adapter;
5. reject the integration if weights/assets/licenses or command semantics cannot be
   reproduced without private assumptions.

## Acceptance

- one aerial simulation Rollout is stored through the same public Rollout contract;
- runtime identity contains all simulator, bridge, policy, and asset revisions;
- the UI labels the result simulation-only and research-only where applicable;
- manipulation and aerial golden tests coexist without shared action schemas;
- `supported_paths.actuate` remains false;
- `agents/rr-agent` contains no UAV actuation implementation.

## Non-goals

No real aircraft, arming, offboard physical control, autonomous takeoff, raw motor
commands, or physical safety claims belong in this spike.
