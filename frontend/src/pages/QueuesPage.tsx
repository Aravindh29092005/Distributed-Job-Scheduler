import { useEffect, useState } from 'react';
import { queuesService, organizationsService, projectsService } from '../services';
import { StatusBadge } from '../components/StatusBadge';

interface OrgItem   { id: string; name: string; }
interface ProjItem  { id: string; name: string; }
interface QueueItem {
  id: string; project_id: string; name: string; description?: string;
  priority: number; max_concurrent: number; paused: boolean; created_at: string;
}

export function QueuesPage() {
  // ---------- cascade state ----------
  const [orgs, setOrgs]         = useState<OrgItem[]>([]);
  const [projects, setProjects] = useState<ProjItem[]>([]);
  const [orgId, setOrgId]       = useState('');
  const [projectId, setProjectId] = useState('');
  const [orgsLoading, setOrgsLoading]         = useState(true);
  const [projectsLoading, setProjectsLoading] = useState(false);

  // ---------- queues state ----------
  const [queues, setQueues] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState('');

  // ---------- create form ----------
  const [showCreate, setShowCreate]   = useState(false);
  const [newName, setNewName]         = useState('');
  const [newDesc, setNewDesc]         = useState('');
  const [newPriority, setNewPriority] = useState(0);
  const [newMax, setNewMax]           = useState(10);
  const [creating, setCreating]       = useState(false);

  // Load orgs once
  useEffect(() => {
    organizationsService.list()
      .then(res => {
        const list: OrgItem[] = res.data ?? [];
        setOrgs(list);
        if (list.length > 0) setOrgId(list[0].id);
      })
      .catch(() => setError('Failed to load organizations.'))
      .finally(() => setOrgsLoading(false));
  }, []);

  // Load projects when org changes
  useEffect(() => {
    if (!orgId) { setProjects([]); setProjectId(''); return; }
    setProjectsLoading(true);
    setProjects([]); setProjectId('');
    projectsService.list(orgId)
      .then(res => {
        const list: ProjItem[] = res.data ?? [];
        setProjects(list);
        if (list.length > 0) setProjectId(list[0].id);
      })
      .catch(() => setError('Failed to load projects.'))
      .finally(() => setProjectsLoading(false));
  }, [orgId]);

  // Load queues when project changes
  useEffect(() => {
    if (!projectId) { setQueues([]); return; }
    setLoading(true);
    setError('');
    queuesService.list(projectId)
      .then(res => {
        const raw = res.data;
        setQueues(Array.isArray(raw) ? raw : (raw?.items ?? []));
      })
      .catch(() => setError('Failed to load queues for this project.'))
      .finally(() => setLoading(false));
  }, [projectId]);

  const refresh = () => {
    if (!projectId) return;
    setLoading(true);
    queuesService.list(projectId)
      .then(res => { const raw = res.data; setQueues(Array.isArray(raw) ? raw : (raw?.items ?? [])); })
      .catch(() => setError('Failed to refresh queues.'))
      .finally(() => setLoading(false));
  };

  const handlePause = async (queue: QueueItem) => {
    try {
      if (queue.paused) await queuesService.resume(queue.id, orgId);
      else              await queuesService.pause(queue.id, orgId);
      refresh();
    } catch { setError('Failed to update queue state.'); }
  };

  const handleCreate = async () => {
    if (!newName.trim() || !projectId || !orgId) return;
    setCreating(true);
    try {
      await queuesService.create({
        project_id: projectId,
        organization_id: orgId,
        name: newName.trim(),
        description: newDesc.trim() || undefined,
        priority: newPriority,
        max_concurrent: newMax,
      });
      setNewName(''); setNewDesc(''); setNewPriority(0); setNewMax(10);
      setShowCreate(false);
      refresh();
    } catch { setError('Failed to create queue.'); }
    finally { setCreating(false); }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Queues</h1>
          <p className="page-subtitle">{queues.length} queues loaded</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          {projectId && (
            <button className="btn btn-primary" onClick={() => setShowCreate(s => !s)}>
              + New Queue
            </button>
          )}
          <button className="btn btn-secondary btn-sm" onClick={refresh} disabled={!projectId}>
            ↺ Refresh
          </button>
        </div>
      </div>

      {/* Cascade selectors */}
      <div className="card mb-4" style={{ padding: '1.25rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 200 }}>
          <label className="form-label" style={{ display: 'block', marginBottom: '0.4rem' }}>Organization</label>
          {orgsLoading ? (
            <div className="text-sm text-muted">Loading…</div>
          ) : (
            <select className="input" value={orgId} onChange={e => setOrgId(e.target.value)}>
              {orgs.length === 0
                ? <option value="">No organizations</option>
                : orgs.map(o => <option key={o.id} value={o.id}>{o.name}</option>)
              }
            </select>
          )}
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          <label className="form-label" style={{ display: 'block', marginBottom: '0.4rem' }}>Project</label>
          {projectsLoading ? (
            <div className="text-sm text-muted">Loading…</div>
          ) : (
            <select className="input" value={projectId} onChange={e => setProjectId(e.target.value)} disabled={!orgId}>
              {projects.length === 0
                ? <option value="">No projects</option>
                : projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)
              }
            </select>
          )}
        </div>
      </div>

      {/* Create Queue Form */}
      {showCreate && (
        <div className="card mb-4" style={{ padding: '1.25rem' }}>
          <h3 className="mb-4">New Queue</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div>
              <label className="form-label">Name *</label>
              <input className="input" placeholder="e.g. email-jobs" value={newName}
                onChange={e => setNewName(e.target.value)} autoFocus />
            </div>
            <div>
              <label className="form-label">Description</label>
              <input className="input" placeholder="Optional" value={newDesc}
                onChange={e => setNewDesc(e.target.value)} />
            </div>
            <div>
              <label className="form-label">Priority</label>
              <input className="input" type="number" min={0} value={newPriority}
                onChange={e => setNewPriority(Number(e.target.value))} />
            </div>
            <div>
              <label className="form-label">Max Concurrent</label>
              <input className="input" type="number" min={1} value={newMax}
                onChange={e => setNewMax(Number(e.target.value))} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.75rem' }}>
            <button className="btn btn-primary" onClick={handleCreate} disabled={creating || !newName.trim()}>
              {creating ? <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> : 'Create'}
            </button>
            <button className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
          </div>
        </div>
      )}

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading-overlay"><div className="spinner" /></div>
      ) : queues.length === 0 && projectId ? (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <div className="empty-state-text">No queues in this project yet.</div>
        </div>
      ) : queues.length > 0 ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Max Concurrent</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {queues.map(queue => (
                <tr key={queue.id}>
                  <td>
                    <div style={{ fontWeight: 500 }}>{queue.name}</div>
                    {queue.description && <div className="text-xs text-muted">{queue.description}</div>}
                    <div className="text-xs text-muted font-mono truncate" style={{ maxWidth: 180 }}>{queue.id}</div>
                  </td>
                  <td><StatusBadge status={queue.paused ? 'paused' : 'active'} /></td>
                  <td className="font-mono text-sm">{queue.priority}</td>
                  <td className="font-mono text-sm">{queue.max_concurrent}</td>
                  <td className="text-sm text-muted">{new Date(queue.created_at).toLocaleDateString()}</td>
                  <td>
                    <button
                      className={`btn btn-sm ${queue.paused ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => handlePause(queue)}
                    >
                      {queue.paused ? '▶ Resume' : '⏸ Pause'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
