/**
 * Analytics Dashboard
 *
 * Comprehensive analytics and insights UI with:
 * - Library overview with key metrics
 * - Content insights and patterns
 * - Search analytics and user behavior
 * - Performance metrics and optimization suggestions
 * - Storage analysis and cleanup recommendations
 * - Interactive charts and visualizations
 */

import { useState, useEffect, useCallback, memo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart3,
  TrendingUp,
  HardDrive,
  Users,
  Search,
  Image as ImageIcon,
  Calendar,
  Zap,
  Target,
  Download,
  AlertCircle,
  Loader2,
  Camera,
  FileText,
  MapPin,
  Tag,
  Activity,
  Database,
  Server,
  RefreshCw,
} from 'lucide-react';
import {
  api,
  type FaceStatsSummary,
  type PerformanceCacheStats,
  type PlaceCluster,
  type TagSummary,
  type TimelineData,
} from '../../api';
import { glass } from '../../design/glass';
import { useAmbientThemeContext } from '../../contexts/AmbientThemeContext';

export interface LibraryAnalytics {
  total_photos: number;
  total_size_gb: number;
  new_photos: number;
  duplicates_found: number;
  faces_detected: number;
  ocr_processed: number;
  albums_created: number;
  search_queries: number;
  unique_search_terms: number;
  engagement_rate: number;
  processing_queue_size: number;
  error_rate: number;
  storage_growth_rate: number;
  created_at: string;
}

export interface ContentInsight {
  id: string;
  insight_type: string;
  insight_value: string;
  photo_count: number;
  confidence_score: number;
  title?: string;
  description?: string;
  created_at: string;
}

export interface SearchAnalytics {
  query_text: string;
  search_type: string;
  results_count: number;
  results_clicked: number;
  search_duration_ms: number;
  created_at: string;
}

export interface UserBehavior {
  action_type: string;
  target_type: string;
  session_duration_ms: number;
  created_at: string;
}

export interface PerformanceMetric {
  metric_name: string;
  metric_value: number;
  metric_unit: string;
  operation_type: string;
  processing_time_ms: number;
  created_at: string;
}

