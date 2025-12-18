/* eslint-disable react-refresh/only-export-components */
import React, {
  createContext,
  useContext,
  useCallback,
  useState,
  useRef,
  useEffect,
} from 'react';
import { api, type Photo, type TimelineData } from '../api';
import { type SearchMode } from '../components/search/SearchToggle';
import { usePerformanceMonitor } from '../hooks/usePerformanceMonitor';

export type GridZoomLevel = 'compact' | 'comfortable' | 'spacious';

interface PhotoSearchContextType {
  photos: Photo[];
  loading: boolean;
  error: Error | null;
  hasMore: boolean;
  resultCount: number | null;
  searchQuery: string;
  searchMode: SearchMode;
  sortBy: string;
  typeFilter: string;
  sourceFilter: 'all' | 'local' | 'cloud' | 'hybrid';
  setSourceFilter: (filter: 'all' | 'local' | 'cloud' | 'hybrid') => void;
  favoritesFilter: string;
  tag: string | null;
  dateFrom: string | null;
  dateTo: string | null;
  timelineData: TimelineData[];
  timelineLoading: boolean;
  gridZoom: GridZoomLevel;
  setSearchQuery: (query: string) => void;
  setSearchMode: (mode: SearchMode) => void;
  setSortBy: (sort: string) => void;
  setTypeFilter: (filter: string) => void;
  setFavoritesFilter: (filter: string) => void;
  setTag: (tag: string | null) => void;
  setDateRange: (from: string | null, to: string | null) => void;
  clearDateRange: () => void;
  setGridZoom: (zoom: GridZoomLevel) => void;
  loadMore: () => void;
  search: (query: string) => void;
  clearError: () => void;
  retryLastSearch: () => void;
  refresh: () => void;
}

const PhotoSearchContext = createContext<PhotoSearchContextType | null>(null);

