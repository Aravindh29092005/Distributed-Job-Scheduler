import { useEffect, useState } from 'react';
import { metricsService } from '../services';

interface Metrics {
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

function ProgressBar({ label, value, total, color }: {
  label: string;
  value: number;
  total: number;
  color: string;
}) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div style={{ marginBottom: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.375rem' }}>
        <span className="text-sm text-secondary">{label}</span>
        <span className="text-sm font-mono" style={{ color }}>
          {value.toLocaleString()} ({pct}%)
        </span>
      </div>
      <div style={{
        height: 8,
        background: 'var(--c-surface-3)',
        borderRadius: 4,
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${pct}%`,
          background: color,
          borderRadius: 4,
          transition: 'width 0.5s ease',
        }} />
      </div>
    </div>
  );
}

function MetricRow({ label, value, unit = '' }: { label: string; value: string | number; unit?: string }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '0.625rem 0',
      borderBottom: '1px solid var(--c-border)',
    }}>
      <span className="text-sm text-secondary">{label}</span>
      <span className="text-sm font-mono" style={{ color: 'var(--c-text-primary)' }}>
        {value}{unit && <span className="text-muted"> {unit}</span>}
      </span>
    </div>
  );
}

export function MetricsPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [history, setHistory] = useState<{ ts: string; total: number; active: number }[]>([]);

  const fetchMetrics = async () => {
    try {
      const res = await metricsService.get();
      const m: Metrics = res.data;
      setMetrics(m);
      setHistory(prev => [
        ...prev.slice(-29),
        { ts: new Date().toLocaleTimeString(), total: m.total_jobs, active: m.active_jobs },
      ]);
      setError('');
    } catch {
      setError('Failed to load metrics. Backend may be unavailable.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="loading-overlay"><div className="spinner" /></div>;

  const successRate = metrics && metrics.total_jobs > 0
    ? ((metrics.completed_jobs / metrics.total_jobs) * 100).toFixed(1)
    : '—';

  const maxHistory = Math.max(...history.map(h => h.total), 1);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Metrics</h1>
          <p className="page-subtitle">Real-time platform health indicators</p>
        </div>
        <span className="polling-badge">
          <span className="polling-dot" />
          Live · 5s
        </span>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Stat grid */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-icon indigo">⚙️</div>
          <div><div className="stat-label">Total Jobs</div><div className="stat-value">{metrics?.total_jobs ?? 0}</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon cyan">▶️</div>
          <div><div className="stat-label">Active</div><div className="stat-value">{metrics?.active_jobs ?? 0}</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon emerald">✅</div>
          <div><div className="stat-label">Completed</div><div className="stat-value">{metrics?.completed_jobs ?? 0}</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red">❌</div>
          <div><div className="stat-label">Failed</div><div className="stat-value">{metrics?.failed_jobs ?? 0}</div></div>
        </div>
      </div>

      <div className="grid-2">
        {/* Job breakdown */}
        <div className="card">
          <h3 className="mb-4">Job Status Breakdown</h3>
          {metrics && (
            <>
              <ProgressBar label="Completed" value={metrics.completed_jobs} total={metrics.total_jobs} color="#10b981" />
              <ProgressBar label="Queued"    value={metrics.queued_jobs}    total={metrics.total_jobs} color="#f59e0b" />
              <ProgressBar label="Active"    value={metrics.active_jobs}    total={metrics.total_jobs} color="#6366f1" />
              <ProgressBar label="Failed"    value={metrics.failed_jobs}    total={metrics.total_jobs} color="#ef4444" />
            </>
          )}
        </div>

        {/* KPI table */}
        <div className="card">
          <h3 className="mb-4">Key Performance Indicators</h3>
          <MetricRow label="Success Rate"      value={successRate} unit="%" />
          <MetricRow label="Active Workers"    value={`${metrics?.active_workers ?? 0} / ${metrics?.total_workers ?? 0}`} />
          <MetricRow label="Total Queues"      value={metrics?.total_queues ?? 0} />
          <MetricRow label="DLQ Unresolved"    value={metrics?.dlq_unresolved ?? 0} />
          <MetricRow label="Pending Items"     value={metrics?.pending_items ?? 0} />
          <MetricRow label="Worker Health"     value={(metrics?.active_workers ?? 0) > 0 ? '✅ Online' : '⚠️ No workers'} />
        </div>
      </div>

      {/* Mini spark chart */}
      {history.length > 1 && (
        <div className="card" style={{ marginTop: '1.25rem' }}>
          <h3 className="mb-4">Total Job Count — Last 30 Polls (5s each)</h3>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 80 }}>
            {history.map((h, i) => (
              <div key={i} title={`${h.ts}: ${h.total} total, ${h.active} active`} style={{
                flex: 1,
                minWidth: 8,
                height: `${Math.max(4, (h.total / maxHistory) * 100)}%`,
                background: 'linear-gradient(180deg, #6366f1 0%, #8b5cf6 100%)',
                borderRadius: '2px 2px 0 0',
                opacity: 0.7 + (i / history.length) * 0.3,
                transition: 'height 0.3s ease',
              }} />
            ))}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem' }}>
            <span className="text-xs text-muted">{history[0]?.ts}</span>
            <span className="text-xs text-muted">{history[history.length - 1]?.ts}</span>
          </div>
        </div>
      )}
    </div>
  );
}
