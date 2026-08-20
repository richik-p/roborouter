# Roadmap

This is a product-validation roadmap, not a promise of dates.

## M0 — Repository + vertical-slice design

**Goal:** turn product docs into an implementation plan and choose the simplest working no-hardware slice.

Candidate issues:

- M0-01 audit docs and upstream dependencies;
- M0-02 define repo/package structure;
- M0-03 freeze v0 schema semantics;
- M0-04 choose first policy + simulator/eval path;
- M0-05 create initial catalog seed format;
- M0-06 define vertical-slice acceptance test.

Exit criterion:

> We can name the exact first policy, evaluation environment, data flow, packages, and acceptance criteria without hand-waving.

## M1 — Catalog + compatibility web slice

**Goal:** a user can browse real policy metadata and run a compatibility query.

Candidate issues:

- schema implementation;
- seed 20 curated policy entries;
- policy list/detail API;
- compatibility rule engine v0;
- Explore page;
- Policy detail page;
- simple RobotProfile/TaskProfile input flow.

Exit criterion:

> Search “single-arm language pick-and-place” and “UAV language navigation” and receive sensible, evidence-qualified results.

## M2 — First evaluation + Rollout

**Goal:** one model can run through the complete hosted evaluation experience.

Candidate issues:

- eval job object/lifecycle;
- first policy adapter/runtime;
- first simulator/benchmark integration;
- artifact/video storage;
- Rollout persistence;
- Rollout page;
- result page;
- reproducibility metadata.

Exit criterion:

> A stranger can launch an eval and receive a saved Rollout without maintainer intervention.

## M3 — Second policy family + Compare

**Goal:** prove RoboRouter is a multi-policy product.

Candidate issues:

- second PolicyAdapter;
- common evaluation contract hardening;
- side-by-side Compare page;
- compatibility/evidence differences displayed clearly;
- regression tests for both policy families.

Exit criterion:

> Two policies can be evaluated under a meaningfully comparable setup from one UX.

## M4 — `rr-agent` read-only + shadow

**Goal:** connect an external robot without actuation.

Candidate issues:

- agent packaging/auth/bootstrap;
- RobotAdapter interface;
- first middleware adapter (choose based on real pilot);
- read-only introspection;
- RobotProfile proposal/import;
- observation streaming;
- shadow session;
- action trace visualization;
- disconnect/fault behavior.

Exit criterion:

> A collaborator's real robot streams observations through a live policy and records predicted actions without moving.

## M5 — Supervised physical pilot

**Goal:** one known-good policy executes one known task through RoboRouter.

Requires an ExecPlan and safety review.

Candidate issues:

- local arming state;
- local safety policy;
- action validation/TTL;
- safe fault behavior;
- operator controls;
- executed-action trace;
- supervised test checklist;
- physical Rollout evidence.

Exit criterion:

> One external robot completes a supervised task through RoboRouter with an inspectable Rollout.

## M6 — Second embodiment proof

**Goal:** show the product model is not arm-specific.

Preferred early route: UAV simulation.

Candidate issues:

- aerial RobotProfile/control surfaces;
- PX4/AeroVLA or another verified simulation path;
- aerial task filters;
- evidence labeling;
- side-by-side product demo showing manipulation + aerial runs through the same control plane.

Exit criterion:

> The same catalog/compatibility/eval/Rollout product model handles an aerial policy without polluting manipulation schemas.

## M7 — External beta

**Goal:** 3+ external users use the product without live handholding.

Candidate issues:

- pilot application flow;
- minimal accounts/auth;
- docs cleanup;
- telemetry/analytics;
- shareable sim Rollouts;
- feedback capture;
- onboarding fixes.

Exit criterion:

> Users return to try a second model or submit a robot profile because RoboRouter saved meaningful setup/debugging time.

## After product signal

Only then evaluate:

- hosted inference as a paid product;
- BYO GPU/on-prem runners;
- evaluation CI;
- training/fine-tuning workflow;
- provider ecosystem;
- public leaderboards;
- creator/publisher features;
- sophisticated serving/multiplexing economics.
