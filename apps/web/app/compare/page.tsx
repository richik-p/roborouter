"use client";

import Link from "next/link";
import { Play } from "lucide-react";
import { useEffect, useState } from "react";
import { createEvaluation, getPolicy } from "@/lib/api";
import type { EvaluationJob, Policy } from "@/lib/types";

const goalOptions = {
  environmentId: "vla-eval-libero-goal",
  environmentRevision: "vla-eval-0.4.0-lerobot-0.6.0-libero-2a4566009395",
  taskId: "libero-goal-interaction",
  taskRevision: "2026-08-20.1",
  seeds: [7],
};

export default function Compare() {
  const [policies, setPolicies] = useState<Record<string, Policy>>({});
  const [jobs, setJobs] = useState<Record<string, EvaluationJob>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getPolicy("pi05-libero"), getPolicy("molmoact2-libero")])
      .then(([pi05, molmo]) => setPolicies({ [pi05.id]: pi05, [molmo.id]: molmo }))
      .catch((reason: Error) => setError(reason.message));
  }, []);

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
      <p className="detail-lead">π₀.₅ and MolmoAct2 share the LIBERO Goal protocol. Results are only labeled matched when suite, task, seeds, evaluator, observation/action contract, and protocol revision agree.</p>
      {error && <div className="error">{error}</div>}
      <div className="compare-grid">
        <div className="compare-label">Policy</div><div><strong>π₀.₅</strong><br /><span className="mono">lerobot/pi05_libero_finetuned</span></div><div><strong>MolmoAct2</strong><br /><span className="mono">allenai/MolmoAct2-LIBERO</span></div>
        <div className="compare-label">Upstream evidence</div><div><strong>98%</strong><br />LIBERO Goal reported</div><div><strong>97%</strong><br />LIBERO Goal reproduced</div>
        <div className="compare-label">Runtime</div><div>LeRobot 0.6.0<br />vla-eval 0.4.0</div><div>LeRobot bridge<br />vla-eval 0.4.0</div>
        <div className="compare-label">RoboRouter run</div>
        {(["pi05-libero", "molmoact2-libero"] as const).map((policyId) => (
          <div key={policyId}>
            {jobs[policyId] ? <Link className="tag blue" href={`/evaluations/${jobs[policyId].id}`}>{jobs[policyId].state}</Link> : <button className="button accent" onClick={() => launch(policyId)} disabled={!policies[policyId]}><Play size={14} /> Queue matched run</button>}
          </div>
        ))}
      </div>
      <div className="evidence-note" style={{ marginTop: 18 }}>Upstream aggregate results are context, not a RoboRouter leaderboard. A matched comparison becomes evidence only after both policies complete this exact evaluation set.</div>
    </section>
  );
}
