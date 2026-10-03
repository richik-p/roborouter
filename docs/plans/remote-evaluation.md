# Remote π₀.₅/LIBERO evaluation ExecPlan

## Objective

Verify the implemented remote boundary with one π₀.₅ LIBERO Object episode and retain
enough evidence to convert the current provenance-labeled fixture into a
RoboRouter-executed Rollout.

## Preconditions

- NVIDIA Linux host with a supported CUDA runtime and sufficient VRAM;
- outbound HTTPS access to the RoboRouter API and artifact store;
- `vla-evaluation-harness` at release `v0.4.0`, commit
  `2680ab2fafe981c2dba63c6c1a4e7bb4415dbb56`;
- LeRobot `v0.6.0` and checkpoint `lerobot/pi05_libero_finetuned_v044` at
  `8e174154ef5f6c60a8da12ae99c303d8963138c1`;
- LIBERO image digest
  `sha256:2a4566009395888ae3904bde87cffceea7526e2e0f0667b933cae0e8e6134413`;
- LIBERO assets and licenses accepted according to upstream requirements;
- unique worker token and empty output directory.

## Procedure

1. Record GPU model, driver, CUDA version, operating system, commit/release, Python
   lockfile hash, checkpoint revision, and every applicable license.
2. Run the upstream health checks without RoboRouter. Preserve their raw logs.
3. Pull the recorded benchmark image by digest and verify the local image identity.
4. Start the outbound worker and verify its registered capabilities through control
   plane logs without exposing the token.
5. Launch one seed through the web UI. Confirm the state sequence is
   `QUEUED → CLAIMED → RUNNING → SUCCEEDED` and heartbeats extend the lease.
6. Confirm one Rollout exists per episode and that MP4, JSON/JSONL, log, and config
   artifacts have matching SHA-256 values in object storage and the API response.
7. Replay completion once. Confirm no duplicate Rollout or artifact identity appears.
8. Record wall time, peak VRAM, disk use, network transfer, result schema, and any
   upstream configuration deviations.

## Acceptance

- The exact execution identity is inspectable from the Rollout page.
- A failed task outcome remains a successful infrastructure job with `success=false`.
- Harness/runtime failures produce typed job failures and no fabricated Rollout.
- No secret appears in logs, artifacts, API responses, or browser output.
- The fixture documentation distinguishes upstream reproduction evidence from this
  newly executed RoboRouter evidence.

## Recovery

Cancel the job from the control plane, stop the worker, and preserve the failed output
directory for diagnosis. Never mark an interrupted model episode retry-safe without
adapter-specific proof. A replacement job receives a new identity and seed record.

## Status

**Performed on 2026-10-02 for the MolmoAct2 family; π₀.₅ remains blocked on gated
access.** The pinned boundary (harness `2680ab2`, LeRobot v0.6.0, LIBERO image
`sha256:2a4566…`) executed end to end through the RoboRouter worker and produced a
verified Rollout. Evidence is in
[`evidence/remote-evaluation-2026-10-02/`](evidence/remote-evaluation-2026-10-02/).

### Evidence record

| Item | Value |
|---|---|
| Host | AWS g5.2xlarge, NVIDIA A10G 24 GB, driver 595.91.07, Amazon Linux 2023, kernel 6.18 |
| Topology | Single box: API `:8800`, PostgreSQL and S3 store in Docker on loopback, worker and model server on the same host; no public exposure |
| RoboRouter | `beta` at `3564c38` |
| Job | `eval-be4fd05b-e857-4b6a-a956-1ffbdf6b1e2b`: `molmoact2-libero@allenai-molmoact2-libero`, `vla-eval-libero-goal`, `libero-goal-interaction`, seed 7 |
| Checkpoint | `allenai/MolmoAct2-LIBERO@0d24a92bd1faf321ef497c3bbd5681af97c65aa2`, loaded from the pinned local snapshot |
| States | QUEUED 00:19:20 → CLAIMED 00:19:24 → RUNNING → SUCCEEDED 00:28:00 UTC |
| Model server ready | 345.8 s after start (checkpoint cached; ~13 GB VRAM) |
| Result | 10 tasks × 1 episode, `mean_success` 1.0, 157 s of episode time, 168 s harness wall |
| Rollout | `rollout-09a3b7b3-3e32-4e67-ad50-330098dd4db1`, `success=true`, 26 artifacts: 10 videos, 10 episode traces, aggregate, 2 logs, 2 configs |
| Verification | Every artifact's SHA-256, byte count, media type and object metadata match the private object; identical completion replay returned 200 with Rollout and artifact counts unchanged |
| Upstream check | Harness smoke config with the same server: 1/1 success before any RoboRouter job |

### Acceptance

- Exact execution identity is on the Rollout: harness commit, LeRobot tag, container
  digest, checkpoint revision, policy and environment config paths. **Met.**
- Task failure stays a successful job with `success=false`; no failures occurred in
  this run, so the branch is covered by tests only. **Not exercised.**
- Harness/runtime failures produce typed job failures: the first π₀.₅ attempt failed
  at model load (see below) before any job existed, so the worker's failure path was
  not exercised here. **Not exercised.**
- No secret in logs, artifacts, API responses: verified by scan of the committed
  evidence; one deployment script echoed a store password into a host-local log, which
  was scrubbed. **Met, with that caveat.**
- Fixture documentation distinguishes upstream reproduction evidence from this run:
  the Rollout's `evidence_note` and `evaluation_job_id` do. **Met.**

## Decisions made during implementation

- **MolmoAct2 ran first, not π₀.₅.** LeRobot's π₀.₅ loads its PaliGemma base from
  `google/paligemma-3b-pt-224`, which is gated; the server exits at load without a
  Hugging Face token whose account has accepted the Gemma terms. The catalog's
  `weights: open` for π₀.₅ is misleading in practice and should be revised. π₀.₅ runs
  as soon as a token is present; the matched Goal pair then needs only that run.
- **One seed is one bounded harness run.** The harness treats `seed` as a run's master
  seed, and its configs run 50 episodes per task; the original adapter would have run
  500 episodes for a one-seed request. Each requested seed now becomes one run with
  `EPISODES_PER_TASK` episodes per task (default 1), its own output directory and
  measured duration, mapped to one Rollout.
- **Server readiness is polled.** The harness client does not retry a refused
  connection, and a cold start includes building the server's own environment. The
  adapter waits on `/health` for up to `SERVER_READY_TIMEOUT_S` and logs the server to
  a file that is uploaded as an artifact.
- **Videos are always requested** (`--record-video`); the harness writes none by
  default.
- **The pinned MinIO images no longer exist** on Docker Hub or quay; the compose file
  now pins Bitnami legacy images verified by digest. A maintained store must replace
  them before any public deployment.
- **Single-box topology** instead of the TLS runbook for this first run; the harness's
  model server owns port 8000, so the API moved to 8800.

## Progress log

- 2026-10-02 — First RoboRouter-executed Rollout (MolmoAct2, LIBERO Goal, seed 7,
  10/10). π₀.₅ blocked on gated PaliGemma access; next is that run and the matched pair.

## Open items

- Obtain gated access and run π₀.₅ on LIBERO Object (this plan's original target) and
  on Goal for the matched pair.
- Revise the π₀.₅ catalog entry's availability to reflect the gated base model.
- `model-server-ready.json` and the aggregate JSON upload as `observation_trace` by
  suffix; the artifact kind vocabulary has no better fit yet.
- Exercise the task-failure and runtime-failure paths against a real worker.
