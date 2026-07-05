/**
 * Polling Hook
 * Polls an async function at specified intervals
 * 
 * POLLING STRATEGY:
 * - Used for live updates instead of WebSockets (planned future improvement)
 * - Automatically refetches data at configured intervals
 * - Handles errors gracefully
 * - Cleanup on component unmount
 */

import { useEffect, useState, useCallback, useRef } from 'react';

interface UsePollingOptions {
  interval: number;
  onError?: (error: Error) => void;
  enabled?: boolean;
}

export function usePolling<T>(
  fetchFn: () => Promise<T>,
  options: UsePollingOptions
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      const result = await fetchFn();
      setData(result);
      setError(null);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      options.onError?.(error);
    } finally {
      setLoading(false);
    }
  }, [fetchFn, options]);

  useEffect(() => {
    const enabled = options.enabled !== false;

    if (!enabled) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Initial fetch
    fetch();

    // Set up interval
    intervalRef.current = setInterval(fetch, options.interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [fetch, options.interval, options.enabled]);

  return { data, loading, error, refetch: fetch };
}
