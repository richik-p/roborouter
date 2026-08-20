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

- [ ] Repository and documentation baseline
- [ ] Contracts and catalog validation
- [ ] API and persistence path
- [ ] Product UI
- [ ] End-to-end validation

## Validation

Contract, compatibility, API, catalog, build, and browser workflow tests.

## Rollback / recovery

The fixture and seed import are idempotent. Schema changes remain pre-release
and can be reset through the documented local database command.

## Progress log

- 2026-08-20: implementation started from the approved plan.
