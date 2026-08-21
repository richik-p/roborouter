"use client";

import Link from "next/link";
import { CircleDashed, ServerCog, Square } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { cancelEvaluation, getEvaluation, listEvaluationRollouts } from "@/lib/api";
import type { EvaluationJob, Rollout } from "@/lib/types";

export default function EvaluationDetail() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<EvaluationJob | null>(null);
  const [rollouts, setRollouts] = useState<Rollout[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [canceling, setCanceling] = useState(false);
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const refresh = async () => {
      try {
        const current = await getEvaluation(id);
        setJob(current);
        if (current.state === "SUCCEEDED") setRollouts(await listEvaluationRollouts(id));
        if (!["SUCCEEDED", "FAILED", "CANCELED"].includes(current.state)) {
          timer = setTimeout(refresh, 4000);
        }
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Could not load evaluation");
      }
    };
    refresh();
    return () => clearTimeout(timer);
  }, [id]);

  async function cancel() {
    setCanceling(true);
    try {
      setJob(await cancelEvaluation(id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not cancel evaluation");
    } finally {
      setCanceling(false);
    }
  }
  if (error) return <div className="detail"><div className="error">{error}</div></div>;
  if (!job) return <div className="detail loading">Creating evaluation identity…</div>;
  return (
    <article className="detail">
      <div className="eyebrow"><CircleDashed size={14} /> Evaluation job</div>
      <div className="detail-top"><div><h1>{job.state.toLowerCase()}</h1><p className="detail-lead">{job.id}</p></div><span className="tag blue"><ServerCog size={13} /> {job.worker_id ?? "awaiting worker"}</span></div>
      <div className="timeline"><span className="active">QUEUED</span><span className={job.state !== "QUEUED" ? "active" : ""}>CLAIMED</span><span className={job.state === "RUNNING" || job.state === "SUCCEEDED" ? "active" : ""}>RUNNING</span><span className={job.state === "SUCCEEDED" ? "active" : ""}>PERSISTED</span></div>
      {["QUEUED", "CLAIMED", "RUNNING"].includes(job.state) && <button className="button" onClick={cancel} disabled={canceling}><Square size={13} /> {canceling ? "Canceling…" : "Cancel evaluation"}</button>}
      <div className="panel"><h2>Exact request</h2>{Object.entries(job.request).map(([key, value]) => <div className="kv" key={key}><span>{key}</span><code>{Array.isArray(value) ? value.join(", ") : value}</code></div>)}</div>
      {job.state === "QUEUED" && <div className="evidence-note" style={{ marginTop: 16 }}><strong>Waiting for a compatible NVIDIA worker</strong><br />The local product is useful without CUDA. A worker with the pinned vla-eval and LeRobot runtime must claim this job.</div>}
      {job.state === "CANCELED" && <div className="evidence-note" style={{ marginTop: 16 }}><strong>Evaluation canceled</strong><br />A canceled job cannot be claimed or completed.</div>}
      {job.state === "SUCCEEDED" && <div className="panel"><h2>Persisted Rollouts</h2>{rollouts.length ? rollouts.map((rollout) => <div className="kv" key={rollout.id}><span>{rollout.success ? "Successful episode" : "Unsuccessful outcome"}</span><Link href={`/rollouts/${rollout.id}`}>{rollout.id}</Link></div>) : <p>No episode Rollouts were returned.</p>}</div>}
      {job.failure_detail && <div className="error">{job.failure_kind}: {job.failure_detail}</div>}
    </article>
  );
}
