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

