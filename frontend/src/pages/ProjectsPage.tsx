import { useEffect, useState } from 'react';
import { projectsService, organizationsService } from '../services';

interface Organization {
  id: string;
  name: string;
}

interface Project {
  id: string;
  organization_id: string;
  name: string;
  description?: string;
  created_at: string;
}

export function ProjectsPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState('');
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [orgsLoading, setOrgsLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');
  const [creating, setCreating] = useState(false);

  // Load organizations for the selector on mount
  useEffect(() => {
    organizationsService.list()
      .then(res => {
        const list = res.data ?? [];
        setOrgs(list);
        if (list.length > 0) setSelectedOrgId(list[0].id);
      })
      .catch(() => setError('Failed to load organizations.'))
      .finally(() => setOrgsLoading(false));
  }, []);

  // Fetch projects whenever the selected org changes
  useEffect(() => {
    if (!selectedOrgId) return;
    setLoading(true);
    setError('');
    projectsService.list(selectedOrgId)
      .then(res => setProjects(res.data ?? []))
      .catch(() => setError('Failed to load projects for this organization.'))
      .finally(() => setLoading(false));
  }, [selectedOrgId]);

  const handleCreate = async () => {
    if (!newProjectName.trim() || !selectedOrgId) return;
    setCreating(true);
    try {
      await projectsService.create({
        organization_id: selectedOrgId,
        name: newProjectName.trim(),
        description: newProjectDesc.trim() || undefined,
      });
      setNewProjectName('');
      setNewProjectDesc('');
      setShowCreate(false);
      // Refresh list
      const res = await projectsService.list(selectedOrgId);
      setProjects(res.data ?? []);
    } catch {
      setError('Failed to create project.');
    } finally {
      setCreating(false);
    }
  };

  const selectedOrg = orgs.find(o => o.id === selectedOrgId);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Projects</h1>
          <p className="page-subtitle">Projects belong to organizations</p>
        </div>
        {selectedOrgId && (
          <button className="btn btn-primary" onClick={() => setShowCreate(s => !s)}>
            + New Project
          </button>
        )}
      </div>

      {/* Organization Selector */}
      <div className="card mb-4" style={{ padding: '1.25rem' }}>
        <label className="form-label" style={{ marginBottom: '0.5rem', display: 'block' }}>
          Organization
        </label>
        {orgsLoading ? (
          <div className="text-sm text-muted">Loading organizations…</div>
        ) : orgs.length === 0 ? (
          <div className="alert alert-error">
            No organizations found. Create one first from the Organizations page.
          </div>
        ) : (
          <select
            className="input"
            value={selectedOrgId}
            onChange={e => setSelectedOrgId(e.target.value)}
            style={{ cursor: 'pointer' }}
          >
            {orgs.map(org => (
              <option key={org.id} value={org.id}>
                {org.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Create Project Form */}
      {showCreate && (
        <div className="card mb-4" style={{ padding: '1.25rem' }}>
          <h3 className="mb-4">New Project in {selectedOrg?.name}</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <input
              className="input"
              placeholder="Project name"
              value={newProjectName}
              onChange={e => setNewProjectName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreate()}
              autoFocus
            />
            <input
              className="input"
              placeholder="Description (optional)"
              value={newProjectDesc}
              onChange={e => setNewProjectDesc(e.target.value)}
            />
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button className="btn btn-primary" onClick={handleCreate} disabled={creating || !newProjectName.trim()}>
                {creating ? <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> : 'Create'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading-overlay"><div className="spinner" /></div>
      ) : projects.length === 0 && selectedOrgId ? (
        <div className="empty-state">
          <div className="empty-state-icon">📁</div>
          <div className="empty-state-text">No projects in this organization yet.</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '0.875rem' }}>
          {projects.map(p => (
            <div key={p.id} className="card">
              <h3 style={{ marginBottom: '0.25rem' }}>{p.name}</h3>
              {p.description && <p className="text-sm text-secondary mb-2">{p.description}</p>}
              <p className="text-xs text-muted font-mono">{p.id}</p>
              <p className="text-xs text-muted" style={{ marginTop: '0.25rem' }}>
                Created {new Date(p.created_at).toLocaleDateString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
