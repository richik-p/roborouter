# Current Robotics Infrastructure — Verified Snapshot

**Checked:** 2026-08-20
**Purpose:** identify which layers RoboRouter should reuse rather than rebuild.

This file should be rechecked whenever a major upstream release changes integration strategy.

## 1. AllenAI VLA evaluation harness — first execution boundary

### Verified

Release `v0.4.0` documents a LeRobot model-server bridge, structured benchmark
results, and recordings. Its published integrations include a reproduced
`lerobot/pi05_libero_finetuned` result on LIBERO, giving RoboRouter a bounded first
path that does not require a new universal runtime protocol.

The `v0.4.0` tag resolves to commit
`2680ab2fafe981c2dba63c6c1a4e7bb4415dbb56`. The Hugging Face checkpoint alias now
resolves to `lerobot/pi05_libero_finetuned_v044` at
`8e174154ef5f6c60a8da12ae99c303d8963138c1`; RoboRouter records and enforces that
snapshot rather than loading mutable `main`.

### Product implication

Pin the harness release, LeRobot version, policy and benchmark configuration
revisions, and the exact container digest used by the worker. Preserve upstream
action semantics; the RoboRouter adapter only maps job identity and result artifacts.

### Source

- https://github.com/allenai/vla-evaluation-harness/releases/tag/v0.4.0
- https://huggingface.co/api/models/lerobot/pi05_libero_finetuned
- https://huggingface.co/api/models/allenai/MolmoAct2-LIBERO

---

## 2. XPolicyLab — policy/evaluation layer

### Verified

XPolicyLab describes itself as a unified standard/open ecosystem for robot policy evaluation and deployment. Its repository currently states that it integrates **41 policies** across VLA, world-action, imitation-learning, and memory-augmented families.

It explicitly handles:

- policy environment isolation;
- remote deployment via WebSocket;
- common policy lifecycle/adapter contracts;
- policy-to-benchmark/evaluation wiring;
- integration with RoboDojo and RoboTwin.

It also says arbitrary benchmarks/simulators/real-robot setups can act as environment clients against the same policy-side interface.

### Product implication

**Do not make “write adapters for every VLA” RoboRouter's main engineering burden.**

Use XPolicyLab as an initial policy-side dependency where it is sufficiently stable and compatible. Keep RoboRouter's `PolicyAdapter` boundary so we can use native/LeRobot runtimes where XPolicyLab is missing or unsuitable.

### Source

- https://github.com/XPolicyLab/XPolicyLab

---

## 3. RoboDojo — evaluation infrastructure

### Verified

RoboDojo's current repository describes:

- 42 simulation tasks;
- 18 real-world tasks;
- 3 robot embodiments for real-world evaluation;
- five capability dimensions;
- XPolicyLab as the policy integration/server layer.

It explicitly describes the release as **evaluation-only**, with policy integration owned by XPolicyLab.

### Product implication

RoboDojo is a good example of infrastructure RoboRouter can broker/represent rather than recreate.

Do not make RoboDojo the only simulator/evaluation backend. The RoboRouter data model should support other environments and non-manipulation domains.

### Source

- https://github.com/RoboDojo-Benchmark/RoboDojo

---

## 4. Hugging Face LeRobot — robot/policy/data ecosystem

### Verified

LeRobot's Bring Your Own Hardware documentation defines a standard `Robot` base class for physical robot integration and expects a robot to expose programmatic sensor reads and motor commands through a communication interface/SDK.

LeRobot also has policy integration, training/evaluation, processors, simulation integrations, and a growing hardware ecosystem.

### Product implication

LeRobot should be a first-class `RobotAdapter` family and may also serve policy-side needs.

RoboRouter's value is not to replace LeRobot. It is to make policy/robot compatibility, cross-framework comparison, execution brokerage, and Rollout observability coherent across LeRobot and non-LeRobot systems.

### Sources

- https://huggingface.co/docs/lerobot/integrate_hardware
- https://huggingface.co/docs/lerobot/bring_your_own_policies
- https://huggingface.co/docs/lerobot/

---

## 5. Physical Intelligence openpi — remote inference proof

### Verified

openpi documents remote policy serving explicitly. Its stated motivations include running inference on stronger off-robot GPUs and keeping policy dependencies separated from robot software.

