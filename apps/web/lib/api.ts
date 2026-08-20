import type { Compatibility, EvaluationJob, Policy, Robot, Rollout, Task } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function listPolicies(query = ""): Promise<Policy[]> {
  const data = await request<{ items: Policy[] }>(`/v0/policies${query}`);
  return data.items;
}

export const getPolicy = (id: string) => request<Policy>(`/v0/policies/${id}`);
export const listRobots = async () => (await request<{ items: Robot[] }>("/v0/robots")).items;
export const listTasks = async () => (await request<{ items: Task[] }>("/v0/tasks")).items;
export const listRollouts = async () => (await request<{ items: Rollout[] }>("/v0/rollouts")).items;
export const getRollout = (id: string) => request<Rollout>(`/v0/rollouts/${id}`);
export const getEvaluation = (id: string) => request<EvaluationJob>(`/v0/evaluations/${id}`);

export function queryCompatibility(robot: Robot, task: Task, policyIds?: string[]) {
  return request<Compatibility[]>("/v0/compatibility/queries", {
    method: "POST",
    body: JSON.stringify({
      robot_profile_id: robot.id,
      robot_revision: robot.revision,
      task_profile_id: task.id,
      task_revision: task.revision,
      policy_ids: policyIds,
    }),
  });
}

export function createEvaluation(
  policy: Policy,
  options: {
    environmentId: string;
    environmentRevision: string;
    taskId: string;
    taskRevision: string;
    seeds: number[];
  } = {
    environmentId: "vla-eval-libero-object",
    environmentRevision: "vla-eval-0.4.0-lerobot-0.6.0-libero-2a4566009395",
    taskId: "libero-object-pick-place",
    taskRevision: "2026-08-20.1",
    seeds: [7],
  },
) {
  return request<EvaluationJob>("/v0/evaluations", {
    method: "POST",
    body: JSON.stringify({
      policy_id: policy.id,
      policy_revision: policy.revision,
      environment_id: options.environmentId,
      environment_revision: options.environmentRevision,
      task_profile_id: options.taskId,
      task_revision: options.taskRevision,
      seeds: options.seeds,
    }),
  });
}
