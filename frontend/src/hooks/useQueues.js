import { useState, useEffect } from 'react';
import { queuesService } from '../services';
export function useQueues(projectId) {
  const [queues, setQueues] = useState([]);
  useEffect(() => {
    if (projectId) {
      queuesService.list(projectId).then(res => setQueues(res.data || []));
    }
  }, [projectId]);
  return queues;
}
export default useQueues;
