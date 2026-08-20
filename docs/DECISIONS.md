# Product and Architecture Decision Log

This is a lightweight decision record. Add dated entries when a core choice changes.

## D-001 — Product starts from robot/use case

**Status:** accepted  
**Date:** 2026-08-19

Default UX asks what the user is controlling and trying to do. Model-first exploration is secondary.

Reason: robotics compatibility is embodiment/task dependent in a way LLM model selection is not.

---

## D-002 — Not arm-specific

**Status:** accepted  
**Date:** 2026-08-19

Core schemas must support manipulators, hands, mobile robots, UAVs, legged systems, humanoids, and future robot classes without pretending they share one low-level action representation.

---

## D-003 — Broad discovery, narrow physical execution

**Status:** accepted  
**Date:** 2026-08-19

The catalog may cover many domains before RoboRouter has direct physical execution support for all of them.

Evidence labels prevent overclaiming.

---

## D-004 — PolicyAdapter and RobotAdapter are separate

**Status:** accepted  
**Date:** 2026-08-19

Policy/runtime integration and hardware/middleware integration are independent axes.

Reason: avoid N×M policy/robot integration explosion.

---

## D-005 — ExecutablePolicySpec is the runnable identity

**Status:** accepted  
**Date:** 2026-08-19

A model/checkpoint name alone is insufficient. Execution-critical preprocessing, normalization, action semantics, runtime, and controller assumptions must be versioned.

---

## D-006 — Compatibility is graded/evidence-backed

**Status:** accepted  
**Date:** 2026-08-19

Do not use a single boolean “supported.” Distinguish real verified, bridged, sim verified, fine-tune required, research only, unknown, and incompatible states.

---

## D-007 — Leverage XPolicyLab instead of centering a new protocol

**Status:** accepted  
**Date:** 2026-08-19

XPolicyLab has emerged as a common policy-side evaluation/deployment layer with 40+ integrations. RoboRouter should initially build above/use it where practical rather than inventing a competing universal policy protocol.

Future protocol work is allowed only if a real gap remains after integrations are attempted.

---

## D-008 — Existing hardware ecosystems remain authoritative

**Status:** accepted  
**Date:** 2026-08-19

Prefer:

- LeRobot for compatible hardware;
- ROS2/ros2_control for general robots;
- PX4 + ROS2 for UAV high-level control;
- vendor SDK adapters where needed.

---

## D-009 — Shadow mode before physical actuation

**Status:** accepted  
**Date:** 2026-08-19

Every first physical pilot should pass a real-observation/predicted-action shadow phase before enabling commands.

---

## D-010 — Local safety authority

**Status:** accepted  
**Date:** 2026-08-19

Cloud inference is never the sole physical safety controller.

---

## D-011 — No automatic cross-policy mid-episode fallback

**Status:** accepted  
**Date:** 2026-08-19

Policy switching happens explicitly at an episode/session boundary unless a future narrowly designed feature proves otherwise.

---

## D-012 — First physical pilot uses a collaborator's known-working stack

**Status:** accepted  
**Date:** 2026-08-19

We do not need to buy an arm before product validation. Integrate an external robot and known-good policy first.

---

## D-013 — Simulation is the no-hardware acquisition path

**Status:** accepted  
**Date:** 2026-08-19

The website must offer useful evaluation/discovery even to users who own no robot.

---

## D-014 — Do not copy mature OpenRouter features before proving the wedge

**Status:** accepted  
**Date:** 2026-08-19

Do not start with marketplace payouts, smart routing, complex provider economics, or billing. Copy OpenRouter's low-friction discovery/unification principles first.

---

## D-015 — Serving multiplexing is an optimization hypothesis

**Status:** accepted  
**Date:** 2026-08-19

Do not base MVP economics or architecture on assumed robots-per-GPU figures. Benchmark per architecture/workload before investing in specialized multiplexing.
