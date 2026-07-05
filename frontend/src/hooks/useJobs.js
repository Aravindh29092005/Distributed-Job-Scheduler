import { useState, useEffect } from 'react';
import { jobsService } from '../services';
export function useJobs(queueId) {
  const [jobs, setJobs] = useState([]);
  useEffect(() => {
    if (queueId) {
      jobsService.list({ queue_id: queueId }).then(res => setJobs(res.data.items || []));
    }
  }, [queueId]);
  return jobs;
}
export default useJobs;
