import apiClient from './api';

/**
 * All service calls go through the typed axios client.
 * Note: baseURL is already configured as '/api' in api.ts,
 * so we do not include the '/api' prefix in any URL here.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Auth
// ─────────────────────────────────────────────────────────────────────────────
export const authService = {
  login: (email: string, password: string) =>
    apiClient.post('/auth/login', { email, password }),
  register: (email: string, password: string, fullName?: string) =>
    apiClient.post('/auth/register', { email, password, full_name: fullName }),
  me: () => apiClient.get('/auth/me'),
  refresh: (refreshToken: string) =>
    apiClient.post('/auth/refresh', { refresh_token: refreshToken }),
};

// ─────────────────────────────────────────────────────────────────────────────
// Organizations
// ─────────────────────────────────────────────────────────────────────────────
export const organizationsService = {
  list: () => apiClient.get('/organizations'),
  get: (id: string) => apiClient.get(`/organizations/${id}`),
  create: (data: { name: string }) => apiClient.post('/organizations', data),
  addMember: (orgId: string, data: { user_id: string; role: string }) =>
    apiClient.post(`/organizations/${orgId}/members`, data),
  archive: (id: string) => apiClient.delete(`/organizations/${id}`),
};

// ─────────────────────────────────────────────────────────────────────────────
// Projects
// ─────────────────────────────────────────────────────────────────────────────
export const projectsService = {
  list: (orgId: string) => apiClient.get('/projects', { params: { org_id: orgId } }),
  get: (id: string) => apiClient.get(`/projects/${id}`),
  create: (data: { organization_id: string; name: string; description?: string }) =>
    apiClient.post('/projects', data),
};

// ─────────────────────────────────────────────────────────────────────────────
// Queues
// ─────────────────────────────────────────────────────────────────────────────
export const queuesService = {
  list: (projectId: string) =>
    apiClient.get('/queues', { params: { project_id: projectId } }),
  get: (id: string) => apiClient.get(`/queues/${id}`),
  stats: (id: string) => apiClient.get(`/queues/${id}/stats`),
  create: (data: any) => apiClient.post('/queues', data),
  pausedStatus: (id: string) => apiClient.get(`/queues/${id}/stats`), // placeholder/helper
  pause: (id: string, orgId: string) =>
    apiClient.post(`/queues/${id}/pause`, null, { params: { org_id: orgId } }),
  resume: (id: string, orgId: string) =>
    apiClient.post(`/queues/${id}/resume`, null, { params: { org_id: orgId } }),
  archive: (id: string, orgId: string) =>
    apiClient.delete(`/queues/${id}`, { params: { org_id: orgId } }),
};

// ─────────────────────────────────────────────────────────────────────────────
// Retry Policies
// ─────────────────────────────────────────────────────────────────────────────
export const retryPoliciesService = {
  list: (projectId: string) =>
    apiClient.get('/retry-policies', { params: { project_id: projectId } }),
  get: (id: string) => apiClient.get(`/retry-policies/${id}`),
  create: (data: any) => apiClient.post('/retry-policies', data),
};

// ─────────────────────────────────────────────────────────────────────────────
// Jobs
// ─────────────────────────────────────────────────────────────────────────────
export const jobsService = {
  list: (params?: Record<string, string | number | undefined>) =>
    apiClient.get('/jobs', { params }),
  get: (id: string) => apiClient.get(`/jobs/${id}`),
  create: (data: any) => apiClient.post('/jobs', data),
  cancel: (id: string) => apiClient.post(`/jobs/${id}/cancel`),
  retry: (id: string) => apiClient.post(`/jobs/${id}/retry`),
};

// ─────────────────────────────────────────────────────────────────────────────
// Workers
// ─────────────────────────────────────────────────────────────────────────────
export const workersService = {
  list: () => apiClient.get('/workers'),
  get: (id: string) => apiClient.get(`/workers/${id}`),
};

// ─────────────────────────────────────────────────────────────────────────────
// Dead Letter Queue
// ─────────────────────────────────────────────────────────────────────────────
export const dlqService = {
  list: (params?: Record<string, string | boolean | undefined>) =>
    apiClient.get('/dlq', { params }),
  resubmit: (id: string) => apiClient.post(`/dlq/${id}/resubmit`),
};

// ─────────────────────────────────────────────────────────────────────────────
// Metrics
// ─────────────────────────────────────────────────────────────────────────────
export const metricsService = {
  get: () => apiClient.get('/metrics'),
};
