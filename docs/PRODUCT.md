# Product Specification

## One-line product

**RoboRouter helps developers find, evaluate, and run compatible robot policies.**

## Problem

Robot-model discovery currently starts from repositories, papers, model cards, Discord posts, framework docs, and hardware-specific tutorials. Even after finding a promising policy, users must determine whether it works with their:

- robot embodiment;
- sensors;
- action/controller interface;
- task;
- data normalization;
- runtime stack;
- compute;
- safety constraints.

A model can be impressive and open-weight while still being unusable on a particular physical system without retraining or a nontrivial adapter.

The user needs an answer to:

> **What can I actually use on the robot I have, for the task I care about, and what evidence supports that answer?**

## Product principles

### 1. Robot/use-case first

The default discovery flow begins with the user's robot and task.

Model-first browsing remains available to researchers who want it.

### 2. Compatibility over marketing

Never collapse:

- “paper claims cross-embodiment,”
- “runs in simulator,”
- “fine-tuning recipe exists,”
- “someone demonstrated this robot,”
- “RoboRouter verified this exact stack”

into one green checkmark.

### 3. Broad catalog, narrow execution

The catalog can represent arms, hands, UAVs, mobile robots, humanoids, quadrupeds, etc. before RoboRouter can physically actuate all of them.

The execution product expands only through validated adapter/control surfaces.

### 4. Local physical authority

The robot-side system owns e-stop, actuator limits, network-loss behavior, flight stabilization, balance, and other embodiment-specific safety functions.

### 5. Interoperate rather than replace

RoboRouter should be the compatibility/discovery/evaluation/execution **control plane above** existing robotics infrastructure where possible.

## Primary users

### Robotics researcher

Has one or more physical platforms. Wants to compare current policies without rebuilding each serving environment.

### Robotics startup engineer

Has an internal robot and policy stack. Wants faster evaluation of external models and a reproducible execution/observability layer.

### Student/hobbyist

May own a low-cost robot or no robot at all. Wants to understand which models are relevant and run them in simulation before buying hardware.

### Model/policy author

Wants their policy to be discoverable, reproducible, and benchmarked on compatible embodiments/tasks.

## Jobs to be done

### Discovery

“When I describe my robot and task, show me the policies worth investigating and explain what work is required.”

### Evaluation

“Let me compare policies under the same task/evaluation setup without manually standing up every repository.”

### Integration

“Tell me exactly why a policy does or does not match my cameras/state/action/controller.”

### Execution

“Run a compatible policy through my existing robot interface without forcing me to rewrite my hardware stack.”

### Debugging

“When the robot behaves badly, let me inspect what the policy saw, predicted, and what was actually executed.”

## Core objects

### RobotProfile

Describes the physical/logical robot interface available to RoboRouter.

### TaskProfile

Describes the requested behavior, environment, and requirements.

### ExecutablePolicySpec

Immutable/versioned description of a runnable policy including execution-critical transforms around the model weights.

### CompatibilityRecord

Evidence-backed compatibility relation between policy, robot, task, control surface, and runtime.

### Rollout

Reproducible execution/evaluation record.

See `docs/DATA_MODEL.md`.

## Main product surfaces

### Explore

Model/policy catalog with evidence-aware filtering.

### Compatibility

Given `RobotProfile + TaskProfile`, return ranked candidate policies with:

- compatibility status;
- missing requirements;
- fine-tuning/adaptation needs;
- evidence;
- supported evaluation path;
- supported execution path.

### Compare

Run or view comparable evaluation results and rollouts across policies.

### Robots

Register/import robot profiles and inspect compatible control surfaces.

### Rollouts

Debuggable trace of sim/shadow/physical runs.

### Connect

Install/connect `rr-agent` on an existing robot-side machine.

## Website information architecture

```text
/                         landing
/explore                  catalog/search
/policies/:id             policy page
/robots                    user's robots
/robots/:id                robot profile + compatibility
/compare                   evaluation comparison
/evals/:id                 evaluation job/result
/rollouts/:id              reproducible trace
/pilots                    external pilot application
/docs                      integration docs
```

## Default discovery flow

1. What are you controlling?
   - single arm;
   - bimanual;
   - dexterous hand;
   - mobile manipulator;
   - rover/wheeled base;
   - drone/UAV;
   - quadruped;
   - humanoid;
   - other.
2. What task?
3. What sensors exist?
4. What control surfaces exist?
5. What availability constraint?
   - open weights;
   - open code;
   - hosted/API;
   - any.
6. What evidence level is acceptable?
7. Return a curated candidate set.

## Example result language

Good:

> **π0.5 — fine-tune required**  
> Policy family is relevant to this manipulation task, but the catalog contains no verified checkpoint matching this robot profile. Simulation/evaluation may still be available.

Bad:

> **π0.5 — compatible ✅**

unless RoboRouter has evidence for the actual execution path.

## Long-term product possibility

If the MVP works, RoboRouter can grow into a neutral control plane spanning:

- hosted inference;
- BYO GPU/on-prem runners;
- evaluation CI;
- model/policy registry;
- per-embodiment leaderboards;
- policy observability;
- external provider routing;
- fine-tune publishing;
- real-world evaluation networks.

Those are *future layers*, not prerequisites for the first useful product.
