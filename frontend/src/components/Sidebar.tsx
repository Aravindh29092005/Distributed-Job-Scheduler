import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../utils/store';

const NAV_ITEMS = [
  { path: '/dashboard',      icon: '⬛', label: 'Dashboard',       section: 'overview' },
  { path: '/organizations',  icon: '🏢', label: 'Organizations',   section: 'resources' },
  { path: '/projects',       icon: '📁', label: 'Projects',        section: 'resources' },
  { path: '/queues',         icon: '📋', label: 'Queues',          section: 'resources' },
  { path: '/jobs',           icon: '⚙️', label: 'Jobs',            section: 'resources' },
  { path: '/workers',        icon: '🖥️', label: 'Workers',         section: 'system' },
  { path: '/dlq',            icon: '☠️', label: 'Dead Letter Queue', section: 'system' },
  { path: '/metrics',        icon: '📊', label: 'Metrics',         section: 'system' },
];

export function Sidebar() {
  const location = useLocation();
  const { logout } = useAuthStore();

  const sections = [
    { id: 'overview',   label: 'Overview' },
    { id: 'resources',  label: 'Resources' },
    { id: 'system',     label: 'System' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">⚡</div>
        <span className="sidebar-logo-text">Codity</span>
      </div>

      <nav className="sidebar-nav">
        {sections.map((section) => (
          <div key={section.id}>
            <p className="sidebar-section-title">{section.label}</p>
            {NAV_ITEMS.filter(n => n.section === section.id).map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-item ${location.pathname.startsWith(item.path) ? 'active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </div>
        ))}
      </nav>

      <div style={{ padding: '1rem 1.25rem', borderTop: '1px solid var(--c-border)' }}>
        <button
          onClick={logout}
          className="btn btn-secondary w-full"
          style={{ justifyContent: 'flex-start', gap: '0.5rem' }}
        >
          <span>↩</span> Logout
        </button>
      </div>
    </aside>
  );
}
