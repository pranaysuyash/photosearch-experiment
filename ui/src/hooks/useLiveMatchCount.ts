import { useState, useEffect, useCallback } from 'react';

type SearchMode = 'metadata' | 'hybrid' | 'semantic';

interface UseLiveMatchCountProps {
  query: string;
  searchMode: SearchMode;
  debounceMs?: number;
}

interface MatchCountResult {
  count: number | null;
  isLoading: boolean;
  error: string | null;
}

export const useLiveMatchCount = ({
  query,
  searchMode,
  debounceMs = 500
}: UseLiveMatchCountProps): MatchCountResult => {
  const [count, setCount] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCount = useCallback(async (searchQuery: string, mode: SearchMode) => {
    if (!searchQuery.trim()) {
      setCount(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/search/count', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
          mode: mode
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setCount(data.count);
    } catch (err) {
      console.error('Failed to get match count:', err);
      setError(err instanceof Error ? err.message : 'Failed to get match count');
      setCount(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Reset state when query is empty
    if (!query.trim()) {
      setCount(null);
      setIsLoading(false);
      setError(null);
      return;
    }

    // Set loading immediately when query changes
    setIsLoading(true);

    // Debounce the API call
    const timer = setTimeout(() => {
      fetchCount(query, searchMode);
    }, debounceMs);

    return () => clearTimeout(timer);
  }, [query, searchMode, debounceMs, fetchCount]);

  return { count, isLoading, error };
};
