"use client";

import Link from "next/link";
import { CheckCircle2, Play, TriangleAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import LaunchKeyField from "@/components/launch-key-field";
import { createEvaluation, getPolicy, listRollouts } from "@/lib/api";
import type { EvaluationJob, Policy, Rollout } from "@/lib/types";

const policyIds = ["pi05-libero", "molmoact2-libero"] as const;
const goalOptions = {
  environmentId: "vla-eval-libero-goal",
  environmentRevision: "vla-eval-0.4.0-lerobot-0.6.0-libero-2a4566009395",
  taskId: "libero-goal-interaction",
  taskRevision: "2026-08-20.1",
  seeds: [7],
};

function comparisonIdentity(rollout: Rollout) {
  return [
    rollout.environment_id,
    rollout.environment_revision,
    rollout.task_profile_id,
    rollout.task_revision,
    rollout.seed,
    rollout.runtime_identity.harness_revision,
    rollout.runtime_identity.container_digest,
    rollout.runtime_identity.vla_eval,
    rollout.runtime_identity.protocol,
  ].join("|");
}

function metric(rollout: Rollout | undefined) {
  if (!rollout) return "No result";
  const successRate = rollout.metrics.upstream_success_rate ?? rollout.metrics.success_rate;
  return typeof successRate === "number" ? `${Math.round(successRate * 100)}% success` : rollout.success ? "Successful" : "Unsuccessful";
}

export default function Compare() {
  const [policies, setPolicies] = useState<Record<string, Policy>>({});
  const [jobs, setJobs] = useState<Record<string, EvaluationJob>>({});
  const [rollouts, setRollouts] = useState<Record<string, Rollout>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getPolicy("pi05-libero"),
      getPolicy("molmoact2-libero"),
      listRollouts({ environmentId: goalOptions.environmentId, taskProfileId: goalOptions.taskId }),
    ])
      .then(([pi05, molmo, results]) => {
        setPolicies({ [pi05.id]: pi05, [molmo.id]: molmo });
        const latest: Record<string, Rollout> = {};
        for (const result of results) if (!latest[result.policy_spec_id]) latest[result.policy_spec_id] = result;
        setRollouts(latest);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  const matched = useMemo(() => {
    const pi05 = rollouts["pi05-libero"];
    const molmo = rollouts["molmoact2-libero"];
    return Boolean(pi05 && molmo && comparisonIdentity(pi05) === comparisonIdentity(molmo));
  }, [rollouts]);

  async function launch(policyId: string) {
    const policy = policies[policyId];
    if (!policy) return;
    try {
      const job = await createEvaluation(policy, goalOptions);
      setJobs((current) => ({ ...current, [policyId]: job }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create matched evaluation");
    }
  }

  return (
    <section className="detail">
      <div className="eyebrow">Matched protocol</div>
      <h1>Compare execution identities, not names.</h1>
      <p className="detail-lead">π₀.₅ and MolmoAct2 share the LIBERO Goal protocol. Results are matched only when the immutable environment and task revisions, seed, harness, container, evaluator contract, and protocol agree.</p>
      {error && <div className="error">{error}</div>}
      <div className="launch-controls" style={{ alignItems: "flex-start", marginBottom: 18 }}><LaunchKeyField /></div>
      <div className={`evidence-note ${matched ? "" : "error"}`} style={{ marginBottom: 18 }}>
        {matched ? <><CheckCircle2 size={16} /> <strong>Matched result set</strong> — both displayed records use the exact same evaluation identity.</> : <><TriangleAlert size={16} /> <strong>Non-comparable</strong> — both exact result identities are required.</>}
      </div>
      <div className="compare-grid">
        <div className="compare-label">Policy</div><div><strong>π₀.₅</strong><br /><span className="mono">lerobot/pi05_libero_finetuned</span></div><div><strong>MolmoAct2</strong><br /><span className="mono">allenai/MolmoAct2-LIBERO</span></div>
        <div className="compare-label">Completed result</div>{policyIds.map((policyId) => <div key={`${policyId}-result`}><strong>{metric(rollouts[policyId])}</strong>{rollouts[policyId] && <><br /><Link href={`/rollouts/${rollouts[policyId].id}`}>Open exact Rollout</Link></>}</div>)}
        <div className="compare-label">Evidence class</div>{policyIds.map((policyId) => <div key={`${policyId}-evidence`}>{rollouts[policyId]?.evaluation_job_id ? "RoboRouter execution" : "Upstream aggregate fixture"}<br /><span className="mono">seed {rollouts[policyId]?.seed ?? "—"}</span></div>)}
        <div className="compare-label">Runtime identity</div>{policyIds.map((policyId) => <div key={`${policyId}-runtime`}>LeRobot {rollouts[policyId]?.runtime_identity.lerobot ?? "—"}<br />vla-eval {rollouts[policyId]?.runtime_identity.vla_eval ?? "—"}</div>)}
        <div className="compare-label">Launch fresh run</div>
        {policyIds.map((policyId) => (
          <div key={`${policyId}-launch`}>
            {jobs[policyId] ? <Link className="tag blue" href={`/evaluations/${jobs[policyId].id}`}>{jobs[policyId].state} · open job</Link> : <button className="button accent" onClick={() => launch(policyId)} disabled={!policies[policyId]}><Play size={14} /> Queue matched run</button>}
          </div>
        ))}
      </div>
      <div className="evidence-note" style={{ marginTop: 18 }}>The initial pair is provenance-labeled upstream aggregate context, not a RoboRouter leaderboard. Fresh jobs replace context with episode Rollouts only after both complete this exact evaluation set.</div>
    </section>
  );
}
