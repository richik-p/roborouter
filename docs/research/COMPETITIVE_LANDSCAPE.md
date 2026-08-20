# Competitive / Adjacent Landscape

**Snapshot:** 2026-08-19.

The goal is not to prove “no competitor exists.” The goal is to understand which layers are already being solved and where RoboRouter can provide a coherent product.

## XPolicyLab

### What it does

Common policy/evaluation/deployment adapter layer across 40+ robot policies and integrated benchmarks.

### Overlap

High technical overlap with the **policy adapter/runtime standardization** part of the original RoboRouter concept.

### Strategy

Build on/integrate with it. Do not compete by writing another 40 adapters unless an important gap appears.

RoboRouter differentiation:

- productized discovery;
- RobotProfiles;
- compatibility graph;
- cross-framework hardware onboarding;
- runner brokerage;
- Rollout observability;
- user-facing evidence/UX.

## Hugging Face LeRobot

### What it does

Broad robot-learning ecosystem for hardware, teleop, datasets, training, policies, evaluation and deployment.

### Overlap

High ecosystem overlap; LeRobot may expand into adjacent UX/hosting areas.

### Strategy

Be complementary. A user with a LeRobot robot should be one of the easiest RoboRouter onboarding paths.

Long-term partnership/distribution opportunities may exist, but are not required for MVP.

## RoboDojo / RoboTwin

### What they do

Evaluation/benchmark environments with common policy integration via XPolicyLab.

### Strategy

Treat as evaluation backends/evidence sources, not competitors to the overall product.

## Physical Intelligence / openpi

### What it does

Model lab + open model/runtime/fine-tuning/remote-inference ecosystem for open π releases.

### Strategy

Model supplier/upstream integration. RoboRouter is neutral across families.

## NVIDIA Isaac GR00T / Isaac ecosystem

### What it does

Open model family plus simulation/training/deployment ecosystem tied to NVIDIA's physical-AI stack.

### Strategy

Important supply/integration ecosystem. RoboRouter remains cross-vendor.

## Vertical robotics platforms

Products such as robot-specific training/control platforms can overlap heavily for their supported hardware but often optimize a more vertically integrated experience.

RoboRouter's positioning should remain:

> **model- and hardware-agnostic compatibility/evaluation/execution control plane**

rather than trying to out-verticalize a vendor on one robot.

## Generic GPU/model hosting

Generic inference platforms can host robotics workloads but generally do not understand:

- robot profiles;
- control surfaces;
- normalization/controller identity;
- safety modes;
- rollout evidence;
- embodiment compatibility.

RoboRouter should use generic compute where practical rather than compete on raw GPU hosting.

## Competitive risk: upstream platforms add the UX

The strongest risk is not a tiny direct startup. It is that LeRobot/HF, XPolicyLab, NVIDIA, or another ecosystem progressively adds enough discovery, hosting, and evaluation UX that a separate control plane becomes unnecessary.

Defense is not “more infrastructure.” It is to build the missing user-facing graph/data:

- verified robot-policy compatibility;
- exact execution identity;
- cross-ecosystem RobotProfiles;
- Rollout observability;
- real external user workflows;
- evidence collected across heterogeneous stacks.

## Positioning statement

Avoid:

> “OpenRouter for VLAs.”

Use:

> **RoboRouter helps you find, evaluate, and run the right model for your robot.**

The OpenRouter analogy is useful for investors/developers after the product is understood, but should not constrain the architecture.
