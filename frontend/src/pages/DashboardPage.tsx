import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { metricsService } from '../services';
import type { Metrics } from '../types';

interface StatCardProps {
  label: string;
  value: number;
  iconClass: string;
  icon: string;
}

function StatCard({ label, value, iconClass, icon }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${iconClass}`}>{icon}</div>
      <div>
        <div className="stat-label">{label}</div>
        <div className="stat-value">{value.toLocaleString()}</div>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchMetrics = async () => {
    try {
      const res = await metricsService.get();
      setMetrics(res.data);
      setLastUpdated(new Date());
      setError('');
    } catch {
      setError('Failed to load metrics. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="spinner" />
        <span>Loading metrics…</span>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Real-time platform overview</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {lastUpdated && (
            <span className="text-xs text-muted font-mono">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <span className="polling-badge">
            <span className="polling-dot" />
            Live · 5s
          </span>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Stats */}
      <div className="stat-grid">
        <StatCard label="Total Jobs"    value={metrics?.total_jobs ?? 0}      icon="⚙️" iconClass="indigo" />
        <StatCard label="Active"        value={metrics?.active_jobs ?? 0}      icon="▶️" iconClass="cyan" />
        <StatCard label="Queued"        value={metrics?.queued_jobs ?? 0}      icon="⏳" iconClass="amber" />
        <StatCard label="Completed"     value={metrics?.completed_jobs ?? 0}   icon="✅" iconClass="emerald" />
        <StatCard label="Failed"        value={metrics?.failed_jobs ?? 0}      icon="❌" iconClass="red" />
        <StatCard label="DLQ Pending"   value={metrics?.dlq_unresolved ?? 0}   icon="☠️" iconClass="red" />
        <StatCard label="Workers"       value={metrics?.total_workers ?? 0}    icon="🖥️" iconClass="indigo" />
        <StatCard label="Queues"        value={metrics?.total_queues ?? 0}     icon="📋" iconClass="cyan" />
      </div>

      {/* Quick links */}
      <div className="grid-2">
        <div className="card">
          <h3 className="mb-4" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>⚡</span> Quick Actions
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <Link to="/jobs" className="btn btn-secondary">
              📋 View All Jobs
            </Link>
            <Link to="/queues" className="btn btn-secondary">
              📂 Manage Queues
            </Link>
            <Link to="/dlq" className="btn btn-secondary">
              ☠️ Dead Letter Queue
            </Link>
            <Link to="/workers" className="btn btn-secondary">
              🖥️ Monitor Workers
            </Link>
          </div>
        </div>

        <div className="card">
          <h3 className="mb-4" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>📈</span> System Status
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="text-sm text-secondary">Workers online</span>
              <span className={`badge ${(metrics?.active_workers ?? 0) > 0 ? 'badge-active' : 'badge-offline'}`}>
                {metrics?.active_workers ?? 0} / {metrics?.total_workers ?? 0}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="text-sm text-secondary">Job success rate</span>
              <span className="text-sm font-mono" style={{ color: 'var(--c-success)' }}>
                {metrics && metrics.total_jobs > 0
                  ? `${Math.round((metrics.completed_jobs / metrics.total_jobs) * 100)}%`
                  : '—'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="text-sm text-secondary">DLQ pressure</span>
              <span className={`badge ${(metrics?.dlq_unresolved ?? 0) > 0 ? 'badge-failed' : 'badge-active'}`}>
                {(metrics?.dlq_unresolved ?? 0) > 0 ? `${metrics!.dlq_unresolved} pending` : 'Clear'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="text-sm text-secondary">Queue throughput</span>
              <span className="text-sm font-mono" style={{ color: 'var(--c-info)' }}>
                {metrics?.total_queues ?? 0} queue{metrics?.total_queues !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Architecture callout */}
      <div className="card-glass" style={{ marginTop: '1.25rem', display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
        <div style={{ fontSize: '1.5rem', flexShrink: 0 }}>🔒</div>
        <div>
          <h3 style={{ fontSize: '0.9375rem', marginBottom: '0.375rem' }}>
            Atomic Job Claiming via <code style={{ background: 'rgba(255,255,255,0.08)', padding: '0 4px', borderRadius: 4 }}>SELECT FOR UPDATE SKIP LOCKED</code>
          </h3>
          <p className="text-sm text-secondary">
            Workers claim jobs using a single atomic SQL statement — a CTE that finds the next eligible job
            with a row-level exclusive lock and immediately updates its status in the same query.
            Concurrent workers that hit the same row skip it instantly (no blocking, no double-claiming).
            All status transitions are enforced by <strong>JobStateMachine</strong>, preventing illegal moves at the application layer.
          </p>
        </div>
      </div>
    </div>
  );
}
