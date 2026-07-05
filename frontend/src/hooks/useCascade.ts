/**
 * Shared cascade-select hook: Org → Project → Queue
 * Used by QueuesPage and JobsPage to avoid manual UUID entry.
 */
import { useEffect, useState } from 'react';
import { organizationsService, projectsService, queuesService } from '../services';

export interface OrgItem   { id: string; name: string; }
export interface ProjItem  { id: string; name: string; organization_id: string; }
export interface QueueItem { id: string; name: string; project_id: string; }

export function useCascade() {
  const [orgs, setOrgs]     = useState<OrgItem[]>([]);
  const [projects, setProjects] = useState<ProjItem[]>([]);
  const [queues, setQueues] = useState<QueueItem[]>([]);

  const [orgId, setOrgId]       = useState('');
  const [projectId, setProjectId] = useState('');
  const [queueId, setQueueId]   = useState('');

  const [orgsLoading, setOrgsLoading]     = useState(true);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [queuesLoading, setQueuesLoading] = useState(false);

  const [error, setError] = useState('');

  // Load orgs on mount
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
    if (!projectId) { setQueues([]); setQueueId(''); return; }
    setQueuesLoading(true);
    setQueues([]); setQueueId('');
    queuesService.list(projectId)
      .then(res => {
        const raw = res.data;
        const list: QueueItem[] = Array.isArray(raw) ? raw : (raw?.items ?? []);
        setQueues(list);
        if (list.length > 0) setQueueId(list[0].id);
      })
      .catch(() => setError('Failed to load queues.'))
      .finally(() => setQueuesLoading(false));
  }, [projectId]);

  return {
    orgs, projects, queues,
    orgId, setOrgId,
    projectId, setProjectId,
    queueId, setQueueId,
    orgsLoading, projectsLoading, queuesLoading,
    error, setError,
  };
}
