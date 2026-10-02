"""RoboRouter x Strands Robots spike (CPU experiments). Writes ~/spike/out/report/*."""
import asyncio, dataclasses, hashlib, importlib.metadata as md, inspect, json, os, platform, subprocess, sys, time, traceback, warnings
from datetime import datetime, timezone
from pathlib import Path
warnings.filterwarnings("ignore")
import numpy as np
from strands_robots import MockPolicy, Policy, Robot

OUT = Path.home() / "spike/out/report"; OUT.mkdir(parents=True, exist_ok=True)
REPORT = {}
JOINTS = lambda obs: {k: float(v) for k, v in obs.items() if not isinstance(v, np.ndarray) and not k.endswith(".vel")}

def section(name):
    def deco(fn):
        print(f"\n━━━ {name} ━━━", flush=True)
        try: REPORT[name] = fn(); print("  ->", json.dumps(REPORT[name], default=str)[:900])
        except Exception as e:
            REPORT[name] = {"error": f"{type(e).__name__}: {e}"}; print("  !! ", REPORT[name]["error"][:500]); traceback.print_exc(limit=3)
    return deco

def sha256_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jblock(res): return next((b["json"] for b in res.get("content", []) if "json" in b), {})
def tblock(res): return " | ".join(b.get("text", "")[:300] for b in res.get("content", []) if "text" in b)

def new_sim():
    sim = Robot("so100", mesh=False)
    sim.add_object(name="cube", shape="box", position=[0.2, 0.0, 0.05], size=[0.025]*3, color=[1, 0, 0, 1], mass=0.05)
    sim.add_camera(name="front", position=[0.5, 0.0, 0.4], target=[0.2, 0, 0.05])
    return sim

