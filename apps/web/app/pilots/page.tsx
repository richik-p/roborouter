import { Cable, Eye, ExternalLink, Mail, ShieldCheck } from "lucide-react";

const REPOSITORY_URL = process.env.NEXT_PUBLIC_REPOSITORY_URL ?? "https://github.com/richik-p/roborouter";
const CONTACT_EMAIL = process.env.NEXT_PUBLIC_PILOT_CONTACT_EMAIL;

const intakeFields = [
  "Robot model",
  "Robot class",
  "Middleware/interface (ROS 2 / LeRobot / PX4 / vendor SDK / other)",
  "Sensors/cameras",
  "State topics/APIs",
  "Command/control interfaces and control frequency",
  "Existing working policy/controller",
  "Compute attached to the robot",
  "Network/remote access constraints",
  "Hardware e-stop/manual recovery",
  "Windows when supervised testing is possible",
];

const issueUrl = `${REPOSITORY_URL}/issues/new?template=pilot_integration.md&title=${encodeURIComponent("Pilot: <robot model>")}`;
const mailtoUrl = CONTACT_EMAIL
  ? `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent("RoboRouter pilot: <robot model>")}&body=${encodeURIComponent(intakeFields.map((field) => `${field}:`).join("\n"))}`
  : null;

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
      <div className="panel" style={{ marginTop: 18 }}>
        <h2>Pilot intake</h2>
        <p>Send the details below. No proprietary training data, hardware changes, or cloud actuation are required, and you keep full control of the robot throughout.</p>
        <pre className="intake" aria-label="Pilot intake fields">{intakeFields.map((field) => `${field}:`).join("\n")}</pre>
        <div className="hero-actions" style={{ marginTop: 18 }}>
          <a className="button primary" href={issueUrl} target="_blank" rel="noreferrer">Open a pilot intake issue <ExternalLink size={16} /></a>
          {mailtoUrl && <a className="button" href={mailtoUrl}><Mail size={16} /> Email the maintainer</a>}
        </div>
        <p className="mono" style={{ marginTop: 14, fontSize: 12 }}>The issue template is public. Prefer email for anything you would rather not post, or leave sensitive fields blank and we will follow up privately.</p>
      </div>
    </section>
  );
}
