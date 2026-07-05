import { useEffect, useState } from 'react';
import { dlqService } from '../services';

interface DLQEntry {
  id: string;
  job_id: string;
  queue_id: string;
  project_id: string;
  payload: Record<string, unknown>;
  reason: string;
  failed_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  created_at: string;
}

export function DeadLetterQueuePage() {
  const [entries, setEntries] = useState<DLQEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [resolvedFilter, setResolvedFilter] = useState<'all' | 'unresolved' | 'resolved'>('unresolved');
  const [resubmitting, setResubmitting] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState('');

  const fetchEntries = async () => {
    try {
      const params: Record<string, string | boolean | undefined> = {};
      if (resolvedFilter === 'unresolved') params.resolved = false;
      if (resolvedFilter === 'resolved') params.resolved = true;
      const res = await dlqService.list(params);
      setEntries(res.data.items ?? res.data ?? []);
      setTotal(res.data.total ?? 0);
      setError('');
    } catch {
      setError('Failed to load DLQ entries.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries();
    const interval = setInterval(fetchEntries, 10000);
    return () => clearInterval(interval);
  }, [resolvedFilter]);

  const handleResubmit = async (entry: DLQEntry) => {
    if (!confirm(`Resubmit job ${entry.job_id.slice(0, 8)}... back to its queue?`)) return;
    setResubmitting(entry.id);
    try {
      await dlqService.resubmit(entry.id);
      setSuccessMsg(`Job resubmitted successfully — it will be picked up by the next available worker.`);
      fetchEntries();
    } catch {
      setError('Failed to resubmit. Job may already be resolved.');
    } finally {
      setResubmitting(null);
    }
  };

  const fmt = (s: string) => new Date(s).toLocaleString();
  const unresolvedCount = entries.filter(e => !e.resolved_at).length;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dead Letter Queue</h1>
          <p className="page-subtitle">
            {total} total entries · {unresolvedCount} pending resolution
          </p>
        </div>
        <span className="polling-badge">
          <span className="polling-dot" />
          Live · 10s
        </span>
      </div>

      {successMsg && <div className="alert alert-success">{successMsg}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {/* Filters */}
      <div style={{ display: 'flex', gap: '0.375rem', marginBottom: '1.25rem' }}>
        {(['all', 'unresolved', 'resolved'] as const).map(f => (
          <button
            key={f}
            className={`btn ${resolvedFilter === f ? 'btn-primary' : 'btn-secondary'} btn-sm`}
            onClick={() => setResolvedFilter(f)}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading-overlay"><div className="spinner" /></div>
      ) : entries.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🎉</div>
          <div className="empty-state-text">
            {resolvedFilter === 'unresolved' ? 'No pending DLQ entries — all jobs healthy!' : 'No entries in this filter.'}
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
          {entries.map(entry => (
            <div key={entry.id} className="card" style={{
              borderColor: entry.resolved_at ? 'var(--c-border)' : 'rgba(239,68,68,0.3)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.375rem' }}>
                    <span
                      className={`badge ${entry.resolved_at ? 'badge-completed' : 'badge-dead_letter_queue'}`}
                    >
                      {entry.resolved_at ? 'Resolved' : 'Pending'}
                    </span>
                    <span className="text-xs font-mono text-muted">{entry.id}</span>
                  </div>
                  <p className="text-sm" style={{ marginBottom: '0.25rem' }}>
                    <strong>Job:</strong>{' '}
                    <a href={`/jobs/${entry.job_id}`} style={{ color: 'var(--c-info)', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                      {entry.job_id}
                    </a>
                  </p>
                  <p className="text-sm text-secondary" style={{ marginBottom: '0.5rem' }}>
                    <strong>Reason:</strong> {entry.reason}
                  </p>
                  <div style={{ display: 'flex', gap: '1rem' }}>
                    <span className="text-xs text-muted">Failed: {fmt(entry.failed_at)}</span>
                    {entry.resolved_at && (
                      <span className="text-xs" style={{ color: 'var(--c-success)' }}>
                        Resolved: {fmt(entry.resolved_at)}
                      </span>
                    )}
                  </div>
                </div>
                <div>
                  {!entry.resolved_at && (
                    <button
                      className="btn btn-primary btn-sm"
                      disabled={resubmitting === entry.id}
                      onClick={() => handleResubmit(entry)}
                    >
                      {resubmitting === entry.id
                        ? <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                        : '↩ Resubmit'}
                    </button>
                  )}
                </div>
              </div>
              {Object.keys(entry.payload).length > 0 && (
                <details style={{ marginTop: '0.75rem' }}>
                  <summary className="text-xs text-muted" style={{ cursor: 'pointer' }}>
                    View Payload
                  </summary>
                  <pre className="code-block" style={{ marginTop: '0.5rem', fontSize: '0.75rem', maxHeight: 120, overflow: 'auto' }}>
                    {JSON.stringify(entry.payload, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
