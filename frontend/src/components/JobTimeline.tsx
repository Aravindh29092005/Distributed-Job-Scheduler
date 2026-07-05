import { AlertCircle, CheckCircle2, Clock, RefreshCw } from 'lucide-react';

export interface TimelineEvent {
  id: string;
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'retrying';
  timestamp: string;
  duration?: number;
  message?: string;
}

interface JobTimelineProps {
  events: TimelineEvent[];
}

export function JobTimeline({ events }: JobTimelineProps) {
  const getIcon = (status: TimelineEvent['status']) => {
    switch (status) {
      case 'succeeded':
        return <CheckCircle2 className="text-green-500" size={24} />;
      case 'failed':
        return <AlertCircle className="text-red-500" size={24} />;
      case 'running':
        return <RefreshCw className="text-blue-500 animate-spin" size={24} />;
      default:
        return <Clock className="text-gray-400" size={24} />;
    }
  };

  return (
    <div className="space-y-6">
      {events.map((event, index) => (
        <div key={event.id} className="flex gap-4">
          <div className="flex flex-col items-center">
            {getIcon(event.status)}
            {index < events.length - 1 && (
              <div className="w-1 h-12 bg-gray-300 mt-2" />
            )}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold capitalize">{event.status}</span>
              <span className="text-sm text-gray-500">
                {new Date(event.timestamp).toLocaleString()}
              </span>
            </div>
            {event.duration && (
              <p className="text-sm text-gray-600">
                Duration: {(event.duration / 1000).toFixed(2)}s
              </p>
            )}
            {event.message && (
              <p className="text-sm text-gray-700 mt-1">{event.message}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
