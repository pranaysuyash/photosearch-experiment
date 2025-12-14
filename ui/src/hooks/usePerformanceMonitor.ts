import { useRef, useEffect, useCallback } from 'react';

interface PerformanceMetrics {
  searchStartTime: number;
  searchEndTime: number;
  apiCallCount: number;
  cacheHitCount: number;
  totalImagesLoaded: number;
  averageLoadTime: number;
}

export function usePerformanceMonitor() {
  const metricsRef = useRef<PerformanceMetrics>({
    searchStartTime: 0,
    searchEndTime: 0,
    apiCallCount: 0,
    cacheHitCount: 0,
    totalImagesLoaded: 0,
    averageLoadTime: 0,
  });

  const loadTimesRef = useRef<number[]>([]);

  const startSearch = useCallback(() => {
    metricsRef.current.searchStartTime = performance.now();
  }, []);

  const endSearch = useCallback(() => {
    metricsRef.current.searchEndTime = performance.now();
  }, []);

  const recordApiCall = useCallback(() => {
    metricsRef.current.apiCallCount++;
  }, []);

  const recordCacheHit = useCallback(() => {
    metricsRef.current.cacheHitCount++;
  }, []);

  const recordImageLoad = useCallback((loadTime: number) => {
    loadTimesRef.current.push(loadTime);
    metricsRef.current.totalImagesLoaded++;

    // Keep only last 100 load times for average calculation
    if (loadTimesRef.current.length > 100) {
      loadTimesRef.current = loadTimesRef.current.slice(-100);
    }

    metricsRef.current.averageLoadTime =
      loadTimesRef.current.reduce((a, b) => a + b, 0) /
      loadTimesRef.current.length;
  }, []);

  const getMetrics = useCallback(() => {
    const metrics = metricsRef.current;
    const searchTime = metrics.searchEndTime - metrics.searchStartTime;

    return {
      ...metrics,
      searchTime,
      cacheHitRate:
        metrics.apiCallCount > 0
          ? (metrics.cacheHitCount /
              (metrics.apiCallCount + metrics.cacheHitCount)) *
            100
          : 0,
    };
  }, []);

  const resetMetrics = useCallback(() => {
    metricsRef.current = {
      searchStartTime: 0,
      searchEndTime: 0,
      apiCallCount: 0,
      cacheHitCount: 0,
      totalImagesLoaded: 0,
      averageLoadTime: 0,
    };
    loadTimesRef.current = [];
  }, []);

  // Log performance metrics in development
  useEffect(() => {
    if (import.meta.env.DEV) {
      const logMetrics = () => {
        const metrics = getMetrics();
        if (metrics.apiCallCount > 0 || metrics.cacheHitCount > 0) {
          console.log('[Performance]', {
            searchTime: `${metrics.searchTime.toFixed(2)}ms`,
            apiCalls: metrics.apiCallCount,
            cacheHits: metrics.cacheHitCount,
            cacheHitRate: `${metrics.cacheHitRate.toFixed(1)}%`,
            imagesLoaded: metrics.totalImagesLoaded,
            avgImageLoadTime: `${metrics.averageLoadTime.toFixed(2)}ms`,
          });
        }
      };

      const interval = setInterval(logMetrics, 10000); // Log every 10 seconds
      return () => clearInterval(interval);
    }
  }, [getMetrics]);

  return {
    startSearch,
    endSearch,
    recordApiCall,
    recordCacheHit,
    recordImageLoad,
    getMetrics,
    resetMetrics,
  };
}
