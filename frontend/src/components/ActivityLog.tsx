export type LogLevel = 'info' | 'success' | 'error' | 'warn';

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
}

interface ActivityLogProps {
  entries: LogEntry[];
  title?: string;
  onClear?: () => void;
}

const LEVEL_STYLES: Record<LogLevel, string> = {
  info: 'var(--c-info)',
  success: 'var(--c-success)',
  error: 'var(--c-danger)',
  warn: 'var(--c-warning)',
};

export function ActivityLog({ entries, title = 'Activity Log', onClear }: ActivityLogProps) {
  const fmt = (s: string) =>
    new Date(s).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  return (
    <div className="card" style={{ padding: '1rem', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>{title}</h3>
        {onClear && entries.length > 0 && (
          <button className="btn btn-secondary btn-sm" onClick={onClear} type="button">
            Clear
          </button>
        )}
      </div>

      <div
        style={{
          flex: 1,
          minHeight: 280,
          maxHeight: 520,
          overflowY: 'auto',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.75rem',
          background: 'var(--c-surface-2)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--c-border)',
          padding: '0.75rem',
        }}
      >
        {entries.length === 0 ? (
          <p className="text-sm text-muted" style={{ textAlign: 'center', padding: '2rem 0' }}>
            No activity yet. Post a job or change filters to see logs here.
          </p>
        ) : (
          entries.map((entry) => (
            <div
              key={entry.id}
              style={{
                display: 'flex',
                gap: '0.5rem',
                padding: '0.35rem 0',
                borderBottom: '1px solid var(--c-border)',
              }}
            >
              <span className="text-muted" style={{ flexShrink: 0, width: 72 }}>
                {fmt(entry.timestamp)}
              </span>
              <span
                style={{
                  flexShrink: 0,
                  width: 56,
                  fontWeight: 600,
                  color: LEVEL_STYLES[entry.level],
                  textTransform: 'uppercase',
                }}
              >
                {entry.level}
              </span>
              <span style={{ color: 'var(--c-text-secondary)', wordBreak: 'break-word' }}>
                {entry.message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export function createLogEntry(level: LogLevel, message: string): LogEntry {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: new Date().toISOString(),
    level,
    message,
  };
}
