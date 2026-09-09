import { launchHeaders } from "./launch-key";
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
export async function listRollouts(filters?: {
  policyId?: string;
  environmentId?: string;
  taskProfileId?: string;
}) {
  const params = new URLSearchParams();
  if (filters?.policyId) params.set("policy_id", filters.policyId);
  if (filters?.environmentId) params.set("environment_id", filters.environmentId);
  if (filters?.taskProfileId) params.set("task_profile_id", filters.taskProfileId);
  const query = params.size ? `?${params}` : "";
  return (await request<{ items: Rollout[] }>(`/v0/rollouts${query}`)).items;
}
export const getRollout = (id: string) => request<Rollout>(`/v0/rollouts/${id}`);
export const getEvaluation = (id: string) => request<EvaluationJob>(`/v0/evaluations/${id}`);
export const cancelEvaluation = (id: string) =>
  request<EvaluationJob>(`/v0/evaluations/${id}/cancel`, { method: "POST", headers: launchHeaders() });
export const listEvaluationRollouts = async (id: string) =>
  (await request<{ items: Rollout[] }>(`/v0/evaluations/${id}/rollouts`)).items;

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
    headers: launchHeaders(),
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
