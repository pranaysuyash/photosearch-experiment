import { useState, useEffect, useCallback, useRef } from 'react';
import { api, type Photo } from '../api';

interface UsePhotoSearchOptions {
  initialQuery?: string;
  debounceMs?: number;
  initialFetch?: boolean;
  mode?: string;
  sortBy?: string;
  typeFilter?: string;
}

export function usePhotoSearch(options: UsePhotoSearchOptions = {}) {
  const [query, setQuery] = useState(options.initialQuery || "");
  const [results, setResults] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [hasMore, setHasMore] = useState(true);
  
  // Store ALL mutable values in refs to prevent re-render loops
  const offsetRef = useRef(0);
  const loadingRef = useRef(false);
  const hasMoreRef = useRef(true);
  const queryRef = useRef(query);
  const initialFetchDoneRef = useRef(false);
  
  // Store options in refs so they don't cause useCallback recreation
  const optionsRef = useRef(options);
  optionsRef.current = options;
  
  const LIMIT = 50;

  // Stable search function - no dependencies that change
  const doSearch = useCallback(async (searchQuery: string, isLoadMore: boolean) => {
    // Prevent concurrent requests
    if (loadingRef.current) {
      return;
    }

    loadingRef.current = true;
    setLoading(true);
    setError(null);

    if (!isLoadMore) {
      setResults([]);
      offsetRef.current = 0;
      hasMoreRef.current = true;
      setHasMore(true);
    }

    try {
      const opts = optionsRef.current;
      const searchMode = opts.mode || 'semantic';
      const sortBy = opts.sortBy || 'date_desc';
      const typeFilter = opts.typeFilter || 'all';
      const effectiveOffset = isLoadMore ? offsetRef.current : 0;
      
      console.log(`[usePhotoSearch] Fetching: query="${searchQuery}" mode=${searchMode} offset=${effectiveOffset}`);
      
      const res = await api.search(searchQuery, searchMode, LIMIT, effectiveOffset, sortBy, typeFilter);
      const newPhotos = res.results || [];

      if (!isLoadMore) {
        setResults(newPhotos);
        offsetRef.current = newPhotos.length;
      } else {
        setResults(prev => [...prev, ...newPhotos]);
        offsetRef.current += newPhotos.length;
      }

      // If we got fewer than limit, no more pages
      const moreAvailable = newPhotos.length >= LIMIT;
      hasMoreRef.current = moreAvailable;
      setHasMore(moreAvailable);
      console.log(`[usePhotoSearch] Got ${newPhotos.length} results, hasMore=${moreAvailable}, offset now=${offsetRef.current}`);
      
    } catch (err) {
      console.error("[usePhotoSearch] Search failed:", err);
      setError(err instanceof Error ? err : new Error("Search failed"));
      if (!isLoadMore) setResults([]);
      hasMoreRef.current = false;
      setHasMore(false);
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, []); // NO dependencies - reads from refs

  const loadMore = useCallback(() => {
    if (!loadingRef.current && hasMoreRef.current) {
      console.log('[usePhotoSearch] loadMore triggered, offset:', offsetRef.current);
      doSearch(queryRef.current, true);
    }
  }, [doSearch]);

  // Keep queryRef in sync
  useEffect(() => {
    queryRef.current = query;
  }, [query]);

  // Initial fetch effect - runs once on mount
  useEffect(() => {
    if (optionsRef.current.initialFetch === false) {
      return;
    }
    if (initialFetchDoneRef.current) {
      return;
    }
    initialFetchDoneRef.current = true;
    doSearch(query, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  // Query change effect - debounced
  useEffect(() => {
    // Skip if this is the initial render (handled by initial fetch effect)
    if (!initialFetchDoneRef.current) {
      return;
    }
    
    const timer = setTimeout(() => {
      doSearch(query, false);
    }, optionsRef.current.debounceMs || 300);

    return () => clearTimeout(timer);
  }, [query, doSearch]);

  // Re-fetch when mode/sort/filter changes (but not on initial mount)
  useEffect(() => {
    if (!initialFetchDoneRef.current) {
      return;
    }
    doSearch(queryRef.current, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options.mode, options.sortBy, options.typeFilter]);

  return {
    query,
    setQuery,
    results,
    loading,
    error,
    hasMore,
    loadMore,
    search: (q: string) => doSearch(q, false),
  };
}
