import { Cable, Eye, ShieldCheck } from "lucide-react";

export default function Pilots() {
  return (
    <section className="detail">
      <div className="eyebrow">External robot pilot</div>
      <h1>Bring the stack that already works.</h1>
      <p className="detail-lead">We are looking for collaborators with a programmatically controlled robot, a known-good policy or controller, operator recovery, and a documented LeRobot, ROS 2, or vendor SDK interface.</p>
      <div className="proof-grid" style={{ marginTop: 44 }}>
        <article className="proof-card"><span className="number">PHASE 01</span><Cable size={28} /><h3>Read-only inspection</h3><p>Build and review a RobotProfile. No command path is installed.</p></article>
        <article className="proof-card"><span className="number">PHASE 02</span><Eye size={28} /><h3>Shadow execution</h3><p>Real observations flow through a known-good policy while predicted actions are recorded and cannot actuate.</p></article>
        <article className="proof-card"><span className="number">PHASE 03</span><ShieldCheck size={28} /><h3>Supervised validation</h3><p>Only after a separate safety review: local arming, limits, fault tests, and one low-risk known task.</p></article>
      </div>
      <div className="panel" style={{ marginTop: 18 }}><h2>Pilot intake</h2><p>Email the robot model, middleware, sensors, command interfaces, current policy/controller, attached compute, network constraints, and recovery systems to the project maintainer. No proprietary training data or cloud actuation is required.</p></div>
    </section>
  );
}
