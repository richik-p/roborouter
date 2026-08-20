import Link from "next/link";
import { ArrowDown, ArrowRight, Braces, CircleCheck, Satellite, ShieldCheck } from "lucide-react";
import Explorer from "@/components/explorer";

export default function Home() {
  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow">Compatibility intelligence for robotics</div>
          <h1>Find what your robot can <em>actually run.</em></h1>
          <p>RoboRouter turns fragmented model cards, checkpoints, simulators, and control assumptions into one evidence-backed answer for your robot and task.</p>
          <div className="hero-actions">
            <Link className="button primary" href="#explore">Explore policies <ArrowDown size={17} /></Link>
            <Link className="button" href="/rollouts/rollout-upstream-pi05-libero-object">Inspect a Rollout <ArrowRight size={17} /></Link>
          </div>
        </div>
        <div className="signal-card" aria-label="Example compatibility signal">
          <div className="signal-head"><span>ROBOROUTER / LIVE GRAPH</span><span className="signal-dot">● ONLINE</span></div>
          <div className="signal-screen">
            <div className="signal-row"><span>ROBOT</span><strong>LIBERO PANDA</strong></div>
            <div className="signal-row"><span>POLICY</span><strong>π₀.₅</strong></div>
            <div className="signal-row"><span>CONTROL</span><strong>EE DELTA POSE</strong></div>
            <div className="signal-row"><span>EVIDENCE</span><strong>SIM VERIFIED</strong></div>
            <div className="signal-wave" />
          </div>
          <div className="signal-head"><span>EXACT RUNTIME IDENTITY</span><span>NO ACTUATION</span></div>
        </div>
      </section>

      <section id="explore" className="section">
        <div className="section-head">
          <div><div className="eyebrow">Explore the graph</div><h2>Start with the machine.</h2></div>
          <p>Choose a robot and task. We expose missing sensors, action mismatches, fine-tuning needs, and the exact evidence behind every result.</p>
        </div>
        <Explorer />
      </section>

      <section className="section">
        <div className="section-head"><div><div className="eyebrow">Three proofs</div><h2>From claim to trace.</h2></div></div>
        <div className="proof-grid">
          <article className="proof-card"><span className="number">01 / DISCOVER</span><Braces size={30} /><h3>Catalog the runnable identity</h3><p>Weights, preprocessing, normalization, action semantics, runtime, and evidence stay attached to one immutable spec.</p></article>
          <article className="proof-card"><span className="number">02 / EVALUATE</span><CircleCheck size={30} /><h3>Compare without hardware</h3><p>Run pinned simulation protocols and keep metrics, videos, seeds, and environment revisions in a durable Rollout.</p></article>
          <article className="proof-card"><span className="number">03 / CONNECT</span><ShieldCheck size={30} /><h3>Keep safety local</h3><p>Shadow mode comes first. A future robot-side agent retains arming, limits, hold, and fault authority near the machine.</p></article>
        </div>
        <div style={{ marginTop: 16 }} className="proof-card">
          <span className="number">EMBODIMENT-GENERAL BY DESIGN</span><Satellite size={30} /><h3>Arms are the first runtime, not the schema boundary.</h3><p>The launch catalog includes bimanual systems, dexterous hands, mobile robots, and AeroVLA. Aerial policies use explicit PX4 high-level control surfaces instead of pretending every robot emits the same action tensor.</p>
        </div>
      </section>
    </>
  );
}

