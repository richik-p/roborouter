# Evaluation access gating (launch keys and quotas)

## Objective

Evaluation launches can be exposed to invited external users without an open GPU
queue: every launch is attributed to a revocable key, bounded per key, and bounded
globally. Catalog, compatibility, Rollout, and job reads stay public.

## Why now

`POST /v0/evaluations` was unauthenticated. The smoke runbook hid it behind site-wide
HTTP basic auth, which does not distinguish users, cannot be revoked per person, and
cannot bound spend. Nothing else stands between "works" and "public".

## Scope

- Launch keys `rrl_<credential-id>.<secret>`, SHA-256 stored, roles `user` and
  `operator`, per-key `concurrent_limit` and `daily_limit`, expiry, revocation.
- `EVALUATION_ACCESS=key` (default) requires a key to create or cancel a job;
  `open` keeps the pre-beta behavior for local exploration.
- Global `MAX_ACTIVE_EVALUATIONS` cap on QUEUED/CLAIMED/RUNNING jobs, applied to
  operators too, and `MAX_SEEDS_PER_EVALUATION` on episodes per job.
- Job ownership: a `user` key cancels only its own jobs; `operator` cancels any.
- Revoking a key cancels its in-flight jobs (spend stop).
- Operator CLI `roborouter-launch-credentials create|list|revoke`; a
  `LAUNCH_BOOTSTRAP_TOKEN` seeds one key for dev, tests, and first deployment.
- Web: an **Access key** field (localStorage) on the policy and Compare pages;
  the key is sent as a Bearer header on launch and cancel only.

## Non-goals

Accounts, OAuth, sessions, billing, key self-service, rate limiting of reads, and a
strict (serialized) global cap. Those wait for real usage.

## Current state

`services/api/src/roborouter_api/launch_auth.py`, `launch_credentials.py`,
migration `20260909_04`, enforcement in `main.py` (`_enforce_launch_quotas`),
`apps/web/lib/launch-key.ts`, `apps/web/components/launch-key-field.tsx`.

## Constraints

Mirror the worker-credential pattern (token format, hashing, revocation) so
operators learn one model. No contract changes: `EvaluationJob` is unchanged and the
owning key is a database column only. Reads remain unauthenticated.

## Design

```text
browser ──(Bearer rrl_…)──► POST /v0/evaluations
                             │ 401 missing/invalid key (unless EVALUATION_ACCESS=open)
                             │ 422 seeds > MAX_SEEDS_PER_EVALUATION
                             │ 429 active jobs ≥ MAX_ACTIVE_EVALUATIONS   (everyone)
                             │ 429 key's active jobs ≥ concurrent_limit  (users)
                             │ 429 key's jobs in 24 h ≥ daily_limit      (users)
                             └─► job row records launch_credential_id
```

Counts are advisory under concurrent requests; the cap bounds spend rather than
guaranteeing an exact maximum. A serialized cap can be added with a singleton lock
row if usage ever needs it.

## Data model / API changes

New table `launch_credentials`; new nullable indexed column
`evaluation_jobs.launch_credential_id`. No OpenAPI schema changes beyond the optional
`authorization` header on create/cancel.

## Failure modes

- Missing or wrong key: 401 with a clear detail; the UI shows it inline.
- Quota hit: 429 with the limit stated; nothing is queued.
- Key revoked mid-run: job set to CANCELED with `failure_detail="launch key revoked"`;
  the worker terminates on its next heartbeat exactly as with a manual cancel.
- Bootstrap token malformed or conflicting: startup fails loudly, as for workers.

## Safety impact

None on physical actuation; this bounds simulation spend and attribution only.

## Milestones

- [x] Keys, quotas, ownership, revocation, bootstrap, CLI — unit tests pass.
- [x] Web access-key field; Playwright covers refusal without a key and launch with one.
- [x] Runbook and `.env.example` updated; default is closed.
- [ ] Issue the first external keys and record who holds which label.

## Validation

`make check` and `make e2e`; `alembic upgrade head && alembic check` on a fresh
database; the upgrade path from a `20260820_03` database.

## Rollback / recovery

Set `EVALUATION_ACCESS=open` to restore the pre-beta behavior without a code change;
the global and seed caps still apply. Downgrade migration drops the table and column.

## Progress log

- 2026-09-09 — implemented on `beta` alongside the catalog repair.

## Decisions made during implementation

- Operators bypass per-key quotas but never the global cap: the cap is a spend guard,
  not a permission.
- Keys are stored in browser localStorage rather than a cookie session, so the API
  stays stateless and the same key works from `curl`.
