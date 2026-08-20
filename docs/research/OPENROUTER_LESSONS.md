# What to Learn from OpenRouter

RoboRouter began as an analogy: “OpenRouter for robotics models.” The analogy is valuable, but only at the correct layer.

## What transfers well

### 1. Fragmentation creates value for a neutral interface

OpenRouter made a fragmented model/provider ecosystem easier to consume from one developer workflow.

Robotics is fragmented across:

- policy families;
- serving frameworks;
- checkpoints;
- robot embodiments;
- simulators;
- hardware middleware;
- evaluation conventions.

Neutrality is valuable.

### 2. Discovery is part of the product

A developer should be able to browse and compare capabilities before writing integration code.

RoboRouter's equivalent is an evidence-aware policy catalog.

### 3. One identity / one control plane

Users should not need separate accounts/configuration conventions for every model runtime/provider.

### 4. Existing-client compatibility lowers adoption friction

OpenRouter benefited from API compatibility. RoboRouter should seek equivalent low-friction adoption through existing ecosystems:

- XPolicyLab-compatible policy runners;
- LeRobot-compatible hardware/policies;
- ROS2 integrations;
- PX4/ROS2 aerial integrations;
- model-native shims.

### 5. Public ecosystem telemetry can become a growth loop

Eventually RoboRouter may publish:

- most-used policies by robot class;
- real/sim evaluation distributions;
- per-embodiment leaderboards;
- public Rollouts.

But distinguish popularity from quality.

## What does NOT transfer directly

### 1. A model name is not enough

LLM provider endpoints can often be substituted under one model identifier.

Robot execution depends on embodiment, sensors, normalization, action semantics, controller mapping, and timing.

RoboRouter needs `ExecutablePolicySpec`, not merely `model="pi0.5"`.

### 2. Silent fallback is much more dangerous

Switching an LLM provider mid-request is often invisible.

Switching physical policies mid-episode may radically change behavior.

Default:

- runner failover only for equivalent executable specs;
- policy change at explicit session/episode boundary.

### 3. “Cheapest provider” is not a sufficient routing objective

Robot execution should prioritize:

1. semantic compatibility;
2. evidence/reproducibility constraints;
3. latency/deadline feasibility;
4. privacy/data policy;
5. capacity;
6. price.

### 4. Safety cannot live in the router

The robot-side system remains the physical safety authority.

### 5. Tokens do not exist as the obvious unit

Potential usage units include:

- session time;
- action chunks;
- GPU time;
- simulation episodes.

Do not freeze billing semantics before product usage exists.

## Product-sequencing lesson

Do not copy mature OpenRouter features too early.

The initial RoboRouter analogue of OpenRouter's early magic is:

> **“I changed one workflow and suddenly I can understand/try multiple models.”**

Not:

> “We already built a marketplace, provider auctions, credits, and smart routing.”

## Recommended sequencing

1. catalog;
2. compatibility;
3. no-hardware evaluation;
4. Rollouts;
5. external robot shadow execution;
6. supervised actuation;
7. multi-provider/hosted runner choices;
8. only then billing/marketplace/routing sophistication.
