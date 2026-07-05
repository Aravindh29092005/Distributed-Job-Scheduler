import { useEffect, useState } from 'react';
import { workersService } from '../services';
import { StatusBadge } from '../components/StatusBadge';

interface Worker {
  id: string;
  hostname: string;
  status: string;
  concurrency_limit: number;
  created_at: string;
  updated_at: string;
}

export function WorkersPage() {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchWorkers = async () => {
    try {
      const res = await workersService.list();
      setWorkers(res.data ?? []);
      setError('');
    } catch {
      setError('Failed to load workers.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkers();
    const interval = setInterval(fetchWorkers, 5000);
    return () => clearInterval(interval);
  }, []);

  const activeCount = workers.filter(w => w.status === 'active').length;
  const offlineCount = workers.filter(w => w.status === 'offline').length;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Workers</h1>
          <p className="page-subtitle">
            {activeCount} active · {offlineCount} offline · {workers.length} total
          </p>
        </div>
        <span className="polling-badge">
          <span className="polling-dot" />
          Live · 5s
        </span>
      </div>

      {/* Stats */}
      <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <div className="stat-card">
          <div className="stat-icon indigo">🖥️</div>
          <div>
            <div className="stat-label">Total Workers</div>
            <div className="stat-value">{workers.length}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon emerald">✅</div>
          <div>
            <div className="stat-label">Active</div>
            <div className="stat-value">{activeCount}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red">❌</div>
          <div>
            <div className="stat-label">Offline</div>
            <div className="stat-value">{offlineCount}</div>
          </div>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading-overlay"><div className="spinner" /></div>
      ) : workers.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🖥️</div>
          <div className="empty-state-text">No workers registered yet.</div>
          <p className="text-sm text-muted">Start a worker with: <code>python -m backend.worker.main</code></p>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Hostname</th>
                <th>Status</th>
                <th>Concurrency</th>
                <th>Last Heartbeat</th>
                <th>Registered</th>
                <th>Worker ID</th>
              </tr>
            </thead>
            <tbody>
              {workers.map(worker => (
                <tr key={worker.id}>
                  <td style={{ fontWeight: 500 }}>{worker.hostname}</td>
                  <td><StatusBadge status={worker.status} /></td>
                  <td className="font-mono text-sm">{worker.concurrency_limit}</td>
                  <td className="text-sm text-muted">
                    {new Date(worker.updated_at).toLocaleTimeString()}
                  </td>
                  <td className="text-sm text-muted">
                    {new Date(worker.created_at).toLocaleDateString()}
                  </td>
                  <td className="text-xs font-mono text-muted truncate" style={{ maxWidth: 200 }}>
                    {worker.id}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Architecture note */}
      <div className="card-glass" style={{ marginTop: '1.25rem' }}>
        <h3 style={{ fontSize: '0.9375rem', marginBottom: '0.5rem' }}>🔄 Heartbeat & Reaper</h3>
        <p className="text-sm text-secondary">
          Each worker process writes a <strong>WorkerHeartbeat</strong> row every{' '}
          <code>WORKER_HEARTBEAT_INTERVAL_SECONDS</code> (default 5s). The heartbeat loop runs as
          an independent asyncio task — separate from job execution — so a stuck job cannot block
          heartbeats and trigger false dead-worker detection. The reaper queries for workers whose
          last heartbeat exceeds <code>WORKER_REAPER_STALE_THRESHOLD_SECONDS</code> (default 30s)
          and atomically requeues their in-flight jobs.
        </p>
      </div>
    </div>
  );
}
