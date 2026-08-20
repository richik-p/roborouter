"use client";

import { CircleDashed, ServerCog } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getEvaluation } from "@/lib/api";
import type { EvaluationJob } from "@/lib/types";

export default function EvaluationDetail() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<EvaluationJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const refresh = () => getEvaluation(id).then(setJob).catch((reason: Error) => setError(reason.message));
    refresh();
    const timer = setInterval(refresh, 4000);
    return () => clearInterval(timer);
  }, [id]);
  if (error) return <div className="detail"><div className="error">{error}</div></div>;
  if (!job) return <div className="detail loading">Creating evaluation identity…</div>;
  return (
    <article className="detail">
      <div className="eyebrow"><CircleDashed size={14} /> Evaluation job</div>
      <div className="detail-top"><div><h1>{job.state.toLowerCase()}</h1><p className="detail-lead">{job.id}</p></div><span className="tag blue"><ServerCog size={13} /> remote worker</span></div>
      <div className="timeline"><span className="active">QUEUED</span><span className={job.state !== "QUEUED" ? "active" : ""}>CLAIMED</span><span className={job.state === "RUNNING" || job.state === "SUCCEEDED" ? "active" : ""}>RUNNING</span><span className={job.state === "SUCCEEDED" ? "active" : ""}>PERSISTED</span></div>
      <div className="panel"><h2>Exact request</h2>{Object.entries(job.request).map(([key, value]) => <div className="kv" key={key}><span>{key}</span><code>{Array.isArray(value) ? value.join(", ") : value}</code></div>)}</div>
      {job.state === "QUEUED" && <div className="evidence-note" style={{ marginTop: 16 }}><strong>Waiting for a compatible NVIDIA worker</strong><br />The local product is useful without CUDA. A worker with the pinned vla-eval and LeRobot runtime must claim this job.</div>}
      {job.failure_detail && <div className="error">{job.failure_kind}: {job.failure_detail}</div>}
    </article>
  );
}
