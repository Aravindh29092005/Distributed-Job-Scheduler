import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { jobsService, organizationsService, projectsService, queuesService } from '../services';
import { StatusBadge } from '../components/StatusBadge';
import { ActivityLog, createLogEntry, type LogEntry } from '../components/ActivityLog';

interface OrgItem { id: string; name: string; }
interface ProjItem { id: string; name: string; }
interface QueueItem { id: string; name: string; }
interface Job {
  id: string;
  name: string;
  job_type: string;
  status: string;
  priority: number;
  current_attempt: number;
  max_retries: number;
  run_at: string;
  created_at: string;
  queue_id: string;
  payload?: { description?: string; [key: string]: unknown };
}

const JOB_TYPES = ['immediate', 'delayed', 'scheduled', 'recurring', 'batch'] as const;
const MAX_LOG_ENTRIES = 100;

export function JobsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);

  const addLog = useCallback((level: LogEntry['level'], message: string) => {
    setLogs((prev) => [createLogEntry(level, message), ...prev].slice(0, MAX_LOG_ENTRIES));
  }, []);

  const [orgs, setOrgs] = useState<OrgItem[]>([]);
  const [projects, setProjects] = useState<ProjItem[]>([]);
  const [queues, setQueues] = useState<QueueItem[]>([]);
  const [orgId, setOrgId] = useState('');
  const [projectId, setProjectId] = useState('');
  const [queueId, setQueueId] = useState('');
  const [orgsLoading, setOrgsLoading] = useState(true);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [queuesLoading, setQueuesLoading] = useState(false);

  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const limit = 50;

  const [showCreate, setShowCreate] = useState(true);
  const [newName, setNewName] = useState('');
  const [newType, setNewType] = useState<string>('immediate');
  const [newDescription, setNewDescription] = useState('');
  const [newPriority, setNewPriority] = useState(5);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    organizationsService.list()
      .then((res) => {
        const list: OrgItem[] = res.data ?? [];
        setOrgs(list);
        if (list.length > 0) {
          setOrgId(list[0].id);
          addLog('info', `Loaded ${list.length} organization(s).`);
        } else {
          addLog('warn', 'No organizations found. Create one first.');
        }
      })
      .catch(() => {
        setError('Failed to load organizations.');
        addLog('error', 'Failed to load organizations.');
      })
      .finally(() => setOrgsLoading(false));
  }, [addLog]);

  useEffect(() => {
    if (!orgId) { setProjects([]); setProjectId(''); return; }
    setProjectsLoading(true);
    setProjects([]);
    setProjectId('');
    const orgName = orgs.find((o) => o.id === orgId)?.name ?? orgId;
    projectsService.list(orgId)
      .then((res) => {
        const list: ProjItem[] = res.data ?? [];
        setProjects(list);
        if (list.length > 0) {
          setProjectId(list[0].id);
          addLog('info', `Loaded ${list.length} project(s) for "${orgName}".`);
        } else {
          addLog('warn', `No projects in organization "${orgName}".`);
        }
      })
      .catch(() => {
        setError('Failed to load projects.');
        addLog('error', `Failed to load projects for "${orgName}".`);
      })
      .finally(() => setProjectsLoading(false));
  }, [orgId, orgs, addLog]);

  useEffect(() => {
    if (!projectId) { setQueues([]); setQueueId(''); return; }
    setQueuesLoading(true);
    setQueues([]);
    setQueueId('');
    const projectName = projects.find((p) => p.id === projectId)?.name ?? projectId;
    queuesService.list(projectId)
      .then((res) => {
        const raw = res.data;
        const list: QueueItem[] = Array.isArray(raw) ? raw : (raw?.items ?? []);
        setQueues(list);
        if (list.length > 0) {
          setQueueId(list[0].id);
          addLog('info', `Loaded ${list.length} queue(s) for project "${projectName}".`);
        } else {
          addLog('warn', `No queues in project "${projectName}". Create a queue first.`);
        }
      })
      .catch(() => {
        setError('Failed to load queues.');
        addLog('error', `Failed to load queues for "${projectName}".`);
      })
      .finally(() => setQueuesLoading(false));
  }, [projectId, projects, addLog]);

  const fetchJobs = useCallback(() => {
    if (!queueId && !projectId) { setJobs([]); setTotal(0); return; }
    setLoading(true);
    const params: Record<string, string | number | undefined> = {
      skip: (page - 1) * limit,
      limit,
    };
    if (queueId) params.queue_id = queueId;
    else if (projectId) params.project_id = projectId;
    if (statusFilter) params.status = statusFilter;

    jobsService.list(params)
      .then((res) => {
        const items = res.data.items ?? res.data ?? [];
        setJobs(items);
        setTotal(res.data.total ?? items.length);
        setError('');
      })
      .catch(() => {
        setError('Failed to load jobs.');
        addLog('error', 'Failed to refresh job list.');
      })
      .finally(() => setLoading(false));
  }, [queueId, projectId, statusFilter, page, addLog]);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  const handleCancel = async (jobId: string) => {
    if (!confirm('Cancel this job?')) return;
    try {
      await jobsService.cancel(jobId);
      addLog('success', `Cancelled job ${jobId.slice(0, 8)}…`);
      fetchJobs();
    } catch {
      addLog('error', `Failed to cancel job ${jobId.slice(0, 8)}…`);
      alert('Cannot cancel job in its current state.');
    }
  };

  const handleRetry = async (jobId: string) => {
    try {
      await jobsService.retry(jobId);
      addLog('success', `Retry requested for job ${jobId.slice(0, 8)}…`);
      fetchJobs();
    } catch {
      addLog('error', `Failed to retry job ${jobId.slice(0, 8)}…`);
      alert('Cannot retry job in its current state.');
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) {
      setError('Job name is required.');
      addLog('warn', 'Job creation blocked: name is required.');
      return;
    }
    if (!queueId || !projectId) {
      setError('Select a project and queue before posting a job.');
      addLog('warn', 'Job creation blocked: no queue selected.');
      return;
    }

    const queueName = queues.find((q) => q.id === queueId)?.name ?? queueId;
    setCreating(true);
    setError('');

    try {
      const payload: Record<string, unknown> = {};
      if (newDescription.trim()) {
        payload.description = newDescription.trim();
      }

      const response = await jobsService.create({
        queue_id: queueId,
        project_id: projectId,
        name: newName.trim(),
        job_type: newType,
        payload,
        priority: newPriority,
      });

      const created = response.data;
      addLog(
        'success',
        `Posted job "${newName.trim()}" (${newType}, priority ${newPriority}) to queue "${queueName}". ID: ${created.id?.slice(0, 8) ?? 'unknown'}…`,
      );

      setNewName('');
      setNewDescription('');
      setNewPriority(5);
      setNewType('immediate');
      fetchJobs();
    } catch (err) {
      let message = 'Failed to create job.';
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') message = detail;
        else if (Array.isArray(detail)) message = detail.map((d) => d.msg).join(', ');
        else if (!err.response) message = 'Backend unreachable. Is the API running on port 8000?';
      }
      setError(message);
      addLog('error', `Job post failed: ${message}`);
    } finally {
      setCreating(false);
    }
  };

  const fmt = (s: string) =>
    new Date(s).toLocaleString('en-US', { dateStyle: 'short', timeStyle: 'short' });

  const getDescription = (job: Job) => {
    const desc = job.payload?.description;
    return typeof desc === 'string' ? desc : '—';
  };

  const selectedQueue = queues.find((q) => q.id === queueId);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Jobs</h1>
          <p className="page-subtitle">
            {total} total jobs
            {selectedQueue ? ` · queue: ${selectedQueue.name}` : ''}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            className="btn btn-primary"
            onClick={() => setShowCreate((s) => !s)}
            type="button"
          >
            {showCreate ? 'Hide Form' : '+ Post Job'}
          </button>
          <span className="polling-badge">
            <span className="polling-dot" />
            Live · 5s
          </span>
        </div>
      </div>

      <div className="card mb-4" style={{ padding: '1.25rem', display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label className="form-label" style={{ display: 'block', marginBottom: '0.4rem' }}>Organization</label>
          {orgsLoading ? <div className="text-sm text-muted">Loading…</div> : (
            <select className="input" value={orgId} onChange={(e) => setOrgId(e.target.value)}>
              {orgs.length === 0
                ? <option value="">No organizations</option>
                : orgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
            </select>
          )}
        </div>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label className="form-label" style={{ display: 'block', marginBottom: '0.4rem' }}>Project</label>
          {projectsLoading ? <div className="text-sm text-muted">Loading…</div> : (
            <select className="input" value={projectId} onChange={(e) => setProjectId(e.target.value)} disabled={!orgId}>
              {projects.length === 0
                ? <option value="">No projects</option>
                : projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          )}
        </div>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label className="form-label" style={{ display: 'block', marginBottom: '0.4rem' }}>Queue</label>
          {queuesLoading ? <div className="text-sm text-muted">Loading…</div> : (
            <select
              className="input"
              value={queueId}
              onChange={(e) => {
                setQueueId(e.target.value);
                const q = queues.find((item) => item.id === e.target.value);
                if (q) addLog('info', `Selected queue "${q.name}".`);
              }}
              disabled={!projectId}
            >
              {queues.length === 0
                ? <option value="">No queues</option>
                : queues.map((q) => <option key={q.id} value={q.id}>{q.name}</option>)}
            </select>
          )}
        </div>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label className="form-label" style={{ display: 'block', marginBottom: '0.4rem' }}>Status</label>
          <select
            className="input"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          >
            <option value="">All statuses</option>
            {['queued', 'scheduled', 'claimed', 'running', 'completed', 'failed', 'retrying', 'dead_letter_queue', 'cancelled'].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>

      {showCreate && (
        <div className="card mb-4" style={{ padding: '1.25rem' }}>
          <h3 className="mb-4">Post Job to Queue</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem' }}>
            <div>
              <label className="form-label">Name *</label>
              <input
                className="input"
                placeholder="e.g. send-welcome-email"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                autoFocus
              />
            </div>
            <div>
              <label className="form-label">Job Type</label>
              <select className="input" value={newType} onChange={(e) => setNewType(e.target.value)}>
                {JOB_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="form-label">Priority (0–10)</label>
              <input
                className="input"
                type="number"
                min={0}
                max={10}
                value={newPriority}
                onChange={(e) => setNewPriority(Number(e.target.value))}
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="form-label">Description</label>
              <textarea
                className="input"
                rows={3}
                placeholder="What should this job do?"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                style={{ resize: 'vertical' }}
              />
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.75rem' }}>
            <button
              className="btn btn-primary"
              onClick={handleCreate}
              disabled={creating || !newName.trim() || !queueId}
              type="button"
            >
              {creating ? <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> : 'Post Job'}
            </button>
            <button className="btn btn-secondary" onClick={() => setShowCreate(false)} type="button">
              Cancel
            </button>
          </div>
          {!queueId && (
            <p className="text-sm text-muted" style={{ marginTop: '0.75rem' }}>
              Select a queue above before posting a job.
            </p>
          )}
        </div>
      )}

      {error && <div className="alert alert-error mb-4">{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(280px, 1fr)', gap: '1rem', alignItems: 'start' }}>
        <div>
          {loading ? (
            <div className="loading-overlay"><div className="spinner" /></div>
          ) : jobs.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">⚙️</div>
              <div className="empty-state-text">
                {queueId ? 'No jobs found for this queue. Post one using the form above.' : 'Select a queue above to see jobs.'}
              </div>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Description</th>
                    <th>Status</th>
                    <th>Priority</th>
                    <th>Attempts</th>
                    <th>Run At</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job) => (
                    <tr key={job.id}>
                      <td>
                        <Link to={`/jobs/${job.id}`} style={{ color: 'var(--c-text-primary)', fontWeight: 500 }}>
                          {job.name}
                        </Link>
                        <div className="text-xs text-muted font-mono truncate" style={{ maxWidth: 200 }}>{job.id}</div>
                      </td>
                      <td><span className="badge badge-queued" style={{ fontSize: '0.7rem' }}>{job.job_type}</span></td>
                      <td className="text-sm text-muted" style={{ maxWidth: 180 }}>{getDescription(job)}</td>
                      <td><StatusBadge status={job.status} /></td>
                      <td><span className="font-mono text-sm">{job.priority}</span></td>
                      <td><span className="font-mono text-sm">{job.current_attempt}/{job.max_retries}</span></td>
                      <td className="text-sm font-mono">{fmt(job.run_at)}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.375rem' }}>
                          {['queued', 'scheduled'].includes(job.status) && (
                            <button className="btn btn-danger btn-sm" onClick={() => handleCancel(job.id)} type="button">Cancel</button>
                          )}
                          {['failed', 'dead_letter_queue'].includes(job.status) && (
                            <button className="btn btn-secondary btn-sm" onClick={() => handleRetry(job.id)} type="button">Retry</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {total > limit && (
            <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', marginTop: '1.25rem' }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} type="button">
                ← Prev
              </button>
              <span className="text-sm text-muted" style={{ alignSelf: 'center' }}>
                Page {page} of {Math.ceil(total / limit)}
              </span>
              <button className="btn btn-secondary btn-sm" onClick={() => setPage((p) => p + 1)} disabled={page * limit >= total} type="button">
                Next →
              </button>
            </div>
          )}
        </div>

        <ActivityLog
          entries={logs}
          title="Project Activity Log"
          onClear={() => {
            setLogs([]);
            addLog('info', 'Activity log cleared.');
          }}
        />
      </div>
    </div>
  );
}
