import { useLocation } from 'react-router-dom';
import { useAuthStore } from '../utils/store';

const ROUTE_LABELS: Record<string, string> = {
  '/dashboard':      'Dashboard',
  '/organizations':  'Organizations',
  '/projects':       'Projects',
  '/queues':         'Queues',
  '/jobs':           'Jobs',
  '/workers':        'Workers',
  '/dlq':            'Dead Letter Queue',
  '/metrics':        'Metrics',
};

export function Header() {
  const location = useLocation();
  const { user } = useAuthStore();

  const label = Object.entries(ROUTE_LABELS).find(([path]) =>
    location.pathname.startsWith(path)
  )?.[1] ?? 'Codity';

  const initials = user?.email
    ? user.email[0].toUpperCase()
    : 'U';

  return (
    <header className="header">
      <span className="header-title">{label}</span>
      <div className="header-user">
        <span className="text-sm text-muted">{user?.email ?? ''}</span>
        <div className="avatar" title={user?.email}>{initials}</div>
      </div>
    </header>
  );
}
