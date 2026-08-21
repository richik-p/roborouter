"use client";

import Link from "next/link";
import { ArrowLeft, Check, Database, FileCheck2, Fingerprint } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getRollout } from "@/lib/api";
import type { Rollout } from "@/lib/types";

export default function RolloutDetail() {
  const { id } = useParams<{ id: string }>();
  const [rollout, setRollout] = useState<Rollout | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { getRollout(id).then(setRollout).catch((reason: Error) => setError(reason.message)); }, [id]);
  if (error) return <div className="detail"><div className="error">{error}</div></div>;
  if (!rollout) return <div className="detail loading">Resolving Rollout provenance…</div>;
  return (
    <article className="detail">
      <Link href="/" className="eyebrow"><ArrowLeft size={14} /> Back to Explore</Link>
      <div className="detail-top">
        <div><h1>Rollout evidence</h1><p className="detail-lead">A reproducible record of what ran, where it ran, and what the evaluator observed.</p></div>
        <span className="tag green"><Check size={12} /> {rollout.success ? "Successful" : "Unsuccessful"}</span>
      </div>
      {rollout.evidence_note && <div className="evidence-note"><strong>Evidence boundary</strong><br />{rollout.evidence_note}</div>}
      <div className="timeline"><span className="active">RESOLVED</span><span className="active">EXECUTED</span><span className="active">EVALUATED</span><span className="active">PERSISTED</span></div>
      <div className="metric-grid">
        {Object.entries(rollout.metrics).map(([key, value]) => <div className="metric" key={key}><span className="mono">{key.replaceAll("_", " ")}</span><strong>{String(value)}</strong></div>)}
      </div>
      <div className="detail-grid">
        <section className="panel"><h2><Fingerprint size={17} /> Policy and task</h2><div className="kv"><span>Policy</span><code>{rollout.policy_spec_id}</code></div><div className="kv"><span>Revision</span><code>{rollout.policy_revision}</code></div><div className="kv"><span>Robot</span><code>{rollout.robot_profile_id}</code></div><div className="kv"><span>Task</span><code>{rollout.task_profile_id}</code></div></section>
        <section className="panel"><h2><Database size={17} /> Runtime identity</h2>{Object.entries(rollout.runtime_identity).map(([key, value]) => <div className="kv" key={key}><span>{key}</span><code>{value}</code></div>)}</section>
        <section className="panel full"><h2>Environment</h2><div className="kv"><span>Environment</span><code>{rollout.environment_id}</code></div><div className="kv"><span>Revision</span><code>{rollout.environment_revision}</code></div><div className="kv"><span>Seed</span><code>{rollout.seed}</code></div><div className="kv"><span>Mode</span><span className="tag blue">{rollout.mode}</span></div></section>
        <section className="panel full"><h2><FileCheck2 size={17} /> Immutable artifacts</h2>{rollout.artifacts.length ? rollout.artifacts.map((artifact) => <div className="kv" key={artifact.id}><span>{artifact.kind} · {artifact.size_bytes} bytes</span><code title={artifact.uri}>{artifact.sha256}</code></div>) : <p>No artifacts are attached to this Rollout.</p>}</section>
      </div>
    </article>
  );
}
