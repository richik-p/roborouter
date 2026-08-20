"use client";

import Link from "next/link";
import { ArrowRight, Search, SlidersHorizontal } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { listPolicies, listRobots, listTasks, queryCompatibility } from "@/lib/api";
import type { Compatibility, Policy, Robot, Task } from "@/lib/types";

function statusClass(status?: string) {
  if (status === "SIM_VERIFIED") return "tag green";
  if (status === "INCOMPATIBLE") return "tag orange";
  return "tag blue";
}

function statusLabel(policy: Policy, result?: Compatibility) {
  if (result) return result.status.replaceAll("_", " ");
  return policy.runtime ? "Executable path" : "Research only";
}

export default function Explorer() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [robots, setRobots] = useState<Robot[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [robotId, setRobotId] = useState("sim-libero-panda");
  const [taskId, setTaskId] = useState("libero-object-pick-place");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Record<string, Compatibility>>({});
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listPolicies(), listRobots(), listTasks()])
      .then(([policyData, robotData, taskData]) => {
        setPolicies(policyData);
        setRobots(robotData);
        setTasks(taskData);
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false));
  }, []);

  const visible = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return policies.filter((policy) =>
      !normalized || `${policy.name} ${policy.family} ${policy.description} ${policy.tags.join(" ")}`.toLowerCase().includes(normalized)
    );
  }, [policies, query]);

  async function runCompatibility() {
    const robot = robots.find((item) => item.id === robotId);
    const task = tasks.find((item) => item.id === taskId);
    if (!robot || !task) return;
    setChecking(true);
    setError(null);
    try {
      const records = await queryCompatibility(robot, task);
      setResults(Object.fromEntries(records.map((item) => [item.policy_id, item])));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Compatibility check failed");
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="explore-panel">
      <div className="query-bar">
        <div className="field">
          <label htmlFor="search"><Search size={11} /> Policy or capability</label>
          <input id="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="language pick-and-place" />
        </div>
        <div className="field">
          <label htmlFor="robot">Robot profile</label>
          <select id="robot" value={robotId} onChange={(event) => setRobotId(event.target.value)}>
            {robots.map((robot) => <option key={robot.id} value={robot.id}>{robot.name}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="task">Task</label>
          <select id="task" value={taskId} onChange={(event) => setTaskId(event.target.value)}>
            {tasks.map((task) => <option key={task.id} value={task.id}>{task.name}</option>)}
          </select>
        </div>
        <button className="run-query" onClick={runCompatibility} disabled={checking || loading}>
          {checking ? "Checking…" : "Check compatibility"}
        </button>
      </div>
      {error && <div className="error">API unavailable: {error}. Start the local control plane, then retry.</div>}
      <div className="catalog-meta">
        <span><SlidersHorizontal size={12} /> {visible.length} POLICIES</span>
        <span>{Object.keys(results).length ? "RULESET compat-v0.1.0" : "RUN A CHECK FOR EVIDENCE"}</span>
      </div>
      <div className="policy-list">
        {loading && <div className="loading">Loading the reviewed catalog…</div>}
        {!loading && visible.length === 0 && <div className="empty">No catalog entries match this search.</div>}
        {visible.map((policy) => {
          const result = results[policy.id];
          return (
            <Link href={`/policies/${policy.id}`} className="policy-row" key={`${policy.id}:${policy.revision}`}>
              <div>
                <div className="policy-name">{policy.name}</div>
                <div className="policy-family">{policy.description}</div>
              </div>
              <span className="tag">{policy.robot_classes[0]?.replaceAll(".", " / ")}</span>
              <span className="mono">{policy.task_families[0]?.replaceAll("_", " ")}</span>
              <div className="status-line">
                <span className={statusClass(result?.status)}>{statusLabel(policy, result)}</span>
                {result && <span className="reason">{result.explanation}</span>}
              </div>
              <span className="arrow-box"><ArrowRight size={16} /></span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

