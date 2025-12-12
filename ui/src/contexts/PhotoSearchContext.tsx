import React, { createContext, useContext, useCallback, useState, useRef, useEffect } from 'react';
import { api, type Photo } from '../api';
import { type SearchMode } from '../components/SearchToggle';

interface PhotoSearchContextType {
  photos: Photo[];
  loading: boolean;
  error: Error | null;
  hasMore: boolean;
  searchQuery: string;
  searchMode: SearchMode;
  sortBy: string;
  typeFilter: string;
  timelineData: any[];
  timelineLoading: boolean;
  setSearchQuery: (query: string) => void;
  setSearchMode: (mode: SearchMode) => void;
  setSortBy: (sort: string) => void;
  setTypeFilter: (filter: string) => void;
  loadMore: () => void;
  search: (query: string) => void;
}

const PhotoSearchContext = createContext<PhotoSearchContextType | null>(null);

export function PhotoSearchProvider({ children }: { children: React.ReactNode }) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchMode, setSearchMode] = useState<SearchMode>("metadata");
  const [sortBy, setSortBy] = useState("date_desc");
  const [typeFilter, setTypeFilter] = useState("all");
  const [timelineData, setTimelineData] = useState<any[]>([]);
  const [timelineLoading, setTimelineLoading] = useState(true);
  
  // Refs to prevent concurrent requests and track state
  const offsetRef = useRef(0);
  const loadingRef = useRef(false);
  const hasMoreRef = useRef(true);
  const initialFetchDoneRef = useRef(false);
  const lastSearchParamsRef = useRef<string>('');
  const timelineFetchedRef = useRef(false);
  const searchAbortControllerRef = useRef<AbortController | null>(null);
  
  const LIMIT = 50;

  const doSearch = useCallback(async (query: string, isLoadMore: boolean = false) => {
    if (loadingRef.current) return;

    // Create search params signature to prevent duplicate requests
    const searchParams = `${query}|${searchMode}|${sortBy}|${typeFilter}`;
    if (!isLoadMore && searchParams === lastSearchParamsRef.current) {
      console.log(`[PhotoSearchContext] Skipping duplicate search: ${searchParams}`);
      return;
    }

    // Cancel any ongoing search
    if (searchAbortControllerRef.current) {
      searchAbortControllerRef.current.abort();
    }
    searchAbortControllerRef.current = new AbortController();

    loadingRef.current = true;
    setLoading(true);
    setError(null);

    if (!isLoadMore) {
      setPhotos([]);
      offsetRef.current = 0;
      hasMoreRef.current = true;
      setHasMore(true);
      lastSearchParamsRef.current = searchParams;
    }

    try {
      const effectiveOffset = isLoadMore ? offsetRef.current : 0;
      console.log(`[PhotoSearchContext] Single API call: query="${query}" mode=${searchMode} offset=${effectiveOffset}`);
      
      const res = await api.search(query, searchMode, LIMIT, effectiveOffset, sortBy, typeFilter, searchAbortControllerRef.current?.signal);
      
      // Check if request was aborted
      if (searchAbortControllerRef.current?.signal.aborted) {
        return;
      }

      const newPhotos = res.results || [];

      if (!isLoadMore) {
        setPhotos(newPhotos);
        offsetRef.current = newPhotos.length;
      } else {
        setPhotos(prev => [...prev, ...newPhotos]);
        offsetRef.current += newPhotos.length;
      }

      const moreAvailable = newPhotos.length >= LIMIT;
      hasMoreRef.current = moreAvailable;
      setHasMore(moreAvailable);
      
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        console.log("[PhotoSearchContext] Search aborted");
        return;
      }
      console.error("[PhotoSearchContext] Search failed:", err);
      setError(err instanceof Error ? err : new Error("Search failed"));
      if (!isLoadMore) setPhotos([]);
      hasMoreRef.current = false;
      setHasMore(false);
    } finally {
      loadingRef.current = false;
      setLoading(false);
      searchAbortControllerRef.current = null;
    }
  }, [searchMode, sortBy, typeFilter]);

  const loadMore = useCallback(() => {
    if (!loadingRef.current && hasMoreRef.current) {
      doSearch(searchQuery, true);
    }
  }, [doSearch, searchQuery]);

  const search = useCallback((query: string) => {
    doSearch(query, false);
  }, [doSearch]);

  // Fetch timeline data once
  useEffect(() => {
    if (!timelineFetchedRef.current) {
      timelineFetchedRef.current = true;
      console.log("[PhotoSearchContext] Fetching timeline data (once)");
      api.getTimeline()
        .then(setTimelineData)
        .catch(console.error)
        .finally(() => setTimelineLoading(false));
    }
  }, []);

  // Single effect to handle all search triggers
  useEffect(() => {
    if (!initialFetchDoneRef.current) {
      initialFetchDoneRef.current = true;
      doSearch("");
    } else {
      // Only re-search if we've done the initial fetch
      doSearch(searchQuery);
    }
  }, [searchQuery, searchMode, sortBy, typeFilter, doSearch]);

  const value: PhotoSearchContextType = {
    photos,
    loading,
    error,
    hasMore,
    searchQuery,
    searchMode,
    sortBy,
    typeFilter,
    timelineData,
    timelineLoading,
    setSearchQuery,
    setSearchMode,
    setSortBy,
    setTypeFilter,
    loadMore,
    search,
  };

  return (
    <PhotoSearchContext.Provider value={value}>
      {children}
    </PhotoSearchContext.Provider>
  );
}

export function usePhotoSearchContext() {
  const context = useContext(PhotoSearchContext);
  if (!context) {
    throw new Error('usePhotoSearchContext must be used within a PhotoSearchProvider');
  }
  return context;
}