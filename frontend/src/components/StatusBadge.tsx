interface StatusBadgeProps {
  status: string;
}

const STATUS_LABELS: Record<string, string> = {
  queued:            'Queued',
  scheduled:         'Scheduled',
  claimed:           'Claimed',
  running:           'Running',
  completed:         'Completed',
  failed:            'Failed',
  retrying:          'Retrying',
  dead_letter_queue: 'DLQ',
  cancelled:         'Cancelled',
  active:            'Active',
  idle:              'Idle',
  offline:           'Offline',
  paused:            'Paused',
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const label = STATUS_LABELS[status] ?? status;
  return (
    <span className={`badge badge-${status}`}>
      {label}
    </span>
  );
}
