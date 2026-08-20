# Codex Execution Plans for RoboRouter

Use an **ExecPlan** for complex features, cross-cutting refactors, physical-robot integration work, or anything that changes a core product/data-model contract.

An ExecPlan is a living design and execution document. It should be understandable to a developer who has only the repository and the plan—no hidden conversational context.

## When an ExecPlan is required

Create one when work:

- spans multiple services/packages;
- changes `RobotProfile`, `TaskProfile`, `ExecutablePolicySpec`, `CompatibilityRecord`, or `Rollout` semantics;
- adds a new robot class/control surface;
- adds a new policy runtime family;
- adds physical actuation;
- changes safety behavior;
- adds a significant infrastructure dependency;
- changes persistence/migrations;
- requires a multi-step migration;
- is expected to take more than a focused single-session task.

## ExecPlan template

Create plans under `docs/plans/<short-name>.md`.

```markdown
# <Feature or change>

## Objective
What user-visible or architectural outcome must exist when this is complete?

## Why now
What milestone/user need requires this work?

## Scope
Exactly what is included.

## Non-goals
What tempting adjacent work is explicitly excluded.

## Current state
Relevant repository paths, interfaces, and upstream dependencies.

## Constraints
Product, safety, performance, compatibility, and deployment constraints.

## Design
Data-flow and interface decisions. Include diagrams/examples where useful.

## Data model / API changes
Explicit schema changes and migration implications.

## Failure modes
What can go wrong? Include incompatible hardware, stale actions, dependency failures, partial jobs, and bad external metadata where relevant.

## Safety impact
Required for anything that may influence physical actuation.

## Milestones
- [ ] milestone 1 — observable acceptance condition
- [ ] milestone 2 — observable acceptance condition
- [ ] ...

## Validation
Unit/integration/e2e/manual checks needed to prove success.

## Rollback / recovery
How to undo or safely disable the change.

## Progress log
Dated notes as implementation proceeds.

## Decisions made during implementation
Record deviations from the original design and why.
```

## Execution behavior

While implementing an ExecPlan:

- keep the plan updated;
- complete the next milestone instead of repeatedly asking what to do next;
- surface material ambiguity rather than hiding it;
- prefer a working vertical slice over scattered partial scaffolding;
- keep physical actuation disabled unless that milestone explicitly enables and validates it;
- update docs when contracts change.

## Completion condition

A plan is complete only when:

- acceptance conditions are demonstrably met;
- tests/validation are recorded;
- docs reflect final behavior;
- unresolved risks are explicitly listed;
- follow-up work is moved into separate issues rather than silently remaining in scope.