export function PhotoSearchProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [resultCount, setResultCount] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [searchMode, setSearchMode] = useState<SearchMode>('semantic');
  const [sortBy, setSortBy] = useState('date_desc');
  const [typeFilter, setTypeFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState<
    'all' | 'local' | 'cloud' | 'hybrid'
  >('all');
  const [favoritesFilter, setFavoritesFilter] = useState('all');
  const [tag, setTag] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState<string | null>(null);
  const [dateTo, setDateTo] = useState<string | null>(null);
  const [timelineData, setTimelineData] = useState<TimelineData[]>([]);
  const [timelineLoading, setTimelineLoading] = useState(true);

  // Grid zoom with localStorage persistence
  const [gridZoom, setGridZoomState] = useState<GridZoomLevel>(() => {
    const saved = localStorage.getItem('lm:gridZoom');
    return (saved as GridZoomLevel) || 'comfortable';
  });

  // Performance monitoring
  const { startSearch, endSearch, recordApiCall, recordCacheHit } =
    usePerformanceMonitor();

  // Performance optimizations
  const searchCache = useRef<
    Map<string, { results: Photo[]; hasMore: boolean; timestamp: number }>
  >(new Map());
  const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

  // Refs to prevent concurrent requests and track state
  const offsetRef = useRef(0);
  const loadingRef = useRef(false);
  const hasMoreRef = useRef(true);
  const initialFetchDoneRef = useRef(false);
  const lastSearchParamsRef = useRef<string>('');
  const timelineFetchedRef = useRef(false);
  const searchAbortControllerRef = useRef<AbortController | null>(null);

  // Refs for search parameters to avoid dependency issues
  const searchModeRef = useRef(searchMode);
  const sortByRef = useRef(sortBy);
  const typeFilterRef = useRef(typeFilter);
  const favoritesFilterRef = useRef(favoritesFilter);
  const tagRef = useRef<string | null>(tag);
  const dateFromRef = useRef<string | null>(dateFrom);
  const dateToRef = useRef<string | null>(dateTo);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 300); // 300ms debounce

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Update refs when state changes
  useEffect(() => {
    searchModeRef.current = searchMode;
  }, [searchMode]);

  useEffect(() => {
    sortByRef.current = sortBy;
  }, [sortBy]);

  useEffect(() => {
    typeFilterRef.current = typeFilter;
  }, [typeFilter]);
  useEffect(() => {
    // keep a ref or variable for source filter if needed in the future
  }, [sourceFilter]);

  useEffect(() => {
    favoritesFilterRef.current = favoritesFilter;
  }, [favoritesFilter]);

  useEffect(() => {
    tagRef.current = tag;
  }, [tag]);

  useEffect(() => {
    dateFromRef.current = dateFrom;
  }, [dateFrom]);

  useEffect(() => {
    dateToRef.current = dateTo;
  }, [dateTo]);

  const LIMIT = 50;

  const doSearch = useCallback(
    async (query: string, isLoadMore: boolean = false) => {
      if (loadingRef.current) return;

      if (!isLoadMore) startSearch();

      const currentSearchMode = searchModeRef.current;
      const currentSortBy = sortByRef.current;
      const currentTypeFilter = typeFilterRef.current;
      const currentFavoritesFilter = favoritesFilterRef.current;
      const currentTag = tagRef.current;
      const currentDateFrom = dateFromRef.current;
      const currentDateTo = dateToRef.current;

      const searchParams = `${query}|${currentSearchMode}|${currentSortBy}|${currentTypeFilter}|${currentFavoritesFilter}|${
        currentTag ?? ''
      }|${currentDateFrom ?? ''}|${currentDateTo ?? ''}`;
      if (!isLoadMore && searchParams === lastSearchParamsRef.current) {
        console.log(
          `[PhotoSearchContext] Skipping duplicate search: ${searchParams}`
        );
        return;
      }

      if (searchAbortControllerRef.current) {
        searchAbortControllerRef.current.abort();
      }
      const abortController = new AbortController();
      searchAbortControllerRef.current = abortController;

      loadingRef.current = true;
      setLoading(true);
      setError(null);

      if (!isLoadMore) {
        setPhotos([]);
        setResultCount(null);
        offsetRef.current = 0;
        hasMoreRef.current = true;
        setHasMore(true);
        lastSearchParamsRef.current = searchParams;
      }

      try {
        const effectiveOffset = isLoadMore ? offsetRef.current : 0;

        if (!isLoadMore && effectiveOffset === 0) {
          const cacheKey = `${searchParams}|0`;
          const cached = searchCache.current.get(cacheKey);
          if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
            console.log(
              `[PhotoSearchContext] Using cached results for: ${cacheKey}`
            );
            recordCacheHit();
            setPhotos(cached.results);
            offsetRef.current = cached.results.length;
            hasMoreRef.current = cached.hasMore;
            setHasMore(cached.hasMore);
            endSearch();
            return;
          }
        }

        console.log(
          `[PhotoSearchContext] API call: query="${query}" mode=${currentSearchMode} offset=${effectiveOffset}`
        );
        recordApiCall();

        const res = await api.search(
          query,
          currentSearchMode,
          LIMIT,
          effectiveOffset,
          currentSortBy,
          currentTypeFilter,
          currentFavoritesFilter,
          currentTag,
          currentDateFrom,
          currentDateTo,
          // pass source filter from state
          sourceFilter,
          abortController.signal
        );

        if (abortController.signal.aborted) return;

        const newPhotos = (res?.results ?? []) as Photo[];
        if (typeof res?.count === 'number') setResultCount(res.count);

        if (!isLoadMore) {
          setPhotos(newPhotos);
          offsetRef.current = newPhotos.length;

          const moreAvailable = newPhotos.length >= LIMIT;
          searchCache.current.set(`${searchParams}|0`, {
            results: newPhotos,
            hasMore: moreAvailable,
            timestamp: Date.now(),
          });

          if (searchCache.current.size > 50) {
            const entries = Array.from(searchCache.current.entries());
            entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
            const toDelete = entries.slice(0, searchCache.current.size - 50);
            toDelete.forEach(([key]) => searchCache.current.delete(key));
          }

          endSearch();
          hasMoreRef.current = moreAvailable;
          setHasMore(moreAvailable);
        } else {
          setPhotos((prev) => [...prev, ...newPhotos]);
          offsetRef.current += newPhotos.length;

          const moreAvailable = newPhotos.length >= LIMIT;
          hasMoreRef.current = moreAvailable;
          setHasMore(moreAvailable);
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          console.log('[PhotoSearchContext] Search aborted');
          return;
        }
        console.error('[PhotoSearchContext] Search failed:', err);
        setError(err instanceof Error ? err : new Error('Search failed'));
        if (!isLoadMore) setPhotos([]);
        hasMoreRef.current = false;
        setHasMore(false);
      } finally {
        loadingRef.current = false;
        setLoading(false);
        if (searchAbortControllerRef.current === abortController) {
          searchAbortControllerRef.current = null;
        }
      }
    },
    [CACHE_DURATION, endSearch, recordApiCall, recordCacheHit, startSearch]
  );

  const loadMore = useCallback(() => {
    if (!loadingRef.current && hasMoreRef.current) {
      doSearch(searchQuery, true);
    }
  }, [doSearch, searchQuery]);

  const search = useCallback(
    (query: string) => {
      doSearch(query, false);
    },
    [doSearch]
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const retryLastSearch = useCallback(() => {
    if (lastSearchParamsRef.current) {
      const params = lastSearchParamsRef.current.split('|');
      const query = params[0];
      doSearch(query, false);
    } else {
      doSearch(debouncedSearchQuery, false);
    }
  }, [doSearch, debouncedSearchQuery]);

  const refresh = useCallback(() => {
    retryLastSearch();
  }, [retryLastSearch]);

  const setDateRange = useCallback((from: string | null, to: string | null) => {
    setDateFrom(from);
    setDateTo(to);
  }, []);

  const clearDateRange = useCallback(() => {
    setDateFrom(null);
    setDateTo(null);
  }, []);

  const setGridZoom = useCallback((zoom: GridZoomLevel) => {
    setGridZoomState(zoom);
    localStorage.setItem('lm:gridZoom', zoom);
  }, []);

  // Fetch timeline data once
  useEffect(() => {
    if (!timelineFetchedRef.current) {
      timelineFetchedRef.current = true;
      console.log('[PhotoSearchContext] Fetching timeline data (once)');
      api
        .getTimeline()
        .then(setTimelineData)
        .catch(console.error)
        .finally(() => setTimelineLoading(false));
    }
  }, []);

  // Single effect to handle all search triggers
  useEffect(() => {
    if (!initialFetchDoneRef.current) {
      initialFetchDoneRef.current = true;
      doSearch('');
    } else {
      // Only re-search if we've done the initial fetch
      doSearch(debouncedSearchQuery);
    }
  }, [debouncedSearchQuery, searchMode, sortBy, typeFilter, sourceFilter]);

  const value: PhotoSearchContextType = {
    photos,
    loading,
    error,
    hasMore,
    resultCount,
    searchQuery,
    searchMode,
    sortBy,
    typeFilter,
    sourceFilter,
    favoritesFilter,
    tag,
    dateFrom,
    dateTo,
    timelineData,
    timelineLoading,
    gridZoom,
    setSearchQuery,
    setSearchMode,
    setSortBy,
    setTypeFilter,
    setSourceFilter,
    setFavoritesFilter,
    setTag,
    setDateRange,
    clearDateRange,
    setGridZoom,
    loadMore,
    search,
    clearError,
    retryLastSearch,
    refresh,
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
    throw new Error(
      'usePhotoSearchContext must be used within a PhotoSearchProvider'
    );
  }
  return context;
}