def identity():
    men = next(iter(Path.home().glob(".cache/**/mujoco_menagerie")), None)
    men_sha = subprocess.run(["git", "-C", str(men), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() if men else "unknown"
    return {"strands_robots": md.version("strands-robots"), "strands_agents": md.version("strands-agents"), "mujoco": md.version("mujoco"),
            "numpy": md.version("numpy"), "python": platform.python_version(), "mujoco_gl": os.environ.get("MUJOCO_GL", ""),
            "mujoco_menagerie_revision": men_sha, "platform": platform.platform(), "robot_asset": "so100 (strands registry)"}

class HoldPolicy(Policy):
    """Custom provider written against the Strands Policy ABC: command the current pose."""
    def __init__(self): self._keys = []
    @property
    def provider_name(self): return "roborouter_hold"
    def set_robot_state_keys(self, robot_state_keys): self._keys = list(robot_state_keys)
    async def get_actions(self, observation_dict, instruction, **kwargs):
        return [{k: float(observation_dict.get(k, 0.0)) for k in self._keys}]

def call_policy(policy, obs, instruction):
    if hasattr(policy, "get_actions_sync"): return policy.get_actions_sync(obs, instruction)
    return asyncio.run(policy.get_actions(obs, instruction))

@section("E0 identity")
def _(): return identity()

@section("E1 seeded rollout + video")
def _():
    sim = new_sim(); video_path = OUT / "e1_rollout.mp4"; tried = []
    for video in ({"path": str(video_path), "camera": "front"}, {"output_path": str(video_path), "camera": "front"}, {"video_path": str(video_path)}):
        t0 = time.time(); started = datetime.now(timezone.utc)
        res = sim.run_policy(robot_name="so100", policy_object=MockPolicy(), instruction="pick up the red cube", n_steps=150, seed=7, video=video)
        tried.append({"video_keys": sorted(video), "status": res["status"], "text": tblock(res)[:260]})
        if res["status"] == "success": break
    j = jblock(res)
    out = {"status": res["status"], "wall_s": round(time.time() - t0, 2), "attempts": tried, "result_keys": sorted(j), "video_path": j.get("video_path"),
           "video_bytes": Path(j["video_path"]).stat().st_size if j.get("video_path") and Path(j["video_path"]).exists() else None,
           "seed_echoed": "seed" in j, "identity_fields_in_result": [k for k in j if any(s in k for s in ("version", "revision", "sha", "checkpoint", "commit"))]}
    out["_started"] = started.isoformat(); out["_json"] = {k: v for k, v in j.items() if not isinstance(v, (list, dict))}
    return out

@section("E2 physics determinism (same seed, fresh sims)")
def _():
    finals = []
    for _i in range(2):
        sim = new_sim(); sim.run_policy(robot_name="so100", policy_object=MockPolicy(), instruction="x", n_steps=120, seed=7)
        finals.append(JOINTS(sim.get_observation("so100", skip_images=True)))
    diff = max(abs(finals[0][k] - finals[1][k]) for k in finals[0])
    return {"max_abs_joint_diff": diff, "bitwise_identical": diff == 0.0, "final_joints": {k: round(v, 5) for k, v in finals[0].items()}}

@section("E3 benchmark evaluation (go2_walk_forward, mock, seed=7, x2)")
def _():
    from strands_robots.simulation import register_builtin_benchmarks
    from strands_robots.simulation.benchmark import list_benchmarks
    register_builtin_benchmarks(); reg = list_benchmarks(); runs = []
    for _i in range(2):
        sim = Robot(reg["go2_walk_forward"]["default_robot"], mesh=False); t0 = time.time()
        res = sim.evaluate_benchmark("go2_walk_forward", policy_provider="mock", n_episodes=3, seed=7)
        j = jblock(res); runs.append({"status": res["status"], "wall_s": round(time.time() - t0, 1), "success_rate": j.get("success_rate"), "avg_reward": j.get("avg_reward"),
                                      "episodes": [{k: e.get(k) for k in ("seed", "steps", "success", "reward", "total_reward") if k in e} for e in j.get("episodes", [])]})
    ep_keys = sorted(jblock(res).get("episodes", [{}])[0].keys())
    return {"benchmarks": {k: v.get("default_robot") for k, v in reg.items()}, "episode_record_keys": ep_keys, "runs": runs,
            "reproducible": runs[0]["episodes"] == runs[1]["episodes"], "aggregate_keys": sorted(jblock(res))}

@section("E4a structural shadow: policy sees observations, nothing actuates")
def _():
    sim = new_sim(); policy = MockPolicy(); obs0 = sim.get_observation("so100"); keys = list(JOINTS(obs0)); policy.set_robot_state_keys(keys)
    before = JOINTS(sim.get_observation("so100", skip_images=True)); trace = OUT / "e4a_predicted_actions.jsonl"; lat = []
    with trace.open("w") as f:
        for t in range(50):
            obs = sim.get_observation("so100"); t0 = time.perf_counter()
            actions = call_policy(policy, obs, "pick up the red cube"); lat.append((time.perf_counter() - t0) * 1e3)
            f.write(json.dumps({"t": t, "state": JOINTS(obs), "predicted": actions}, default=float) + "\n")
    after = JOINTS(sim.get_observation("so100", skip_images=True))
    return {"steps": 50, "chunk_len": len(actions), "action_keys": sorted(actions[0]) if actions else [], "state_delta_max": max(abs(after[k] - before[k]) for k in before),
            "actuation_calls": 0, "avg_policy_ms": round(float(np.mean(lat)), 3), "trace": str(trace), "obs_camera_keys": [k for k, v in obs0.items() if isinstance(v, np.ndarray)],
            "camera_shape": list(next(v for v in obs0.values() if isinstance(v, np.ndarray)).shape)}

@section("E4b baseline-vs-shadow via observer hook (executed=Mock, shadow=custom HoldPolicy)")
def _():
    from strands_robots.simulation import observers as ob
    fields = {n: [f.name for f in dataclasses.fields(getattr(ob, n))] for n in ("RunPolicyStarted", "RunPolicyStep", "RunPolicyEnded") if dataclasses.is_dataclass(getattr(ob, n, None))}
    sim = new_sim(); shadow = HoldPolicy(); keys = list(JOINTS(sim.get_observation("so100", skip_images=True))); shadow.set_robot_state_keys(keys)
    rows = []; errors = []
    def observer(ev):
        if type(ev).__name__ != "RunPolicyStep": return
        try:
            obs = getattr(ev, "observation", None) or sim.get_observation("so100", skip_images=True)
            executed = getattr(ev, "action", None)
            predicted = asyncio.run(shadow.get_actions(obs, "pick up the red cube"))[0]
            rows.append({"step": getattr(ev, "step", len(rows)), "executed": executed, "shadow_predicted": predicted})
        except Exception as e: errors.append(f"{type(e).__name__}: {e}")
    res = sim.run_policy(robot_name="so100", policy_object=MockPolicy(), instruction="pick up the red cube", n_steps=60, seed=7, observer=observer)
    trace = OUT / "e4b_baseline_vs_shadow.jsonl"; trace.write_text("\n".join(json.dumps(r, default=float) for r in rows))
    div = None
    if rows and isinstance(rows[0]["executed"], dict):
        common = [k for k in rows[0]["shadow_predicted"] if k in rows[0]["executed"]]
        if common: div = round(float(np.mean([abs(float(r["executed"][k]) - r["shadow_predicted"][k]) for r in rows for k in common])), 5)
    return {"status": res["status"], "observer_event_fields": fields, "rows": len(rows), "observer_errors": errors[:2], "mean_abs_divergence": div,
            "executed_sample": rows[0]["executed"] if rows else None, "custom_policy_abc_ok": True, "trace": str(trace)}

@section("E5 emit RoboRouter-shaped Rollouts + draft RobotProfile")
def _():
    ident = {k: str(v) for k, v in identity().items()}; e1 = REPORT.get("E1 seeded rollout + video", {}); e4 = REPORT.get("E4a structural shadow: policy sees observations, nothing actuates", {})
    def art(aid, kind, path, media):
        p = Path(path); return {"id": aid, "kind": kind, "uri": f"file://{p}", "media_type": media, "sha256": sha256_file(p), "size_bytes": p.stat().st_size}
    base = dict(policy_spec_id="strands-mock", policy_revision="strands-robots-0.5.2", robot_profile_id="sim-so100-mujoco", robot_revision="spike-2026-10-02",
                task_profile_id="so100-cube-reach-spike", task_revision="spike-2026-10-02", environment_id="strands-mujoco-so100", environment_revision="strands-robots-0.5.2-mujoco-" + ident["mujoco"], seed=7)
    arts = [art("art-e1-video", "video", e1["video_path"], "video/mp4")] if e1.get("video_path") and Path(e1["video_path"]).exists() else []
    j = e1.get("_json", {})
    sim_rollout = dict(base, id="rollout-spike-strands-sim", mode="sim", started_at=e1.get("_started"), duration_ms=int(float(j.get("elapsed_s", 0)) * 1000), success=False,
                       metrics={"steps_used": int(j.get("steps_used", 0)), "actions_applied": int(j.get("actions_applied", 0)), "action_errors": int(j.get("action_errors", 0)), "success_measured": False},
                       runtime_identity=ident, artifacts=arts, safety={"physical_system_connected": False},
                       evidence_note="Spike: Strands MockPolicy on the so100 MuJoCo sim. No success criterion; proves the record shape only.")
    shadow_rollout = dict(base, id="rollout-spike-strands-shadow", mode="shadow", started_at=datetime.now(timezone.utc).isoformat(), duration_ms=0, success=False,
                          metrics={"steps": int(e4.get("steps", 0)), "state_delta_max": float(e4.get("state_delta_max", -1)), "actuation_calls": 0, "success_measured": False},
                          runtime_identity=ident, artifacts=[art("art-e4a-predicted", "predicted_action_trace", e4["trace"], "application/x-ndjson")] if e4.get("trace") else [],
                          safety={"predicted_actions_executed": False, "actuation_path_present": False, "observation_source": "simulated (stand-in for real sensors)"},
                          evidence_note="Spike: structural shadow loop using only the Strands Policy interface; no send_action path exists in the loop.")
    sim = new_sim(); obs = sim.get_observation("so100"); joints = list(JOINTS(obs)); cams = {k: v.shape for k, v in obs.items() if isinstance(v, np.ndarray)}
    profile = {"id": "sim-so100-mujoco", "revision": "spike-2026-10-02", "name": "SO-100 (Strands MuJoCo sim)", "robot_class": "manipulator.single_arm", "manufacturer": "TheRobotStudio",
               "model": "SO-100", "middleware": "strands_robots.mujoco", "simulated": True,
               "sensors": [{"id": "joint_state", "type": "proprioception.joint_position", "dimensions": len(joints)}] +
                          [{"id": name, "type": "vision.rgb", "semantic_name": name, "resolution": [int(s[1]), int(s[0])]} for name, s in cams.items()],
               "control_surfaces": [{"schema": "manipulation.joint_position.v1", "dimensions": len(joints), "frame": "joint", "units": ["rad"] * len(joints)}],
               "safety_capabilities": {"hardware_estop": False, "local_limits": True}}
    for name, obj in (("rollout_sim", sim_rollout), ("rollout_shadow", shadow_rollout), ("robot_profile_draft", profile)): (OUT / f"{name}.json").write_text(json.dumps(obj, indent=1, default=str))
    return {"written": ["rollout_sim.json", "rollout_shadow.json", "robot_profile_draft.json"], "joint_names": joints, "cameras": {k: list(v) for k, v in cams.items()}, "artifacts": len(arts)}

(OUT / "report.json").write_text(json.dumps(REPORT, indent=1, default=str))
print("\nreport written:", OUT / "report.json")
