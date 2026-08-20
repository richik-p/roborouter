# M0 fixture-backed vertical slice

## Objective

Deliver a local, reproducible path from policy discovery through compatibility
to a saved Rollout page without requiring CUDA hardware.

## Scope

Repository repair, v0 contracts, one π₀.₅ policy, LIBERO profiles, deterministic
compatibility, a provenance-labeled fixture, FastAPI endpoints, and the web UI.

## Non-goals

Live GPU execution, authentication, arbitrary policies, or physical robots.

## Constraints

Never infer execution semantics. Preserve exact upstream identity. Keep
physical actuation absent.

## Milestones

- [x] Repository and documentation baseline
- [x] Contracts and catalog validation
- [x] API and persistence path
- [x] Product UI
- [x] End-to-end local validation

## Validation

Contract, compatibility, API, catalog, build, and browser workflow tests.

## Rollback / recovery

The fixture and seed import are idempotent. Schema changes remain pre-release
and can be reset through the documented local database command.

## Progress log

- 2026-08-20: implementation started from the approved plan.
- 2026-08-20: completed the fixture-backed web/API/catalog path, generated
  contracts, and added evaluation-job and remote-worker foundations.
- 2026-08-20: local tests, lint, type checks, and production web build passed.
  Remote GPU smoke validation remains tracked separately.
