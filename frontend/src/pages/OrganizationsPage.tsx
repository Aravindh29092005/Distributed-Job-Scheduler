import { useEffect, useState } from 'react';
import { organizationsService } from '../services';

interface Organization {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export function OrganizationsPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchOrgs = async () => {
    try {
      const res = await organizationsService.list();
      setOrgs(res.data ?? []);
      setError('');
    } catch {
      setError('Failed to load organizations.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchOrgs(); }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await organizationsService.create({ name: newName.trim() });
      setNewName('');
      setShowCreate(false);
      fetchOrgs();
    } catch {
      setError('Failed to create organization.');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Organizations</h1>
          <p className="page-subtitle">{orgs.length} total</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          + New Organization
        </button>
      </div>

      {showCreate && (
        <div className="card mb-4" style={{ padding: '1.25rem' }}>
          <h3 className="mb-4">Create Organization</h3>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <input
              className="input"
              placeholder="Organization name"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreate()}
              autoFocus
            />
            <button className="btn btn-primary" onClick={handleCreate} disabled={creating}>
              {creating ? <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> : 'Create'}
            </button>
            <button className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
          </div>
        </div>
      )}

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading-overlay"><div className="spinner" /></div>
      ) : orgs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🏢</div>
          <div className="empty-state-text">No organizations yet. Create one to get started.</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '0.875rem' }}>
          {orgs.map(org => (
            <div key={org.id} className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <h3 style={{ marginBottom: '0.25rem' }}>{org.name}</h3>
                <p className="text-xs text-muted font-mono">{org.id}</p>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span className="text-xs text-muted">
                  Created {new Date(org.created_at).toLocaleDateString()}
                </span>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => {
                    if (confirm(`Archive "${org.name}"?`)) {
                      organizationsService.archive(org.id).then(fetchOrgs).catch(() => setError('Failed to archive.'));
                    }
                  }}
                >
                  Archive
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
