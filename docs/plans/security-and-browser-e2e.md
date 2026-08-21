# Per-worker identity and browser E2E plan

## Why this precedes broader exposure

The current control plane accepts one deployment-wide worker token. That is enough
for a restricted, single-worker smoke run, but it cannot identify, rotate, or revoke
workers independently. Complete this milestone before adding a second worker or
opening worker access beyond the restricted TLS hostname.

## Per-worker credentials

### Contract and persistence

Add an immutable worker-credential table with:

- `credential_id` (public lookup identifier);
- `worker_id` (bound identity);
- SHA-256 of a randomly generated 32-byte secret;
- scopes: `register`, `claim`, `heartbeat`, `artifact`, `complete`, `fail`;
- creation, last-used, expiry, and revocation timestamps;
- optional human-readable label; never the raw token.

Token format: `rrw_<credential-id>.<base64url-secret>`. The creation command prints
the token once. The random secret has enough entropy that a deterministic hash lookup
does not depend on a slow password hash. Compare digests with `hmac.compare_digest`.

### API enforcement

Replace the global-token dependency with a `WorkerPrincipal` dependency. Enforce:

1. token exists, is unexpired, and is not revoked;
2. requested endpoint scope is present;
3. every body/query `worker_id` equals the principal's worker ID;
4. a worker cannot heartbeat, presign, complete, fail, or cancel another worker's
   leased job;
5. logs show credential ID and worker ID, never the raw token;
6. rotation overlaps old/new credentials only for an explicitly bounded interval.

Add operator CLI commands for create, list metadata, rotate, and revoke. Operator
credentials must not be exposed through the public worker hostname.

### Acceptance tests

- malformed, unknown, expired, and revoked tokens return 401;
- valid token with missing scope returns 403;
- worker A cannot register as worker B or touch worker B's lease/artifacts;
- token rotation preserves an active lease only when explicitly allowed;
- revocation prevents the next heartbeat and the worker cancels its harness;
- secret values do not appear in captured logs, Rollouts, OpenAPI examples, or test
  failure output.

## Browser E2E coverage

Use Playwright's multiple `webServer` configuration to start an isolated SQLite API
and Next.js server. Official configuration reference:
https://playwright.dev/docs/test-webserver.

### Repository changes

1. Add `@playwright/test` as a dev dependency and pin it in `package-lock.json`.
2. Add `apps/web/playwright.config.ts` with API and web `webServer` entries, one
   Chromium project, trace-on-first-retry, and screenshots only on failure.
3. Use a unique `/tmp/roborouter-e2e-<worker>.sqlite3`; never reuse the developer DB.
4. Add stable accessible names or `data-testid` only where semantic selectors are
   insufficient.
5. Add `npm run e2e`, `make e2e`, and a CI step after unit tests/build.

### Required scenarios

- catalog loads at least 20 reviewed policies;
- search finds π₀.₅ and a UAV policy;
- LIBERO Panda + Object compatibility displays `SIM VERIFIED` and reason text;
- policy detail shows exact source/checkpoint/runtime/evidence identity;
- fixture Rollout displays its upstream-only evidence warning;
- evaluation launch reaches a durable `QUEUED` job;
- cancellation updates the job to `CANCELED` and is idempotent;
- completed echo/fixture job links to its Rollout and renders artifact provenance;
- Compare refuses a matched label when suite/task/seed/protocol differs;
- matched completed π₀.₅/MolmoAct2 fixtures render metrics, runtime identities, and
  evidence side by side.

### Product gaps to close with the tests

The evaluation page still needs a cancel control and a link to completed Rollouts.
Add `GET /v0/evaluations/{id}/rollouts` rather than making the browser download and
filter the entire Rollout catalog. The Compare page must load completed results; job
launch buttons alone do not satisfy the M3 comparison acceptance criterion.

## Exit criteria

- all identity isolation tests pass against PostgreSQL;
- browser E2E passes locally and in GitHub Actions;
- no test requires CUDA or external network access;
- M3-03 remains open until completed matched results—not just queued jobs—render side
  by side.
