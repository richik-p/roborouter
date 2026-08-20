# MVP Scope

## MVP objective

Prove that RoboRouter removes meaningful friction between **robot developers and a fragmented policy ecosystem**.

The MVP is successful if external users understand the catalog, can compare policies without owning dedicated hardware, and one collaborator can connect a physical robot without rewriting their whole stack.

## MVP thesis to test

> Robotics developers value an evidence-aware compatibility/evaluation layer enough to use it before RoboRouter becomes a full training or inference marketplace.

## Must-have

### A. Curated catalog

At least 20 useful policy entries with enough metadata to filter by:

- model/policy family;
- model role;
- robot class;
- task family;
- sensor requirements;
- state/action/control surface;
- open/closed availability;
- runtime/framework;
- evidence level;
- fine-tune/adaptation status;
- license/source links.

The catalog should intentionally include more than manipulation so the product's extensibility is visible.

### B. Core schemas

Implement stable v0 schemas for:

- RobotProfile;
- TaskProfile;
- ExecutablePolicySpec;
- CompatibilityRecord;
- Rollout.

### C. Compatibility query

Given a robot/task profile, return:

- eligible policies;
- incompatible policies when useful, with reasons;
- missing sensors/control surfaces;
- fine-tune required vs runnable;
- evidence level;
- available eval path.

Initial ranking may be deterministic/rule-based. Do not build ML “smart routing.”

### D. One no-hardware evaluation vertical slice

A user can:

1. select a policy;
2. select a supported task/eval environment;
3. launch evaluation;
4. receive a result/video;
5. see exact policy/eval revisions;
6. open a saved Rollout.

Then add a second policy family to prove the abstraction is not single-model-specific.

### E. One non-arm simulation/example

Represent and, if practical with current upstream tooling, execute one aerial/UAV example in simulation.

This is not required for first code commit, but should exist before public positioning as “all robot models.”

### F. `rr-agent` pilot path

For one external physical robot:

- detect or import a RobotProfile;
- connect through LeRobot, ROS2, or a documented vendor SDK;
- stream observations;
- receive predicted actions;
- run in shadow mode;
- show predicted action/trajectory diagnostics;
- require explicit local arm/enable before actuation;
- record a Rollout.

### G. Basic website

Minimum pages:

- landing;
- explore/filter;
- policy detail;
- compare/eval result;
- rollout detail;
- become-a-pilot.

## Should-have

- robot profile wizard/import;
- compare two evaluation results side-by-side;
- basic catalog provenance/source links;
- public shareable Rollout link for simulation;
- CLI or local diagnostic command;
- basic search by natural-language task translated into structured filters;
- explicit “research only / sim only / fine-tune required” warnings.

## Could-have

Only if Must/Should scope is complete:

- BYO remote GPU runner;
- local policy runner;
- additional simulator backend;
- third policy family;
- pilot application automation;
- basic usage analytics.

## Won't-have in MVP

- payments/billing;
- creator marketplace;
- hosted fine-tuning;
- automatic model-quality routing;
- cross-policy failover during an episode;
- broad autonomous real-world benchmarking;
- enterprise fleet management;
- a novel universal transport protocol;
- multi-LoRA GPU multiplexing;
- “supports every robot” claims;
- cloud-issued low-level motor commands for UAVs;
- unsupervised real-world actuation.

## MVP demo script

### Demo 1 — discovery

Search/filter for:

> language-conditioned single-arm pick-and-place

Show a few candidates and why they differ.

Then change robot class to UAV and show aerial policies, proving the catalog is embodiment-general.

### Demo 2 — evaluation

Choose two supported manipulation policies and evaluate/compare on the same task/environment.

Show:

- videos;
- result metrics;
- exact revisions;
- Rollout objects.

### Demo 3 — partner robot

Open a registered external robot.

Show:

- robot profile;
- available control surface;
- compatibility result;
- shadow run;
- predicted actions;
- local arming;
- one supervised execution;
- resulting Rollout.

## Acceptance criteria for public beta

- a new user can understand why a policy is/isn't usable without reading its paper;
- one user can complete a simulation eval without manual maintainer intervention;
- at least two policy families are executable through the same product workflow;
- at least one non-arm domain exists in the catalog and has a credible evaluation story;
- one external real robot has completed a shadow session;
- one supervised real task has completed through the product;
- no real actuation can occur without local enable/arming;
- all real/sim evidence is labeled accurately;
- a user can apply to become a pilot from the website.

## Product metrics during MVP

Do not optimize revenue. Track:

- catalog searches per user;
- compatibility queries;
- eval jobs started/completed;
- compare actions;
- pilot applications;
- external RobotProfiles collected;
- percentage of users who encounter “no compatible policy” and why;
- time from pilot install to first shadow run;
- time from shadow run to first supervised actuation;
- number of Rollouts users revisit/share.

The most important qualitative metric:

> “Did RoboRouter save you enough setup/debugging time that you would use it again for the next model?”
