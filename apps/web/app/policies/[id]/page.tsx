"use client";

import Link from "next/link";
import { ArrowLeft, ExternalLink, Play, ShieldAlert } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { createEvaluation, getPolicy } from "@/lib/api";
import type { Policy } from "@/lib/types";

export default function PolicyDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);

  useEffect(() => { getPolicy(id).then(setPolicy).catch((reason: Error) => setError(reason.message)); }, [id]);

  async function launch() {
    if (!policy) return;
    setLaunching(true);
    try {
      const job = await createEvaluation(policy);
      router.push(`/evaluations/${job.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create evaluation");
      setLaunching(false);
    }
  }

  if (error && !policy) return <div className="detail"><div className="error">{error}</div></div>;
  if (!policy) return <div className="detail loading">Loading exact policy identity…</div>;
  const evidence = policy.evidence[0];
  return (
    <article className="detail">
      <Link href="/#explore" className="eyebrow"><ArrowLeft size={14} /> Back to Explore</Link>
      <div className="detail-top">
        <div><h1>{policy.name}</h1><p className="detail-lead">{policy.description}</p></div>
        <button className="button accent" disabled={!policy.runtime || policy.id !== "pi05-libero" || launching} onClick={launch}>
          <Play size={16} /> {launching ? "Queueing…" : policy.id === "pi05-libero" ? "Run LIBERO eval" : "Runner unavailable"}
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="detail-grid">
        <section className="panel">
          <h2>Executable identity</h2>
          <div className="kv"><span>Family</span><strong>{policy.family}</strong></div>
          <div className="kv"><span>Revision</span><code>{policy.revision}</code></div>
          <div className="kv"><span>Checkpoint</span><code>{policy.source.checkpoint ?? "Not cataloged"}</code></div>
          <div className="kv"><span>Runtime</span><span>{policy.runtime ? `${policy.runtime.framework} ${policy.runtime.framework_revision}` : "Research metadata only"}</span></div>
          <div className="kv"><span>Availability</span><span>{policy.availability.weights} weights / {policy.availability.code} code</span></div>
        </section>
        <section className="panel">
          <h2>Interface contract</h2>
          <div className="kv"><span>Robot classes</span><span>{policy.robot_classes.join(", ")}</span></div>
          <div className="kv"><span>Tasks</span><span>{policy.task_families.join(", ").replaceAll("_", " ")}</span></div>
          <div className="kv"><span>Sensors</span><span>{policy.observations.sensor_types.join(", ")}</span></div>
          <div className="kv"><span>Cameras</span><span>{policy.observations.cameras.join(", ") || "Unknown"}</span></div>
          <div className="kv"><span>Action</span><code>{policy.actions?.schema ?? "Unknown"}</code></div>
        </section>
        <section className="panel full">
          <h2>Best available evidence</h2>
          {evidence ? <div className="evidence-note"><strong>{evidence.level.replaceAll("_", " ")}</strong><br />{evidence.description}<br /><a href={evidence.source} target="_blank" rel="noreferrer">Open primary source <ExternalLink size={13} /></a></div> : <p>No evidence is cataloged.</p>}
        </section>
        <section className="panel full">
          <h2><ShieldAlert size={17} /> Execution boundary</h2>
          <p>No physical actuation path exists in this release. Simulation jobs are isolated from future robot-side safety and arming authority.</p>
        </section>
      </div>
    </article>
  );
}

