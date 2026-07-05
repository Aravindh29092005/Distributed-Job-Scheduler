import { formatDate, formatDuration } from '../utils/date';
import { StatusBadge } from './StatusBadge';

export interface RetryHistoryItem {
  id: string;
  attemptNumber: number;
  status: string;
  startedAt: string;
  completedAt?: string;
  error?: string;
  nextRetryAt?: string;
}

interface RetryHistoryProps {
  retries: RetryHistoryItem[];
  loading?: boolean;
}

export function RetryHistory({ retries, loading }: RetryHistoryProps) {
  if (loading) {
    return <div className="text-center py-8 text-gray-500">Loading retry history...</div>;
  }

  if (retries.length === 0) {
    return <div className="text-center py-8 text-gray-500">No retries</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-4 py-2 text-left font-semibold text-gray-700">
              Attempt
            </th>
            <th className="px-4 py-2 text-left font-semibold text-gray-700">
              Status
            </th>
            <th className="px-4 py-2 text-left font-semibold text-gray-700">
              Started
            </th>
            <th className="px-4 py-2 text-left font-semibold text-gray-700">
              Duration
            </th>
            <th className="px-4 py-2 text-left font-semibold text-gray-700">
              Error
            </th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {retries.map((retry) => (
            <tr key={retry.id} className="hover:bg-gray-50">
              <td className="px-4 py-2">#{retry.attemptNumber}</td>
              <td className="px-4 py-2">
                <StatusBadge status={retry.status} />
              </td>
              <td className="px-4 py-2 text-gray-600">
                {formatDate(retry.startedAt)}
              </td>
              <td className="px-4 py-2 text-gray-600">
                {retry.completedAt
                  ? formatDuration(retry.startedAt, retry.completedAt)
                  : '—'}
              </td>
              <td className="px-4 py-2 text-red-600 text-xs font-mono">
                {retry.error ? retry.error.substring(0, 50) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
