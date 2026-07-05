import { useState } from 'react';
import { formatDate } from '../utils/date';

interface LogEntry {
  id: string;
  level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG';
  timestamp: string;
  message: string;
  context?: Record<string, any>;
}

interface ExecutionLogsProps {
  logs: LogEntry[];
  loading?: boolean;
}

export function ExecutionLogs({ logs, loading }: ExecutionLogsProps) {
  const [expandedLog, setExpandedLog] = useState<string | null>(null);

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR':
        return 'text-red-600 bg-red-50';
      case 'WARNING':
        return 'text-yellow-600 bg-yellow-50';
      case 'INFO':
        return 'text-blue-600 bg-blue-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  if (loading) {
    return <div className="text-center py-8 text-gray-500">Loading logs...</div>;
  }

  if (logs.length === 0) {
    return <div className="text-center py-8 text-gray-500">No logs available</div>;
  }

  return (
    <div className="space-y-2 font-mono text-sm">
      {logs.map((log) => (
        <div
          key={log.id}
          className={`p-3 rounded border cursor-pointer hover:bg-opacity-75 ${getLevelColor(log.level)}`}
          onClick={() =>
            setExpandedLog(expandedLog === log.id ? null : log.id)
          }
        >
          <div className="flex items-start gap-3">
            <span className="font-semibold w-12">{log.level}</span>
            <span className="text-gray-500 w-32">
              {formatDate(log.timestamp)}
            </span>
            <span className="flex-1">{log.message}</span>
          </div>
          {expandedLog === log.id && log.context && (
            <div className="mt-2 p-2 bg-black bg-opacity-5 rounded text-xs">
              <pre>{JSON.stringify(log.context, null, 2)}</pre>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
