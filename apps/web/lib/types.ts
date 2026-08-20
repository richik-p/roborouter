export type Evidence = {
  level: string;
  source: string;
  checked_at: string;
  description: string;
  exact_robot_match: boolean;
  exact_runtime_match: boolean;
};

export type Policy = {
  id: string;
  revision: string;
  name: string;
  family: string;
  description: string;
  robot_classes: string[];
  task_families: string[];
  runtime: null | { adapter: string; framework: string; framework_revision: string };
  source: { repository: string; checkpoint: string | null; checkpoint_revision: string | null };
  availability: { weights: string; code: string; license: string };
  observations: { sensor_types: string[]; cameras: string[]; language_prompt: boolean };
  actions: null | { schema: string; dimensions?: number; horizon?: number; expected_rate_hz?: number };
  evidence: Evidence[];
  tags: string[];
};

export type Robot = { id: string; revision: string; name: string; robot_class: string };
export type Task = { id: string; revision: string; name: string; task_family: string; domain: string };

export type Compatibility = {
  id: string;
  policy_id: string;
  status: string;
  reason_codes: string[];
  explanation: string;
  missing_requirements: string[];
  score: number;
  best_evidence: Evidence | null;
  supported_paths: { simulate: boolean; shadow: boolean; actuate: boolean };
};

export type Artifact = { id: string; kind: string; uri: string; media_type: string };
export type Rollout = {
  id: string;
  evaluation_job_id: string | null;
  mode: string;
  policy_spec_id: string;
  policy_revision: string;
  robot_profile_id: string;
  task_profile_id: string;
  environment_id: string;
  environment_revision: string;
  seed: number;
  started_at: string;
  duration_ms: number;
  success: boolean;
  metrics: Record<string, string | number | boolean>;
  runtime_identity: Record<string, string>;
  artifacts: Artifact[];
  evidence_note: string | null;
};

export type EvaluationJob = {
  id: string;
  state: string;
  request: {
    policy_id: string;
    policy_revision: string;
    environment_id: string;
    environment_revision: string;
    task_profile_id: string;
    task_revision: string;
    seeds: number[];
  };
  created_at: string;
  updated_at: string;
  failure_kind: string | null;
  failure_detail: string | null;
};

