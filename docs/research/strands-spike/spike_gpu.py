"""RoboRouter x Strands spike, GPU part: a real VLA (MolmoAct2 SO-100/101) in shadow and in sim."""
import asyncio, hashlib, importlib.metadata as md, json, os, platform, subprocess, time, traceback, warnings
from datetime import datetime, timezone
from pathlib import Path
warnings.filterwarnings("ignore")
import numpy as np, torch
from strands_robots import Robot
from strands_robots.policies import create_policy

CKPT, REV, ROBOT = "allenai/MolmoAct2-SO100_101", "152569fe57914d97be91055800035f54e250d009", "so101"
INSTR = "pick up the red cube"
OUT = Path.home() / "spike/out/gpu"; OUT.mkdir(parents=True, exist_ok=True); R = {}
JOINTS = lambda obs: {k: float(v) for k, v in obs.items() if not isinstance(v, np.ndarray) and not k.endswith(".vel")}
def jblock(res): return next((b["json"] for b in res.get("content", []) if "json" in b), {})
def tblock(res): return " | ".join(b.get("text", "")[:500] for b in res.get("content", []) if "text" in b)
def vram(): return {"allocated_gb": round(torch.cuda.memory_allocated() / 1e9, 2), "peak_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2)}
def step(name, fn):
    print(f"\n━━━ {name} ━━━", flush=True)
    try: R[name] = fn(); print("  ->", json.dumps(R[name], default=str)[:1400], flush=True)
    except Exception as e:
        R[name] = {"error": f"{type(e).__name__}: {str(e)[:900]}"}; print("  !!", R[name]["error"], flush=True); traceback.print_exc(limit=4)
    (OUT / "gpu_report.json").write_text(json.dumps(R, indent=1, default=str))

def new_sim():
    sim = Robot(ROBOT, mesh=False)
    sim.add_object(name="cube", shape="box", position=[0.22, 0.0, 0.03], size=[0.02] * 3, color=[1, 0, 0, 1], mass=0.05)
    sim.add_camera(name="front", position=[0.22, 0.025, 0.6], target=[0.22, 0.025, 0])
    sim.add_camera(name="wrist", parent_body="so101/gripper", position=[0.058, 0.0, -0.029], target=[-0.024, 0.0, -0.297])
    return sim

def g0():
    smi = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    return {"gpu": smi, "torch": torch.__version__, "cuda": torch.version.cuda, "lerobot": md.version("lerobot"), "transformers": md.version("transformers"),
            "strands_robots": md.version("strands-robots"), "mujoco": md.version("mujoco"), "python": platform.python_version(), "checkpoint": CKPT, "checkpoint_revision": REV}
step("G0 identity", g0)

POLICY = {}
def g1():
    # Strands refuses revision= for transformers-native MolmoAct2 checkpoints, so pin the RoboRouter way:
    # download the exact revision and load from the local snapshot directory.
    from huggingface_hub import snapshot_download
    t0 = time.time(); local = snapshot_download(repo_id=CKPT, revision=REV); dl = round(time.time() - t0, 1)
    size_gb = round(sum(f.stat().st_size for f in Path(local).rglob("*") if f.is_file()) / 1e9, 2)
    t0 = time.time()
    POLICY["p"] = create_policy("lerobot_local", pretrained_name_or_path=local, embodiment=ROBOT, inference_action_mode="continuous", device="cuda")
    p = POLICY["p"]
    return {"snapshot_download_s": dl, "snapshot_gb": size_gb, "snapshot_dir_ends_with_revision": Path(local).name == REV, "create_s": round(time.time() - t0, 1), "provider": p.provider_name, "vram_after_create": vram(), "requires_images": getattr(p, "requires_images", None),
            "load_time_s": getattr(p, "load_time_s", None), "public": [n for n in dir(p) if not n.startswith("_")][:40]}
step("G1 load pinned checkpoint", g1)

def g2():
    if "p" not in POLICY: return {"skipped": "policy did not load"}
    p = POLICY["p"]; sim = new_sim(); obs0 = sim.get_observation(ROBOT); keys = list(JOINTS(obs0)); p.set_robot_state_keys(keys)
    try: p.preflight(set(obs0.keys())); pre = "ok"
    except Exception as e: pre = f"{type(e).__name__}: {str(e)[:300]}"
    before = JOINTS(sim.get_observation(ROBOT, skip_images=True)); lat = []; chunks = []; trace = OUT / "g2_shadow_predicted_actions.jsonl"
    with trace.open("w") as f:
        for i in range(6):
            obs = sim.get_observation(ROBOT); t0 = time.perf_counter()
            actions = asyncio.run(p.get_actions(obs, INSTR)); lat.append(round((time.perf_counter() - t0) * 1e3, 1)); chunks.append(len(actions))
            f.write(json.dumps({"call": i, "state": JOINTS(obs), "predicted_chunk": actions}, default=float) + "\n")
    after = JOINTS(sim.get_observation(ROBOT, skip_images=True)); a0 = actions[0]
    return {"obs_keys": sorted(k for k in obs0), "state_keys": keys, "preflight": pre, "latency_ms_per_call": lat, "chunk_len": chunks, "action_keys": sorted(a0),
            "first_action": {k: round(float(v), 4) for k, v in a0.items()}, "state_delta_max": max(abs(after[k] - before[k]) for k in before), "actuation_calls": 0,
            "vram": vram(), "trace": str(trace), "integrity": {n: bool(getattr(p, n, False)) for n in ("positional_fallback_used", "generic_state_keys_used", "missing_state_keys_used")}}
step("G2 structural shadow with a real VLA", g2)

def g3():
    if "p" not in POLICY: return {"skipped": "policy did not load"}
    p = POLICY["p"]; sim = new_sim(); before = JOINTS(sim.get_observation(ROBOT, skip_images=True)); video = OUT / "g3_molmoact2_so101.mp4"
    t0 = time.time(); started = datetime.now(timezone.utc).isoformat()
    res = sim.run_policy(robot_name=ROBOT, policy_object=p, instruction=INSTR, n_steps=90, action_horizon=30, seed=7, video={"path": str(video), "camera": "front"})
    after = JOINTS(sim.get_observation(ROBOT, skip_images=True)); j = jblock(res)
    return {"status": res["status"], "wall_s": round(time.time() - t0, 1), "started": started, "text": tblock(res)[:700], "max_joint_motion_deg": round(max(abs(after[k] - before[k]) for k in before) * 57.2958, 2),
            "scalars": {k: v for k, v in j.items() if not isinstance(v, (list, dict))}, "video_bytes": video.stat().st_size if video.exists() else None, "vram": vram()}
step("G3 sim rollout with the real VLA (video)", g3)

def g4():
    if "trace" not in R.get("G2 structural shadow with a real VLA", {}): return {"skipped": "no shadow trace"}
    ident = {k: str(v) for k, v in R["G0 identity"].items()}; g2r = R["G2 structural shadow with a real VLA"]; tr = Path(g2r["trace"])
    rollout = {"id": "rollout-spike-strands-shadow-molmoact2", "mode": "shadow", "policy_spec_id": "molmoact2-so100-101", "policy_revision": f"allenai-molmoact2-so100-101-{REV[:12]}",
               "robot_profile_id": "sim-so101-mujoco", "robot_revision": "spike-2026-10-02", "task_profile_id": "so101-cube-pick-spike", "task_revision": "spike-2026-10-02",
               "environment_id": "strands-mujoco-so101", "environment_revision": f"strands-robots-{ident['strands_robots']}-mujoco-{ident['mujoco']}", "seed": 7,
               "started_at": datetime.now(timezone.utc).isoformat(), "duration_ms": int(sum(g2r["latency_ms_per_call"])), "success": False,
               "metrics": {"policy_calls": len(g2r["latency_ms_per_call"]), "chunk_len": int(g2r["chunk_len"][0]), "median_latency_ms": float(np.median(g2r["latency_ms_per_call"])),
                           "state_delta_max": float(g2r["state_delta_max"]), "actuation_calls": 0, "success_measured": False},
               "runtime_identity": ident, "artifacts": [{"id": "art-g2-predicted", "kind": "predicted_action_trace", "uri": f"file://{tr}", "media_type": "application/x-ndjson",
                                                         "sha256": hashlib.sha256(tr.read_bytes()).hexdigest(), "size_bytes": tr.stat().st_size}],
               "safety": {"predicted_actions_executed": False, "actuation_path_present": False, "observation_source": "simulated (stand-in for real sensors)", "trust_remote_code": True},
               "evidence_note": "Spike: a real VLA checkpoint at a pinned revision ran in a structural shadow loop through the Strands Policy interface; nothing was actuated."}
    (OUT / "rollout_shadow_molmoact2.json").write_text(json.dumps(rollout, indent=1)); return {"written": "rollout_shadow_molmoact2.json"}
step("G4 emit RoboRouter shadow Rollout", g4)
print("\nDONE", flush=True)
