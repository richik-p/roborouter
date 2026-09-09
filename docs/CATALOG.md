# Catalog format

**Reconstructed:** 2026-08-20. The missing original is replaced by this
implementation-facing specification.

Catalog records are reviewed YAML files under `catalog/`. Policies, robots,
tasks, and evaluation environments have immutable `id + revision` identities.

Every executable policy entry must include source and checkpoint identity,
runtime adapter and revision, observation requirements, action schema,
normalization identity, availability, license, and dated evidence. A model
family may be listed without an executable checkpoint, but its supported path
must then be `research_only` or `fine_tune_required`.

Catalog validation rejects duplicate identities, missing required provenance,
unsupported status values, malformed URLs, and executable claims without an
exact runtime/checkpoint path. Import is transactional and idempotent.

## Revision resolution

Catalog reads (`GET /v0/policies`, `GET /v0/policies/{id}`, and compatibility
queries) resolve each policy id to its newest imported revision. Older revisions
stay in the database so Rollouts and evaluation jobs keep exact provenance. To
change a reviewed entry, bump its `revision`; re-seeding never mutates an
existing `id + revision` row.

## Research entries

Entries without a `runtime` are research metadata. They may pin a released
checkpoint identity, and their evidence text records what the pinned upstream
evaluation boundary actually found, including negative results, but their
compatibility status stays `RESEARCH_ONLY` until a RoboRouter runner exists.
`UPSTREAM_REPRODUCTION` is used only where that boundary reproduced a published
score; a smoke run with no reference, or a failed reproduction, stays
`RESEARCH_ONLY` with the finding stated.
