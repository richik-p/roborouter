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

## Current blocker

No CUDA-capable remote worker is available in the local workspace. Consequently this
plan is executable but has not been performed; M0-03, M2-03, and matched M3 evidence
remain open.
