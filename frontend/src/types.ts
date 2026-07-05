/** Shared TypeScript types for the Codity frontend. */

export interface Metrics {
  total_jobs: number;
  active_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  queued_jobs: number;
  total_workers: number;
  active_workers: number;
  total_queues: number;
  pending_items: number;
  dlq_unresolved: number;
}

export interface User {
  id: string;
  email: string;
  full_name?: string;
  role?: string;
}

export interface Organization {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface Queue {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  priority: number;
  max_concurrent: number;
  paused: boolean;
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: string;
  queue_id: string;
  project_id: string;
  name: string;
  job_type: string;
  status: string;
  payload: Record<string, unknown>;
  priority: number;
  timeout_seconds: number;
  current_attempt: number;
  max_retries: number;
  run_at: string;
  created_at: string;
  updated_at: string;
  idempotency_key?: string;
  batch_id?: string;
  retry_policy_id?: string;
}

export interface JobExecution {
  id: string;
  attempt: number;
  status: string;
  error_message?: string;
  started_at?: string;
  finished_at?: string;
  duration_seconds?: number;
  created_at: string;
}

export interface Worker {
  id: string;
  hostname: string;
  status: string;
  concurrency_limit: number;
  created_at: string;
  updated_at: string;
}

export interface DLQEntry {
  id: string;
  job_id: string;
  queue_id: string;
  project_id: string;
  payload: Record<string, unknown>;
  reason: string;
  failed_at: string;
  resolved_at?: string;
  resolved_by?: string;
  created_at: string;
  updated_at: string;
}
