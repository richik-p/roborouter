# Safety boundary

**Reconstructed:** 2026-08-20 from the accepted product and architecture
decisions. The original file named by the starter manifest was not present.

## Non-negotiable boundary

The cloud control plane and policy runner are not physical safety controllers.
The robot-side runtime, existing controller, operator, and hardware safety
systems retain authority over motion.

## MVP modes

- `sim`: no physical system is connected.
- `shadow`: real observations may reach a policy, but commands cannot reach an
  actuator. This must be structural, not a UI toggle.
- `actuate`: unavailable before M6. It will require an approved safety ExecPlan,
  explicit local arming, command validation, TTLs, limits, fault latching, and
  supervised recovery.

## Failure behavior

- Network loss, stale actions, invalid units/frames, missed deadlines, or a
  serious runner fault cause the local runtime to hold or enter the robot's
  defined safe behavior.
- Motion never resumes automatically after a serious fault.
- Policy changes occur only at session or episode boundaries.
- UAV integrations use high-level PX4 control surfaces; PX4 retains flight
  stabilization, failsafes, and actuator control.

## Data and code safety

- Do not execute arbitrary uploaded Python or unsafe checkpoint formats in
  trusted workers.
- Authenticate external workers and robot sessions and use outbound-initiated
  connections where possible.
- Simulation artifacts may be retained. Raw physical observations require an
  explicit retention policy and operator consent.
- Every Rollout records its mode, exact execution identity, rejected/clamped
  actions, faults, and whether predicted actions were executed.

