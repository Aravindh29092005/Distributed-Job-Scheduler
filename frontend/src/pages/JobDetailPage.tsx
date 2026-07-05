import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { jobsService } from '../services';
import { StatusBadge } from '../components/StatusBadge';

interface Execution {
  id: string;
  attempt: number;
  status: string;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  created_at: string;
}

interface Job {
  id: string;
  name: string;
  job_type: string;
  status: string;
  priority: number;
  timeout_seconds: number;
  current_attempt: number;
  max_retries: number;
  run_at: string;
  created_at: string;
  updated_at: string;
  queue_id: string;
  project_id: string;
  payload: Record<string, unknown>;
  idempotency_key?: string;
  retry_policy_id?: string;
  executions: Execution[];
}

const STATUS_COLORS: Record<string, string> = {
  running:   '#6366f1',
  completed: '#10b981',
  failed:    '#ef4444',
  queued:    '#64748b',
  claimed:   '#06b6d4',
};

function TimelineDot({ status }: { status: string }) {
  const color = STATUS_COLORS[status] ?? '#64748b';
  return (
    <div
      className="timeline-dot"
      style={{ background: color, color: '#fff' }}
    >
      {status === 'completed' ? '✓' : status === 'failed' ? '✗' : '#'}
    </div>
  );
}

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionMsg, setActionMsg] = useState('');

  const fetchJob = async () => {
    if (!jobId) return;
    try {
      const res = await jobsService.get(jobId);
      setJob(res.data);
      setError('');
    } catch {
      setError('Job not found or backend unreachable.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJob();
    const interval = setInterval(fetchJob, 3000);
    return () => clearInterval(interval);
  }, [jobId]);

  const handleCancel = async () => {
    try {
      await jobsService.cancel(jobId!);
      setActionMsg('Job cancelled.');
      fetchJob();
    } catch { setActionMsg('Cannot cancel job in current state.'); }
  };

  const handleRetry = async () => {
    try {
      await jobsService.retry(jobId!);
      setActionMsg('Job queued for retry.');
      fetchJob();
    } catch { setActionMsg('Cannot retry job in current state.'); }
  };

  if (loading) return <div className="loading-overlay"><div className="spinner" /></div>;
  if (error) return <div className="alert alert-error">{error}</div>;
  if (!job) return null;

  const fmt = (s: string | null) =>
    s ? new Date(s).toLocaleString('en-US', { dateStyle: 'short', timeStyle: 'medium' }) : '—';

  return (
    <div>
      {/* Breadcrumb */}
      <p className="text-sm text-muted mb-4">
        <Link to="/jobs" style={{ color: 'var(--c-info)' }}>← Jobs</Link>
        {' / '}
        <span>{job.name}</span>
      </p>

      {actionMsg && (
        <div className="alert alert-info mb-4">{actionMsg}</div>
      )}

      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {job.name}
            <StatusBadge status={job.status} />
          </h1>
          <p className="page-subtitle font-mono text-xs">{job.id}</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {['queued', 'scheduled'].includes(job.status) && (
            <button className="btn btn-danger" onClick={handleCancel}>Cancel Job</button>
          )}
          {['failed', 'dead_letter_queue'].includes(job.status) && (
            <button className="btn btn-primary" onClick={handleRetry}>↩ Retry</button>
          )}
          <span className="polling-badge">
            <span className="polling-dot" />
            Live · 3s
          </span>
        </div>
      </div>

      <div className="grid-2">
        {/* Metadata */}
        <div className="card">
          <h3 className="mb-4">Job Details</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.875rem' }}>
            {[
              { label: 'Type',        value: job.job_type },
              { label: 'Priority',    value: job.priority },
              { label: 'Attempts',    value: `${job.current_attempt} / ${job.max_retries}` },
              { label: 'Timeout',     value: `${job.timeout_seconds}s` },
              { label: 'Run At',      value: fmt(job.run_at) },
              { label: 'Created',     value: fmt(job.created_at) },
              { label: 'Updated',     value: fmt(job.updated_at) },
              { label: 'Queue ID',    value: job.queue_id },
            ].map(({ label, value }) => (
              <div key={label}>
                <div className="text-xs text-muted" style={{ marginBottom: 2 }}>{label}</div>
                <div className="text-sm font-mono" style={{ wordBreak: 'break-all' }}>{String(value)}</div>
              </div>
            ))}
          </div>
          {job.idempotency_key && (
            <div className="mt-4">
              <div className="text-xs text-muted mb-1">Idempotency Key</div>
              <code className="text-xs font-mono">{job.idempotency_key}</code>
            </div>
          )}
        </div>

        {/* Payload */}
        <div className="card">
          <h3 className="mb-4">Payload</h3>
          <pre className="code-block" style={{ maxHeight: 220, overflow: 'auto' }}>
            {JSON.stringify(job.payload, null, 2)}
          </pre>
        </div>
      </div>

      {/* Execution Timeline */}
      <div className="card" style={{ marginTop: '1.25rem' }}>
        <h3 className="mb-4">Execution History</h3>
        {job.executions.length === 0 ? (
          <div className="text-sm text-muted">No execution attempts yet.</div>
        ) : (
          <div className="timeline">
            {[...job.executions].reverse().map((exec) => (
              <div key={exec.id} className="timeline-item">
                <TimelineDot status={exec.status} />
                <div className="timeline-content">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="timeline-label">Attempt #{exec.attempt}</span>
                    <StatusBadge status={exec.status} />
                    {exec.duration_seconds != null && (
                      <span className="text-xs text-muted font-mono">
                        {exec.duration_seconds.toFixed(2)}s
                      </span>
                    )}
                  </div>
                  <div className="timeline-ts">
                    {exec.started_at ? `Started: ${fmt(exec.started_at)}` : ''}
                    {exec.finished_at ? ` · Finished: ${fmt(exec.finished_at)}` : ''}
                  </div>
                  {exec.error_message && (
                    <pre className="code-block" style={{ marginTop: '0.5rem', fontSize: '0.75rem', maxHeight: 100, overflow: 'auto' }}>
                      {exec.error_message}
                    </pre>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