function AnalyticsDashboard() {
  const { isDark } = useAmbientThemeContext();
  const surfaceClass = isDark ? 'bg-black/20' : 'bg-white/40';
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<
    'overview' | 'content' | 'search' | 'performance' | 'storage'
  >('overview');
  const [libraryAnalytics, setLibraryAnalytics] =
    useState<LibraryAnalytics | null>(null);
  const [contentInsights, setContentInsights] = useState<ContentInsight[]>([]);
  const [searchAnalytics, setSearchAnalytics] = useState<SearchAnalytics[]>([]);
  const [userBehavior, setUserBehavior] = useState<UserBehavior[]>([]);
  const [performanceMetrics, setPerformanceMetrics] = useState<
    PerformanceMetric[]
  >([]);
  const [topLocations, setTopLocations] = useState<PlaceCluster[]>([]);
  const [timelineYears, setTimelineYears] = useState<
    Array<{ year: string; count: number }>
  >([]);
  const [popularTags, setPopularTags] = useState<TagSummary[]>([]);
  const [facesStats, setFacesStats] = useState<FaceStatsSummary | null>(null);
  const [perfCacheStats, setPerfCacheStats] =
    useState<PerformanceCacheStats | null>(null);
  const [storageByFormat, setStorageByFormat] = useState<
    Array<{ ext: string; count: number; bytes: number }>
  >([]);
  const [sizeBuckets, setSizeBuckets] = useState<
    Array<{ label: string; count: number; pct: number; barClass: string }>
  >([]);
  const [samplePhotoCount, setSamplePhotoCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState('30d');
  const [autoRefresh, setAutoRefresh] = useState(false);

  const loadAnalytics = useCallback(async () => {
    try {
      setLoading(true);

      // Get library statistics using existing API
      const stats = await api.getStats();

      // Get comprehensive analytics data from real APIs
      const [tagsData, duplicatesStats, locationStats, notesStats, albumsData] =
        await Promise.all([
          api.listTags().catch(() => ({ tags: [] })),
          api
            .getDuplicateStats()
            .catch(() => ({ total_duplicate_groups: 0, total_duplicates: 0 })),
          api
            .getLocationStats()
            .catch(() => ({
              total_places: 0,
              photos_with_locations: 0,
              photos_without_locations: 0,
            })),
          api
            .getNotesStats()
            .catch(() => ({ total_notes: 0, photos_with_notes: 0 })),
          api.listAlbums().catch(() => ({ albums: [] })),
        ]);

      // Get face stats, location clusters, photo timeline, and face-pipeline
      // cache stats from real APIs. Per-call catches keep a single failure
      // from aborting the whole load.
      const [faceStatsResult, placeClusters, timelineData, perfCacheResult, perfMetricsResult, ocrStatsResult] =
        await Promise.all([
          api
            .getFaceStats()
            .catch(() => null)
            .then((data) => (data ?? null) as FaceStatsSummary | null),
          api
            .getPlaceClusters(2)
            .catch(() => [])
            .then((clusters) => (clusters ?? []) as PlaceCluster[]),
          api.getTimeline().catch(() => [] as TimelineData[]),
          api.getPerformanceCacheStats().catch(() => null),
          api.getPerformanceMetrics(20).catch(() => null),
          api.getOcrStats().catch(() => null),
        ]);

      // OCR stats are only meaningful on a successful summary response.
      const ocrProcessed =
        ocrStatsResult?.status === 'success'
          ? (ocrStatsResult.stats?.total_images_processed ?? 0)
          : (notesStats.photos_with_notes || 0); // notes proxy fallback

      // Face stats are only meaningful when the face pipeline is available.
      const validFaceStats =
        faceStatsResult && faceStatsResult.status === 'available'
          ? faceStatsResult
          : null;
      setFacesStats(validFaceStats);
      setTopLocations(placeClusters.slice(0, 10));

      // The timeline endpoint returns per-month counts; aggregate per year.
      const yearCounts = new Map<string, number>();
      timelineData.forEach((entry) => {
        if (!entry?.date) return;
        const year = entry.date.slice(0, 4);
        yearCounts.set(year, (yearCounts.get(year) || 0) + (entry.count || 0));
      });
      setTimelineYears(
        Array.from(yearCounts.entries())
          .map(([year, count]) => ({ year, count }))
          .sort((a, b) => b.year.localeCompare(a.year))
          .slice(0, 3)
      );

      // Cache stats are only reported when the intelligent cache is enabled.
      setPerfCacheStats(
        perfCacheResult &&
          perfCacheResult.status === 'enabled' &&
          perfCacheResult.cache_statistics
          ? perfCacheResult.cache_statistics
          : null
      );

      // Popular tags derived from the already-loaded tag list.
      setPopularTags(
        [...(tagsData.tags ?? [])]
          .sort((a, b) => b.photo_count - a.photo_count)
          .slice(0, 6)
      );

      // Calculate real analytics values
      const totalPhotos = stats.active_files || 0;
      const totalTags = tagsData.tags?.length || 0;
      const totalDuplicates = duplicatesStats.total_duplicates || 0;
      const photosWithLocations = locationStats.photos_with_locations || 0;
      const photosWithoutLocations =
        locationStats.photos_without_locations || 0;
      const albumsCreated = albumsData.albums?.length || 0;

      // Get photo format and quality analysis from sample
      const formatDistribution: Record<string, number> = {};
      const qualityDistribution = { high: 0, medium: 0, low: 0 };
      let largestPhotoSize = 0;
      let totalPhotoSize = 0;
      let photosWithSize = 0;
      const formatSizes: Record<string, { count: number; bytes: number }> = {};
      const sizeBucketCounts = { lt1mb: 0, b1to5mb: 0, b5to10mb: 0, gt10mb: 0 };

      // Get a sample for detailed analysis
      const sampleSize = Math.min(200, totalPhotos);
      if (sampleSize > 0) {
        try {
          const sampleResponse = await api.search(
            '',
            'metadata',
            sampleSize,
            0
          );

          type SamplePhoto = {
            metadata?: {
              file?: { extension?: string; size_bytes?: number };
              filesystem?: { size_bytes?: number };
              image?: { width?: number; height?: number };
            };
          };
          sampleResponse.photos?.forEach((photo: SamplePhoto) => {
            // Analyze file formats
            if (photo.metadata?.file?.extension) {
              const ext = photo.metadata.file.extension.toUpperCase();
              formatDistribution[ext] = (formatDistribution[ext] || 0) + 1;
            }

            // Calculate photo sizes (size lives under filesystem in extracted
            // metadata; fall back to file for legacy records)
            const sizeBytes =
              photo.metadata?.filesystem?.size_bytes ??
              photo.metadata?.file?.size_bytes;
            if (sizeBytes) {
              const sizeMB = sizeBytes / (1024 * 1024);
              largestPhotoSize = Math.max(largestPhotoSize, sizeMB);
              totalPhotoSize += sizeMB;
              photosWithSize++;

              // Track per-format storage and file-size buckets
              const ext =
                (photo.metadata?.file?.extension || '')
                  .replace(/^\./, '')
                  .toUpperCase() || 'OTHER';
              const formatEntry = formatSizes[ext] ?? { count: 0, bytes: 0 };
              formatEntry.count += 1;
              formatEntry.bytes += sizeBytes;
              formatSizes[ext] = formatEntry;

              if (sizeMB < 1) sizeBucketCounts.lt1mb++;
              else if (sizeMB < 5) sizeBucketCounts.b1to5mb++;
              else if (sizeMB < 10) sizeBucketCounts.b5to10mb++;
              else sizeBucketCounts.gt10mb++;
            }

            // Analyze image quality based on resolution
            if (photo.metadata?.image?.width && photo.metadata?.image?.height) {
              const megapixels =
                (photo.metadata.image.width * photo.metadata.image.height) /
                1000000;
              if (megapixels >= 8) qualityDistribution.high++;
              else if (megapixels >= 4) qualityDistribution.medium++;
              else qualityDistribution.low++;
            }
          });
        } catch (error) {
          console.warn(
            'Failed to get photo sample for detailed analysis:',
            error
          );
        }
      }

      // Expose sample-derived storage stats for the storage tab
      setSamplePhotoCount(photosWithSize);
      setStorageByFormat(
        Object.entries(formatSizes)
          .map(([ext, entry]) => ({
            ext,
            count: entry.count,
            bytes: entry.bytes,
          }))
          .sort((a, b) => b.bytes - a.bytes)
          .slice(0, 5)
      );
      if (photosWithSize > 0) {
        const pct = (count: number) => Math.round((count / photosWithSize) * 100);
        setSizeBuckets([
          {
            label: '< 1 MB',
            count: sizeBucketCounts.lt1mb,
            pct: pct(sizeBucketCounts.lt1mb),
            barClass: 'bg-blue-500',
          },
          {
            label: '1-5 MB',
            count: sizeBucketCounts.b1to5mb,
            pct: pct(sizeBucketCounts.b1to5mb),
            barClass: 'bg-green-500',
          },
          {
            label: '5-10 MB',
            count: sizeBucketCounts.b5to10mb,
            pct: pct(sizeBucketCounts.b5to10mb),
            barClass: 'bg-yellow-500',
          },
          {
            label: '> 10 MB',
            count: sizeBucketCounts.gt10mb,
            pct: pct(sizeBucketCounts.gt10mb),
            barClass: 'bg-red-500',
          },
        ]);
      } else {
        setSizeBuckets([]);
      }

      // Calculate storage usage (approximation)
      const avgPhotoSizeMB =
        photosWithSize > 0 ? totalPhotoSize / photosWithSize : 0;
      const estimatedTotalSizeMB = totalPhotos * avgPhotoSizeMB;
      const totalSizeGB = Math.round((estimatedTotalSizeMB / 1024) * 100) / 100;

      // Create comprehensive analytics from real data
      setLibraryAnalytics({
        total_photos: totalPhotos,
        total_size_gb: totalSizeGB,
        new_photos: 0, // Would need import history endpoint
        duplicates_found: totalDuplicates,
        faces_detected: validFaceStats?.faces_detected ?? 0, // Real count from /api/faces/stats when available
        ocr_processed: ocrProcessed, // Real count from /ocr/stats (notes proxy fallback)
        albums_created: albumsCreated,
        search_queries: 0, // Would need search history endpoint
        unique_search_terms: 0, // Would need search analytics endpoint
        engagement_rate:
          totalPhotos > 0
            ? Math.round(
                ((notesStats.photos_with_notes || 0) / totalPhotos) * 100
              )
            : 0,
        processing_queue_size: 0, // Would need job monitoring endpoint
        error_rate: 0, // Would need error tracking endpoint
        storage_growth_rate: 0, // Would need historical data
        created_at: new Date().toISOString(),
      });

      // Create content insights from real analytics data
      const insights = [
        {
          id: '1',
          insight_type: 'storage',
          insight_value: `${totalSizeGB} GB`,
          photo_count: totalPhotos,
          title: 'Storage Usage',
          description: `Total library uses ${totalSizeGB} GB across ${totalPhotos} photos`,
          confidence_score: 100,
          created_at: new Date().toISOString(),
        },
        {
          id: '2',
          insight_type: 'duplicates',
          insight_value: `${totalDuplicates} files`,
          photo_count: totalDuplicates,
          title: 'Duplicate Files',
          description: `${totalDuplicates} duplicate files found using ${
            duplicatesStats.total_duplicate_groups || 0
          } groups`,
          confidence_score: 95,
          created_at: new Date().toISOString(),
        },
        {
          id: '3',
          insight_type: 'location_coverage',
          insight_value: `${photosWithLocations} photos`,
          photo_count: photosWithLocations,
          title: 'Location Coverage',
          description: `${photosWithLocations} photos have GPS data, ${photosWithoutLocations} need location tagging`,
          confidence_score: 90,
          created_at: new Date().toISOString(),
        },
        {
          id: '4',
          insight_type: 'tag_usage',
          insight_value: `${totalTags} tags`,
          photo_count: notesStats.photos_with_notes || 0,
          title: 'Tag Organization',
          description: `${totalTags} tags created, ${
            notesStats.photos_with_notes || 0
          } photos have notes`,
          confidence_score: 85,
          created_at: new Date().toISOString(),
        },
      ];
      setContentInsights(insights);

      // Create search analytics (would need real search history)
      setSearchAnalytics([]);

      // Create user behavior (would need real usage analytics)
      setUserBehavior([]);

      // Create performance metrics from the real face-pipeline metric history
      setPerformanceMetrics(
        (perfMetricsResult?.metrics ?? []).slice(0, 5).map((m) => {
          const durationMs = Math.round((m.duration || 0) * 1000);
          return {
            metric_name: m.operation || 'operation',
            metric_value: durationMs,
            metric_unit: 'ms',
            operation_type: 'face_pipeline',
            processing_time_ms: durationMs,
            created_at:
              typeof m.timestamp === 'number'
                ? new Date(m.timestamp).toISOString()
                : String(m.timestamp || new Date().toISOString()),
          };
        })
      );
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load analytics data on mount
  useEffect(() => {
    void loadAnalytics();

    if (autoRefresh) {
      const interval = setInterval(loadAnalytics, 30000); // Refresh every 30 seconds
      return () => clearInterval(interval);
    }
  }, [dateRange, autoRefresh, loadAnalytics]);

  const getMetricIcon = (metricName: string) => {
    if (metricName.includes('face')) return Users;
    if (metricName.includes('duplicate')) return Target;
    if (metricName.includes('ocr')) return FileText;
    if (metricName.includes('search')) return Search;
    if (metricName.includes('storage') || metricName.includes('size'))
      return HardDrive;
    if (metricName.includes('performance') || metricName.includes('speed'))
      return Zap;
    return BarChart3;
  };

  const getMetricColor = (value: number, type: string) => {
    if (type === 'latency') {
      if (value < 100) return 'text-green-500';
      if (value < 500) return 'text-yellow-500';
      return 'text-red-500';
    }
    if (type === 'accuracy') {
      if (value > 90) return 'text-green-500';
      if (value > 75) return 'text-yellow-500';
      return 'text-red-500';
    }
    return 'text-blue-500';
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const getStorageOptimizations = () => {
    if (!libraryAnalytics) return [];

    const optimizations = [];
    const duplicateSpace = libraryAnalytics.duplicates_found * 5; // Assume 5MB per duplicate
    const lowQualityPhotos = Math.floor(libraryAnalytics.total_photos * 0.1); // 10% low quality

    if (duplicateSpace > 100) {
      optimizations.push({
        type: 'duplicates',
        title: 'Remove Duplicates',
        description: `Save ${formatBytes(
          duplicateSpace * 1024 * 1024
        )} by removing ${libraryAnalytics.duplicates_found} duplicate photos`,
        impact: 'high',
        action: 'Review Duplicates',
      });
    }

    if (libraryAnalytics.total_size_gb > 100) {
      optimizations.push({
        type: 'storage',
        title: 'Compress Photos',
        description: 'Reduce storage by 20-30% with smart compression',
        impact: 'medium',
        action: 'Compress Library',
      });
    }

    if (lowQualityPhotos > 0) {
      optimizations.push({
        type: 'quality',
        title: 'Remove Low Quality',
        description: `Archive ${lowQualityPhotos} low-quality photos to free up space`,
        impact: 'low',
        action: 'Review Quality',
      });
    }

    return optimizations;
  };

  const handleExportAnalytics = () => {
    try {
      const payload = {
        exported_at: new Date().toISOString(),
        library: libraryAnalytics,
        content_insights: contentInsights,
        top_locations: topLocations,
        photo_timeline_by_year: timelineYears,
        popular_tags: popularTags,
        faces: facesStats,
        performance: {
          face_pipeline_metrics: performanceMetrics,
          face_pipeline_cache: perfCacheStats,
        },
        storage: {
          sampled_photos: samplePhotoCount,
          by_format: storageByFormat,
          size_distribution: sizeBuckets,
        },
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'photosearch-analytics.json';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export analytics:', error);
    }
  };

  return (
    <div className='p-6 space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-2xl font-bold text-white mb-2'>
            Analytics Dashboard
          </h2>
          <p className='text-gray-400'>
            Insights and analytics for your photo library
          </p>
        </div>
        <div className='flex items-center gap-3'>
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className='px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500'
          >
            <option value='7d'>Last 7 days</option>
            <option value='30d'>Last 30 days</option>
            <option value='90d'>Last 90 days</option>
            <option value='1y'>Last year</option>
            <option value='all'>All time</option>
          </select>

          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            aria-pressed={autoRefresh}
            className={`px-3 py-2 rounded-lg flex items-center gap-2 transition-colors ${
              autoRefresh
                ? 'bg-green-600/20 text-green-400'
                : 'bg-white/10 text-gray-400 hover:bg-white/20'
            }`}
          >
            <RefreshCw
              className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`}
            />
            Auto-refresh
          </button>

          <button
            onClick={handleExportAnalytics}
            className='px-3 py-2 bg-white/10 text-white rounded-lg hover:bg-white/20 flex items-center gap-2'
          >
            <Download className='w-4 h-4' />
            Export
          </button>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div
          className={`${glass.card} p-4 flex items-center justify-center gap-2`}
        >
          <Loader2 className='w-4 h-4 animate-spin' />
          <span className='text-gray-300'>Loading analytics…</span>
        </div>
      )}

      {/* Tabs */}
      <div className={`flex space-x-1 p-1 ${surfaceClass} rounded-lg`} role='tablist' aria-label='Analytics sections'>
        {(
          ['overview', 'content', 'search', 'performance', 'storage'] as const
        ).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            role='tab'
            aria-selected={activeTab === tab}
            className={`flex-1 px-4 py-2 rounded-md capitalize transition ${
              activeTab === tab
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-white/10'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <AnimatePresence mode='wait'>
        {/* Overview Tab */}
        {activeTab === 'overview' && libraryAnalytics && (
          <motion.div
            key='overview'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className='space-y-6'
          >
            {/* Key Metrics */}
            <div className='grid grid-cols-2 md:grid-cols-4 gap-4 tabular-nums'>
              <div className={`${glass.card} p-4`}>
                <div className='flex items-center justify-between mb-2'>
                  <ImageIcon className='w-5 h-5 text-blue-500' />
                  <TrendingUp className='w-4 h-4 text-green-500' />
                </div>
                <p className='text-2xl font-bold text-white'>
                  {formatNumber(libraryAnalytics.total_photos)}
                </p>
                <p className='text-gray-400 text-sm'>Total Photos</p>
              </div>

              <div className={`${glass.card} p-4`}>
                <div className='flex items-center justify-between mb-2'>
                  <HardDrive className='w-5 h-5 text-green-500' />
                </div>
                <p className='text-2xl font-bold text-white'>
                  {libraryAnalytics.total_size_gb.toFixed(1)} GB
                </p>
                <p className='text-gray-400 text-sm'>Storage Used</p>
              </div>

              <div className={`${glass.card} p-4`}>
                <div className='flex items-center justify-between mb-2'>
                  <Search className='w-5 h-5 text-yellow-500' />
                  <TrendingUp className='w-4 h-4 text-green-500' />
                </div>
                <p className='text-lg text-gray-500'>No data yet</p>
                <p className='text-gray-400 text-sm'>Search Queries</p>
              </div>

              <div className={`${glass.card} p-4`}>
                <div className='flex items-center justify-between mb-2'>
                  <Users className='w-5 h-5 text-purple-500' />
                </div>
                <p className='text-2xl font-bold text-white'>
                  {facesStats ? (
                    formatNumber(facesStats.faces_detected ?? 0)
                  ) : (
                    <span className='text-lg text-gray-500'>No data yet</span>
                  )}
                </p>
                <p className='text-gray-400 text-sm'>Faces Detected</p>
              </div>
            </div>

            {/* Recent Activity */}
            <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
              <div className={`${glass.card} p-6`}>
                <h3 className='text-xl font-semibold text-white mb-4'>
                  Recent Activity
                </h3>
                <div className='space-y-3'>
                  <div className='flex items-center gap-3 p-2 bg-black/20 rounded'>
                    <div className='w-2 h-2 bg-green-500 rounded-full' />
                    <Camera className='w-4 h-4 text-gray-400' />
                    <div className='flex-1'>
                      <p className='text-white text-sm'>New photos</p>
                      <p className='text-gray-500 text-xs'>
                        No import history available yet
                      </p>
                    </div>
                  </div>

                  <div className='flex items-center gap-3 p-2 bg-black/20 rounded'>
                    <div className='w-2 h-2 bg-blue-500 rounded-full' />
                    <Target className='w-4 h-4 text-gray-400' />
                    <div className='flex-1'>
                      <p className='text-white text-sm'>
                        {libraryAnalytics.duplicates_found} duplicates found
                      </p>
                      <p className='text-gray-500 text-xs'>This week</p>
                    </div>
                  </div>

                  <div className='flex items-center gap-3 p-2 bg-black/20 rounded'>
                    <div className='w-2 h-2 bg-yellow-500 rounded-full' />
                    <FileText className='w-4 h-4 text-gray-400' />
                    <div className='flex-1'>
                      <p className='text-white text-sm'>
                        {libraryAnalytics.ocr_processed} images processed
                      </p>
                      <p className='text-gray-500 text-xs'>OCR</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className={`${glass.card} p-6`}>
                <h3 className='text-xl font-semibold text-white mb-4'>
                  Quick Stats
                </h3>
                <div className='space-y-3'>
                  <div className='flex justify-between'>
                    <span className='text-gray-400'>Albums Created</span>
                    <span className='text-white'>
                      {libraryAnalytics.albums_created}
                    </span>
                  </div>
                  <div className='flex justify-between'>
                    <span className='text-gray-400'>Unique Search Terms</span>
                    <span className='text-gray-500'>No data yet</span>
                  </div>
                  <div className='flex justify-between'>
                    <span className='text-gray-400'>Avg Photos per Album</span>
                    <span className='text-white'>
                      {libraryAnalytics.albums_created > 0
                        ? Math.round(
                            libraryAnalytics.total_photos /
                              libraryAnalytics.albums_created
                          )
                        : 0}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Content Tab */}
        {activeTab === 'content' && (
          <motion.div
            key='content'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`${glass.card} p-6`}
          >
            <h3 className='text-xl font-semibold text-white mb-4'>
              Content Insights
            </h3>

            {contentInsights.length > 0 && (
              <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6'>
                {contentInsights.slice(0, 3).map((insight) => (
                  <div
                    key={insight.id}
                    className={`p-4 ${surfaceClass} rounded-lg`}
                  >
                    <div className='flex items-center justify-between mb-2'>
                      <h4 className='text-white font-medium'>
                        {insight.title ??
                          insight.insight_type.replace('_', ' ')}
                      </h4>
                      <span className='text-xs text-gray-400'>
                        {insight.confidence_score}%
                      </span>
                    </div>
                    <p className='text-gray-300 text-sm'>
                      {insight.description ?? insight.insight_value}
                    </p>
                    <p className='text-gray-500 text-xs mt-2'>
                      {formatNumber(insight.photo_count)} photos
                    </p>
                  </div>
                ))}
              </div>
            )}

            <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6'>
              <div className='p-4 bg-black/20 rounded-lg'>
                <div className='flex items-center gap-2 mb-2'>
                  <MapPin className='w-4 h-4 text-blue-500' />
                  <h4 className='text-white font-medium'>Top Locations</h4>
                </div>
                {topLocations.length === 0 ? (
                  <p className='text-gray-500 text-sm'>No data yet</p>
                ) : (
                  <div className='space-y-1'>
                    {topLocations.slice(0, 3).map((location, index) => {
                      const label =
                        location.corrected_place_name ||
                        location.city ||
                        location.region ||
                        location.country ||
                        'Unknown place';
                      return (
                        <div
                          key={`${label}-${index}`}
                          className='flex justify-between text-sm'
                        >
                          <span className='text-gray-300'>{label}</span>
                          <span className='text-gray-400'>
                            {formatNumber(location.photo_count)} photos
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className='p-4 bg-black/20 rounded-lg'>
                <div className='flex items-center gap-2 mb-2'>
                  <Calendar className='w-4 h-4 text-green-500' />
                  <h4 className='text-white font-medium'>Photo Timeline</h4>
                </div>
                {timelineYears.length === 0 ? (
                  <p className='text-gray-500 text-sm'>No data yet</p>
                ) : (
                  <div className='space-y-1'>
                    {timelineYears.map((entry) => (
                      <div
                        key={entry.year}
                        className='flex justify-between text-sm'
                      >
                        <span className='text-gray-300'>{entry.year}</span>
                        <span className='text-gray-400'>
                          {formatNumber(entry.count)} photos
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className='p-4 bg-black/20 rounded-lg'>
                <div className='flex items-center gap-2 mb-2'>
                  <Tag className='w-4 h-4 text-purple-500' />
                  <h4 className='text-white font-medium'>Popular Tags</h4>
                </div>
                {popularTags.length === 0 ? (
                  <p className='text-gray-500 text-sm'>No data yet</p>
                ) : (
                  <div className='flex flex-wrap gap-2'>
                    {popularTags.map((tag) => (
                      <span
                        key={tag.name}
                        className='px-2 py-1 bg-blue-600/20 text-blue-400 text-xs rounded'
                      >
                        {tag.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className='p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg'>
              <div className='flex items-start gap-3'>
                <AlertCircle className='w-5 h-5 text-yellow-500 mt-0.5' />
                <div>
                  <h4 className='text-yellow-400 font-medium mb-1'>
                    Content Analysis
                  </h4>
                  <p className='text-gray-300 text-sm'>
                    Your library contains diverse content with strong
                    representation of urban landscapes and family events.
                    Consider creating specialized albums for better
                    organization.
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Search Tab */}
        {activeTab === 'search' && (
          <motion.div
            key='search'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`${glass.card} p-6`}
          >
            <h3 className='text-xl font-semibold text-white mb-4'>
              Search Analytics
            </h3>

            <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
              <div>
                <h4 className='text-white font-medium mb-3'>
                  Top Search Queries
                </h4>
                {searchAnalytics.length === 0 ? (
                  <p className='text-gray-400 text-sm'>
                    Search history is not available yet (hook up the server-side
                    search events to populate this).
                  </p>
                ) : (
                  <div className='space-y-2'>
                    {searchAnalytics.slice(0, 5).map((row, index) => (
                      <div
                        key={`${row.query_text}-${row.created_at}-${index}`}
                        className={`flex items-center justify-between p-2 ${surfaceClass} rounded`}
                      >
                        <span className='text-gray-300'>
                          {index + 1}. {row.query_text}
                        </span>
                        <span className='text-gray-400 text-sm'>
                          {formatNumber(row.results_count)} results
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <h4 className='text-white font-medium mb-3'>
                  Search Performance
                </h4>
                <p className='text-gray-500 text-sm'>No data yet</p>
              </div>
            </div>

            <div className='mt-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg'>
              <div className='flex items-start gap-3'>
                <Activity className='w-5 h-5 text-blue-500 mt-0.5' />
                <div>
                  <h4 className='text-blue-400 font-medium mb-1'>
                    Search Behavior Insights
                  </h4>
                  <p className='text-gray-300 text-sm'>
                    Users primarily search for location-based content and
                    events. Consider improving metadata tagging to enhance
                    search relevance for these categories.
                  </p>
                  <p className='text-gray-500 text-xs mt-2'>
                    {userBehavior.length === 0
                      ? 'User behavior analytics not configured yet.'
                      : `Tracked actions: ${formatNumber(userBehavior.length)}`}
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Performance Tab */}
        {activeTab === 'performance' && (
          <motion.div
            key='performance'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`${glass.card} p-6`}
          >
            <h3 className='text-xl font-semibold text-white mb-4'>
              Performance Metrics
            </h3>

            <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6 tabular-nums'>
              <div className='p-4 bg-black/20 rounded-lg'>
                <div className='flex items-center justify-between mb-2'>
                  <Zap className='w-4 h-4 text-yellow-500' />
                </div>
                <p className='text-lg text-gray-500'>No data yet</p>
                <p className='text-gray-400 text-sm'>Avg. Search Time</p>
              </div>

              <div className='p-4 bg-black/20 rounded-lg'>
                <div className='flex items-center justify-between mb-2'>
                  <Database className='w-4 h-4 text-blue-500' />
                  {perfCacheStats && (
                    <span
                      className={`text-sm ${
                        perfCacheStats.hit_rate >= 0.7
                          ? 'text-green-400'
                          : perfCacheStats.hit_rate >= 0.3
                          ? 'text-yellow-400'
                          : 'text-red-400'
                      }`}
                    >
                      {perfCacheStats.hit_rate >= 0.7
                        ? 'Good'
                        : perfCacheStats.hit_rate >= 0.3
                        ? 'Fair'
                        : 'Low'}
                    </span>
                  )}
                </div>
                <p className='text-2xl font-bold text-white'>
                  {perfCacheStats ? (
                    `${Math.round(perfCacheStats.hit_rate * 100)}%`
                  ) : (
                    <span className='text-lg text-gray-500'>No data yet</span>
                  )}
                </p>
                <p className='text-gray-400 text-sm'>Cache Hit Rate</p>
              </div>

              <div className='p-4 bg-black/20 rounded-lg'>
                <div className='flex items-center justify-between mb-2'>
                  <Server className='w-4 h-4 text-green-500' />
                </div>
                <p className='text-lg text-gray-500'>No data yet</p>
                <p className='text-gray-400 text-sm'>API Response</p>
              </div>
            </div>

            <div className='space-y-3'>
              {performanceMetrics.slice(0, 5).map((metric, index) => {
                const MetricIcon = getMetricIcon(metric.metric_name);
                const color = getMetricColor(metric.metric_value, 'latency');

                return (
                  <div
                    key={index}
                    className='flex items-center justify-between p-3 bg-black/20 rounded-lg'
                  >
                    <div className='flex items-center gap-3'>
                      <MetricIcon className='w-4 h-4 text-gray-400' />
                      <div>
                        <p className='text-white text-sm capitalize'>
                          {metric.metric_name.replace('_', ' ')}
                        </p>
                        <p className='text-gray-500 text-xs'>
                          {metric.operation_type}
                        </p>
                      </div>
                    </div>
                    <div className='text-right'>
                      <p className={`font-mono text-sm ${color}`}>
                        {metric.metric_value}
                        {metric.metric_unit}
                      </p>
                      <p className='text-gray-500 text-xs'>
                        {formatDuration(metric.processing_time_ms)}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* Storage Tab */}
        {activeTab === 'storage' && (
          <motion.div
            key='storage'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className='space-y-6'
          >
            <div className={`${glass.card} p-6`}>
              <h3 className='text-xl font-semibold text-white mb-4'>
                Storage Analysis
              </h3>

              <div className='grid grid-cols-1 md:grid-cols-2 gap-6 mb-6'>
                <div>
                  <h4 className='text-white font-medium mb-3'>
                    Storage Breakdown
                  </h4>
                  {storageByFormat.length === 0 ? (
                    <p className='text-gray-500 text-sm'>No data yet</p>
                  ) : (
                    <div className='space-y-2'>
                      {storageByFormat.map((format) => (
                        <div
                          key={format.ext}
                          className='flex items-center justify-between'
                        >
                          <span className='text-gray-300'>
                            {format.ext} ({formatNumber(format.count)} photos)
                          </span>
                          <span className='text-white'>
                            {formatBytes(format.bytes)}
                          </span>
                        </div>
                      ))}
                      <p className='text-gray-500 text-xs'>
                        Based on a sample of {formatNumber(samplePhotoCount)}{' '}
                        photos
                      </p>
                    </div>
                  )}
                </div>

                <div>
                  <h4 className='text-white font-medium mb-3'>
                    File Size Distribution
                  </h4>
                  {sizeBuckets.length === 0 ? (
                    <p className='text-gray-500 text-sm'>No data yet</p>
                  ) : (
                    <div className='space-y-2'>
                      {sizeBuckets.map((bucket) => (
                        <div
                          key={bucket.label}
                          className='flex items-center justify-between'
                        >
                          <span className='text-gray-300'>{bucket.label}</span>
                          <div className='flex items-center gap-2'>
                            <div className='w-32 h-2 bg-black/30 rounded-full overflow-hidden'>
                              <div
                                className={`h-full ${bucket.barClass}`}
                                style={{ width: `${bucket.pct}%` }}
                              />
                            </div>
                            <span className='text-gray-400 text-xs w-8 text-right'>
                              {bucket.pct}%
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className={`${glass.card} p-6`}>
              <h3 className='text-xl font-semibold text-white mb-4'>
                Storage Optimization Suggestions
              </h3>

              <div className='space-y-3'>
                {getStorageOptimizations().map((optimization, index) => (
                  <div
                    key={index}
                    className='p-4 bg-black/20 rounded-lg border border-white/10'
                  >
                    <div className='flex items-start justify-between mb-2'>
                      <div className='flex items-center gap-2'>
                        <Target className='w-4 h-4 text-yellow-500' />
                        <h4 className='text-white font-medium'>
                          {optimization.title}
                        </h4>
                      </div>
                      <span
                        className={`px-2 py-1 text-xs rounded ${
                          optimization.impact === 'high'
                            ? 'bg-red-500/20 text-red-400'
                            : optimization.impact === 'medium'
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : 'bg-green-500/20 text-green-400'
                        }`}
                      >
                        {optimization.impact} impact
                      </span>
                    </div>
                    <p className='text-gray-400 text-sm mb-3'>
                      {optimization.description}
                    </p>
                    {optimization.type === 'duplicates' ? (
                      <button
                        onClick={() => navigate('/duplicates')}
                        className='px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700'
                      >
                        {optimization.action}
                      </button>
                    ) : (
                      <button
                        disabled
                        title='Not available yet'
                        className='px-3 py-1 bg-white/10 text-gray-500 text-sm rounded cursor-not-allowed'
                      >
                        {optimization.action}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default memo(AnalyticsDashboard);