The official flow provides a policy server plus a minimal client embedded in robot code. Images may be resized client-side and proprioceptive state may be sent unnormalized for server-side normalization.

### Product implication

Remote policy/robot separation is not speculative. RoboRouter can reuse or wrap native remote-serving approaches initially rather than forcing all policies through one custom transport.

The important product layer is session identity, compatibility, observability, and runner brokerage above the model-native server.

### Source

- https://github.com/Physical-Intelligence/openpi/blob/main/docs/remote_inference.md

---

## 6. NVIDIA GR00T N1.7

### Verified

NVIDIA's current Isaac-GR00T repository describes GR00T N1.7 as an open cross-embodiment VLA for generalized robot skills, adaptable through post-training to specific embodiments/tasks/environments.

NVIDIA/Hugging Face documentation supports GR00T N1.7 within the current LeRobot ecosystem.

### Product implication

GR00T is an important launch-catalog/model-family candidate, but a base “cross-embodiment” model does not mean every user's robot is immediately executable. RoboRouter should separate model-family relevance from exact checkpoint/control compatibility.

### Sources

- https://github.com/NVIDIA/Isaac-GR00T
- https://huggingface.co/nvidia/GR00T-N1.7-3B
- https://huggingface.co/docs/lerobot/groot

---

## 7. ROS 2 / ros2_control — general robot integration seam

### Verified

ros2_control is a framework for real-time robot control that separates controllers from hardware abstractions and provides hardware interface/component concepts.

### Product implication

For many research/industrial robots, RoboRouter should integrate at an existing ROS2/ros2_control boundary instead of implementing each manufacturer's low-level driver.

`rr-agent` can introspect and bridge supported state/command interfaces into RobotProfiles and typed RoboRouter control surfaces.

### Sources

- https://control.ros.org/
- https://control.ros.org/rolling/doc/ros2_control/hardware_interface/doc/hardware_interface_types_userdoc.html

---

## 8. PX4 + ROS 2 — aerial seam

### Verified

PX4 documents deep ROS2 integration, including offboard control examples and a ROS2 interface library for high-level flight modes/interaction.

### Product implication

RoboRouter should not issue raw motor-level commands from a cloud VLA.

For aerial systems, use high-level control surfaces such as position/velocity/mission commands, with PX4 retaining local flight-critical control and failsafe behavior.

Start with simulation/SITL before physical UAV actuation.

### Sources

- https://docs.px4.io/main/en/ros2/
- https://docs.px4.io/main/en/ros/ros2_offboard_control

---

## 9. AeroVLA — evidence that the catalog must extend beyond arms

### Verified

AeroVLA is an open research repository for end-to-end UAV vision-language navigation. Its project describes dual-view visual input and continuous **3-DoF kinematic commands plus a landing signal**, evaluated on the TravelUAV benchmark.

### Product implication

This is a good early test of whether RobotProfile/TaskProfile/ControlSurface semantics are actually embodiment-general.

Even if the first physical pilot is an arm, the website/evaluation model should be capable of representing an aerial policy without abusing manipulation schemas.

### Source

- https://github.com/XuPeng23/AeroVLA

---

## 10. Codex repository handoff

### Verified

OpenAI's current Codex documentation says Codex reads repository `AGENTS.md` files before doing work and supports layered project-specific instructions. OpenAI also documents an `ExecPlan`/`PLANS.md` pattern for long-running complex implementation tasks.

### Product implication

This repository stores product reasoning as files instead of relying on conversational memory. `AGENTS.md` and `PLANS.md` are deliberate engineering controls.

### Sources

- https://developers.openai.com/codex/agent-configuration/agents-md
- https://developers.openai.com/cookbook/articles/codex_exec_plans

---

# Current conclusion

The useful abstraction boundary is now clearer:

```text
RoboRouter control plane
        ↓
PolicyAdapter (vla-eval / XPolicyLab / LeRobot / native)
        ↓
semantic policy output
        ↓
RobotAdapter (LeRobot / ROS2 / PX4 / SDK)
        ↓
local safety/controller
        ↓
physical robot
```

RoboRouter's initial unique work should focus on:

- catalog/discovery;
- compatibility graph;
- execution identity/provenance;
- evaluation brokerage;
- Rollout observability;
- safe external-robot onboarding.
