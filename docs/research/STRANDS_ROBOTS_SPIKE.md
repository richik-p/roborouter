# Strands Robots spike

**Run:** 2026-10-02 on an AWS g5.2xlarge (NVIDIA A10G 24 GB, Amazon Linux 2023,
driver 595.91.07) against `strands-robots` 0.5.2 from PyPI.

**Question:** can `rr-agent` be built on Strands Robots instead of from scratch?

## Verdict

Yes for the policy layer, no for the robot-side loop.

- **Reuse:** the `Policy` interface (`get_actions(observation, instruction)`), the
  LeRobot-backed providers behind it, and the robot-to-model embodiment maps. A real
  VLA ran through that interface unchanged, and a custom policy took about ten lines.
- **Do not reuse for shadow sessions:** the hardware `Robot`. Every rollout on that
  path reaches `send_action`; there is no predict-without-actuating mode. Shadow has
  to be a separate loop with no actuator code path, which is what `SAFETY.md`
  requires anyway ("structural, not a UI toggle").
- **RoboRouter still owns:** the shadow loop, execution identity, checkpoint
  pinning, and safety authority. Strands results carry none of the first three.

All three Rollouts and the draft RobotProfile emitted by the spike validate against
the existing `roborouter_contracts` models without any contract change.

## What ran

| # | Experiment | Result |
|---|---|---|
| E1 | Seeded SO-100 rollout with video, mock policy, CPU | Success; 150 steps in 5.1 s; real rendered frames |
| E2 | Same seed in two fresh simulations | Final joint state bitwise identical |
| E3 | Built-in benchmark, 3 episodes, seed 7, twice | Identical per-episode seeds and outcomes |
| E4a | Structural shadow: policy reads observations, nothing actuates | 50 calls; state delta exactly 0.0; 0 actuation calls |
| E4b | Baseline versus shadow through the observer hook | 60 paired executed/predicted actions; custom policy worked |
| E5 | Emit RoboRouter `Rollout` (sim, shadow) and `RobotProfile` | All validate against the real contracts |
| G1 | Load `allenai/MolmoAct2-SO100_101` at a pinned revision | Loaded from a local snapshot; 11.0 GB VRAM |
| G2 | Structural shadow with that real VLA | 30-action chunks; state delta 0.0; all integrity flags clean |
| G3 | Simulated rollout with the real VLA and video | Success status; 90 actions applied, 0 errors |
| G4 | Emit the real-VLA shadow `Rollout` | Validates against the real contract |

G3 ran 1.8 simulated seconds with no success criterion. It shows the pipeline works;
it says nothing about whether the policy completes the task.

## Measured against RoboRouter requirements

| Requirement | Strands 0.5.2 | Consequence |
|---|---|---|
| `observe()` | `get_observation` returns joint values and camera frames in one flat dict | Usable as is |
| `inspect_capabilities() -> RobotProfile` | Joint names, camera names, and resolution are derivable; units, frames, and rates are not declared | Draft profiles only, marked unverified |
| `validate_action`, limits | Hardware path has a relative-target clamp, joint limits, a rate throttle, and one rollout per bus | Useful, but not exercised here (no hardware) |
| `hold()`, `disarm()` | `stop()` and an operator consent gate in the dashboard | Fault latching and stale-action handling not verified |
| Shadow is structural | No such mode on the hardware path | RoboRouter writes the loop; prototype in `strands-spike/` |
| Rollout records exact identity | Result has no versions, checkpoint revision, asset revision, or seed | RoboRouter stamps identity itself |
| Policy revisions are immutable | `revision=` is refused for this checkpoint type | Download the exact revision, load from the directory |
| No arbitrary remote Python in trusted workers | Local policies need `STRANDS_TRUST_REMOTE_CODE=1`; this checkpoint ships six Python files | Allowlist checkpoints and load only pinned snapshots |

The pinning workaround is the same thing the evaluation worker already does with
`snapshot_download(repo_id, revision)`.

## Numbers

- Simulation-only install: 7 s, 611 MB, no GPU and no torch.
- GPU policy stack (`[molmoact2]` extra): 46 s, 5.6 GB; torch 2.11.0, LeRobot 0.6.1.
- First simulation start: 43 s (one-time asset download), then about 2 s per 100 steps.
- MolmoAct2 SO-100/101: 21.78 GB snapshot, 137 s to download, 391 s to load.
- VRAM: 11.0 GB after load, 11.9 GB peak. A 24 GB A10G is sufficient.
- Inference: 3.7 s for the first call, then about 296 ms per 30-action chunk.
- All CPU experiments together: 24 s.

## Defects and rough edges

- Their example `examples/vla/molmoact2_so101_debug.py --checkpoint ...` fails: it
  never adds the `front` and `wrist` cameras the checkpoint requires. The refusal is
  fast and precise, and happens before any download.
- `lerobot/act_so101`, used in three places in their docs, returns 401 on the Hub.
- The documented `benchmark-libero` extra exists in neither v0.5.2 nor `main`. The
  built-in benchmarks are five locomotion tasks, so this is not a LIBERO evaluation
  backend today.
- The headline `Agent(tools=[robot])` path needs an LLM provider. It was not
  exercised; every experiment here called the tools directly.

## Stability

`main` was 549 commits past v0.5.2 after 15 days, with hundreds of changed lines in
each core file, and two install extras were renamed or removed. The seams this spike
depends on were identical in both: the three abstract members of `Policy`, the
versioned observer event fields, and the `run_policy` and `get_observation`
parameters. Registries only grew (74 to 76 robots, 14 to 16 providers, 33 to 35
embodiment maps).

Conclusion: pin an exact release and keep the dependency behind a thin adapter.

## Not tested

Real hardware, the ROS 2 bridge, the LLM agent path, the Isaac and Newton backends,
task success, and fault behavior (network loss, stale actions, reconnect).

## Proposed `rr-agent` shape

1. Read observations from the robot through LeRobot or a read-only ROS 2 bridge.
   The process has no command path.
2. Call a Strands `Policy` loaded from a pinned local snapshot.
3. Record predicted action chunks, timing, and the embodiment map used.
4. Where the owner's controller is running, record its executed actions alongside
   and report divergence.
5. Stamp execution identity and emit a `mode="shadow"` Rollout to the control plane.

Actuation stays out of scope until an M6 ExecPlan, as before.

## Reproduce

```bash
uv venv --python 3.12 venv && source venv/bin/activate
uv pip install "strands-robots[sim-mujoco]==0.5.2"
MUJOCO_GL=egl python docs/research/strands-spike/spike_strands.py
```

The GPU part needs `strands-robots[sim-mujoco,molmoact2]==0.5.2`, an NVIDIA GPU with
12 GB or more, and `STRANDS_TRUST_REMOTE_CODE=1`; run `spike_gpu.py` the same way.
Both scripts write to `~/spike/out/`.

## Evidence

In [`strands-spike/`](strands-spike/): both scripts, `cpu_report.json`,
`gpu_report.json`, the three emitted Rollouts, and `robot_profile_draft.json`. The
real-VLA run used checkpoint revision `152569fe57914d97be91055800035f54e250d009`
and MuJoCo Menagerie revision `bf756430b615819654b640f321c71ba5c3ebeef8`. Videos and
action traces were kept out of Git.
