import { useState, useEffect, useCallback } from 'react';
import { api, type Photo } from '../api';

interface UsePhotoSearchOptions {
  initialQuery?: string;
  debounceMs?: number;
  initialFetch?: boolean;
}

export function usePhotoSearch(options: UsePhotoSearchOptions = {}) {
  const [query, setQuery] = useState(options.initialQuery || "");
  const [results, setResults] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Memoized fetch function
  const search = useCallback(async (searchQuery: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.search(searchQuery);
      setResults(res.results);
      return res.results;
    } catch (err) {
      console.error("Search failed:", err);
      setError(err instanceof Error ? err : new Error("Search failed"));
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  // Effect for query changes (optional auto-fetch)
  useEffect(() => {
    if (options.initialFetch === false && !query) return;
    
    // Simple debounce integration if needed, or rely on parent debounce
    const timer = setTimeout(() => {
        search(query);
    }, options.debounceMs || 0);

    return () => clearTimeout(timer);
  }, [query, options.debounceMs, options.initialFetch, search]);

  return {
    query,
    setQuery,
    results,
    loading,
    error,
    search, // Manual trigger
  };
}
