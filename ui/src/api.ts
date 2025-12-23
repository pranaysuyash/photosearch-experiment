import axios, { type AxiosRequestConfig } from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const SERVER_CONFIG_TTL_MS = 60_000;
let serverConfigCache: {
  value: any | null;
  timestamp: number;
  promise: Promise<any> | null;
} = { value: null, timestamp: 0, promise: null };

// Create axios instance with proper configuration
const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000, // 30 second timeout
  headers: {
    'Content-Type': 'application/json',
  },
  // Enable connection reuse (browser handles this automatically)
  maxRedirects: 5,
});

// Add request interceptor for consistent configuration
apiClient.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export interface PhotoMetadata {
  file?: {
    name?: string;
    extension?: string;
    mime_type?: string;
  };
  image?: {
    width?: number;
    height?: number;
    format?: string;
    mode?: string;
    dpi?: number[];
    bits_per_pixel?: number;
    animation?: boolean;
    frames?: number;
  };
  video?: {
    format?: Record<string, unknown>;
    streams?: Array<Record<string, unknown>>;
  };
  audio?: Record<string, unknown>;
  pdf?: Record<string, unknown>;
  svg?: Record<string, unknown>;
  exif?: Record<string, unknown>;
  gps?: { latitude?: number; longitude?: number; altitude?: number };
  filesystem?: Record<string, unknown>;
  thumbnail?: Record<string, unknown>;
  hashes?: Record<string, string>;
  calculated?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface MatchReason {
  category: string;
  matched: string;
  confidence: number;
  badge: string;
  type: 'metadata' | 'semantic' | 'hybrid';
}

export interface MatchExplanation {
  type: 'metadata' | 'semantic' | 'hybrid';
  reasons: MatchReason[];
  overallConfidence: number;
}

export interface Photo {
  path: string;
  filename: string;
  score: number;
  metadata: PhotoMetadata;
  matchExplanation?: MatchExplanation;
}

export interface PhotoEdit {
  brightness: number;
  contrast: number;
  saturation: number;
  rotation: number;
  flipH: boolean;
  flipV: boolean;
  crop?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface ExportOptions {
  format?: string;
  include_metadata?: boolean;
  include_thumbnails?: boolean;
  max_resolution?: number;
  rename_pattern?: string;
  password_protect?: boolean;
  password?: string;
}

export interface IntentSearchParams {
  query: string;
  intent_context?: Record<string, any>;
  filters?: Record<string, any>;
  limit?: number;
  offset?: number;
}

export interface SearchResult {
  [key: string]: any;
}

export interface SmartCollectionRule {
  [key: string]: any;
}

export interface SmartCollectionUpdate {
  name?: string;
  description?: string;
  rule_definition?: SmartCollectionRule;
  auto_update?: boolean;
  privacy_level?: string;
  is_favorite?: boolean;
}

export interface AIInsightData {
  [key: string]: any;
}

export interface StoryUpdate {
  title?: string;
  description?: string;
  is_published?: boolean;
  metadata?: Record<string, any>;
}

export interface StoryPhotoData {
  photo_path: string;
  date?: string;
  location?: string;
  caption?: string;
}

export interface TimelineEntryUpdate {
  date?: string;
  location?: string;
  caption?: string;
  narrative_order?: number;
}

export interface BulkActionOperationData {
  [key: string]: any;
}

export interface TagExpression {
  tag: string;
  operator?: string; // 'has', 'not_has', 'maybe_has'
}

export interface TagFilterUpdate {
  name?: string;
  tag_expressions?: TagExpression[];
  combination_operator?: string;
}

export interface EditInstructions {
  [key: string]: any;
}

export interface TimelineData {
  date: string; // YYYY-MM
  count: number;
}

export interface Job {
  id: string;
  type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message?: string;
  result?: unknown;
}

export interface SavedSearch {
  id: string;
  query: string;
  mode: string;
  intent?: string;
  created_at: string;
  results_count: number;
  is_favorite: boolean;
  notes?: string;
}

export interface PricingTier {
  name: string;
  image_limit: number;
  price_monthly: number;
  price_yearly?: number;
  features: string[];
  stripe_price_id?: string;
  is_popular: boolean;
}

export interface UsageStats {
  current_tier: string;
  image_count: number;
  image_limit: number;
  usage_percentage: number;
  billing_cycle_start: string;
  billing_cycle_end: string | null;
  days_remaining: number;
}

export interface Source {
  id: string;
  type: 'local_folder' | 's3' | 'google_drive';
  name: string;
  status: 'pending' | 'connected' | 'auth_required' | 'error';
  created_at: string;
  updated_at: string;
  last_sync_at?: string | null;
  last_error?: string | null;
  config: Record<string, unknown>;
}

// People Search Interface
export interface PersonSearchResult {
  people: Array<{
    cluster_id: string;
    label: string;
    face_count: number;
    photo_count: number;
    thumbnail?: string;
  }>;
  total: number;
  limit: number;
  offset: number;
  success: boolean;
}

// Face Detection Interfaces
export interface FaceDetection {
  detection_id: string;
  photo_path: string;
  bounding_box: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  has_embedding: boolean;
  quality_score: number;
}

export interface FaceDetectionResult {
  photo_path: string;
  faces: FaceDetection[];
  face_count: number;
  success: boolean;
  error?: string;
}

export interface FaceThumbnailResult {
  detection_id: string;
  thumbnail: string; // base64 encoded image
  success: boolean;
  error?: string;
}

export interface BatchDetectionResult {
  processed_photos: number;
  total_faces_detected: number;
  results: Array<{
    photo_path: string;
    face_count: number;
    detection_ids: string[];
  }>;
  success: boolean;
}

export interface FaceCluster {
  cluster_id: string;
  label: string;
  face_count: number;
  photo_count: number;
  detection_ids: string[];
}

export interface ClusteringResult {
  clusters_created: number;
  total_faces_clustered: number;
  clusters: FaceCluster[];
  success: boolean;
}

export interface SimilarFace {
  detection_id: string;
  photo_path: string;
  similarity: number;
  person_id?: string;
  person_label?: string;
}

export interface SimilarFacesResult {
  detection_id: string;
  similar_faces: SimilarFace[];
  count: number;
  success: boolean;
}

export interface ClusterQuality {
  cluster_id: string;
  label: string;
  face_count: number;
  avg_confidence: number;
  avg_quality_score: number;
  coherence_score: number;
  quality_rating: 'Excellent' | 'Good' | 'Fair' | 'Poor' | 'Low';
  created_at: string;
  updated_at: string;
}

export interface ClusterQualityResult {
  cluster_id: string;
  quality_analysis: ClusterQuality;
  success: boolean;
}

export interface MergeClustersResult {
  source_cluster_id: string;
  target_cluster_id: string;
  faces_moved: number;
  success: boolean;
}

export interface Album {
  id: string;
  name: string;
  description?: string;
  cover_photo_path?: string;
  created_at: string;
  updated_at: string;
  is_smart: boolean;
  smart_rules?: Record<string, unknown>;
  photo_count: number;
}

export interface TagSummary {
  name: string;
  photo_count: number;
  created_at: string;
  updated_at: string;
}

export interface TrashItem {
  id: string;
  original_path: string;
  trashed_path: string;
  status: string;
  source_id?: string | null;
  remote_id?: string | null;
  created_at: string;
}

export const api = {
  /**
   * Raw axios client (rarely needed).
   *
   * Most UI code expects `api.get/post/...` to resolve to the JSON payload directly
   * (not an AxiosResponse). Keep this escape hatch for the few cases that need
   * headers/status/etc.
   */
  http: apiClient,

  // Low-level helpers that resolve to `response.data` (payload-first ergonomics).
  get: async <T = any>(url: string, config?: AxiosRequestConfig) => {
    const res = await apiClient.get<T>(url, config);
    return res.data;
  },
  post: async <T = any, D = any>(
    url: string,
    data?: D,
    config?: AxiosRequestConfig
  ) => {
    const res = await apiClient.post<T>(url, data, config);
    return res.data;
  },
  put: async <T = any, D = any>(
    url: string,
    data?: D,
    config?: AxiosRequestConfig
  ) => {
    const res = await apiClient.put<T>(url, data, config);
    return res.data;
  },
  delete: async <T = any>(url: string, config?: AxiosRequestConfig) => {
    const res = await apiClient.delete<T>(url, config);
    return res.data;
  },

  scan: async (path: string, background: boolean = true) => {
    const res = await apiClient.post('/scan', { path, background });
    return res.data; // Returns { job_id, status } if background=true
  },

  // Sources (Local + Cloud)
  listSources: async () => {
    const res = await apiClient.get('/sources');
    return res.data as { sources: Source[] };
  },

  addLocalFolderSource: async (
    path: string,
    name?: string,
    force: boolean = false
  ) => {
    const res = await apiClient.post('/sources/local-folder', {
      path,
      name,
      force,
    });
    return res.data as { source: Source; job_id: string };
  },

  addS3Source: async (payload: {
    name: string;
    endpoint_url: string;
    region: string;
    bucket: string;
    prefix?: string;
    access_key_id: string;
    secret_access_key: string;
  }) => {
    const res = await apiClient.post('/sources/s3', payload);
    return res.data as { source: Source; job_id?: string };
  },

  addGoogleDriveSource: async (payload: {
    name: string;
    client_id: string;
    client_secret: string;
  }) => {
    const res = await apiClient.post('/sources/google-drive', payload);
    return res.data as { source: Source; auth_url: string };
  },

  deleteSource: async (sourceId: string) => {
    const res = await apiClient.delete(`/sources/${sourceId}`);
    return res.data as { ok: boolean };
  },

  rescanSource: async (sourceId: string, force: boolean = false) => {
    const res = await apiClient.post(`/sources/${sourceId}/rescan`, { force });
    return res.data as { ok: boolean; job_id: string };
  },

  syncSource: async (sourceId: string) => {
    const res = await apiClient.post(`/sources/${sourceId}/sync`);
    return res.data as { ok: boolean; job_id: string };
  },

  getJobStatus: async (jobId: string) => {
    const res = await apiClient.get(`/jobs/${jobId}`);
    return res.data as Job;
  },

  listJobs: async (params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const res = await apiClient.get('/jobs', { params });
    return res.data as { jobs: Job[]; total?: number };
  },

  cancelJob: async (jobId: string) => {
    const res = await apiClient.post(`/jobs/${jobId}/cancel`);
    return res.data as { ok: boolean };
  },

  search: async (
    query: string,
    mode: string = 'metadata',
    limit: number = 50,
    offset: number = 0,
    sortBy: string = 'date_desc',
    typeFilter: string = 'all',
    favoritesFilter: string = 'all',
    tag?: string | null,
    dateFrom?: string | null,
    dateTo?: string | null,
    sourceFilter: 'all' | 'local' | 'cloud' | 'hybrid' = 'all',
    signal?: AbortSignal,
    person?: string | null
  ) => {
    // Parse "person:Name" from the query if person is not explicitly provided
    let parsedPerson = person || null;
    let cleanQuery = query;

    if (!parsedPerson && query) {
      // Match patterns like "person:Name" or "person:Full Name" (quoted) or "person:Name with spaces"
      const personMatch = query.match(/\bperson:(?:"([^"]+)"|'([^']+)'|(\S+))/i);
      if (personMatch) {
        parsedPerson = personMatch[1] || personMatch[2] || personMatch[3];
        // Remove the person: prefix from the query
        cleanQuery = query.replace(/\bperson:(?:"[^"]+"|'[^']+'|\S+)/i, '').trim();
      }
    }

    const res = await apiClient.get('/search', {
      params: {
        query: cleanQuery,
        mode,
        limit,
        offset,
        sort_by: sortBy,
        type_filter: typeFilter,
        source_filter: sourceFilter,
        favorites_filter: favoritesFilter,
        ...(tag ? { tag } : {}),
        ...(dateFrom ? { date_from: dateFrom } : {}),
        ...(dateTo ? { date_to: dateTo } : {}),
        ...(parsedPerson ? { person: parsedPerson } : {}),
      },
      signal,
    });
    return res.data;
  },

  getTimeline: async () => {
    const res = await apiClient.get('/timeline');
    return res.data.timeline as TimelineData[];
  },

  getStats: async () => {
    const res = await apiClient.get('/stats');
    return res.data as {
      active_files?: number;
      deleted_files?: number;
      total_versions?: number;
    };
  },

  listSavedSearches: async (filter?: string) => {
    const res = await apiClient.get('/searches', {
      params: filter && filter !== 'all' ? { filter } : undefined,
    });
    return res.data as { searches: SavedSearch[] };
  },

  executeSavedSearch: async (searchId: string) => {
    const res = await apiClient.post(`/searches/${searchId}/execute`);
    return res.data as { results: Photo[]; search: SavedSearch };
  },

  updateSavedSearch: async (searchId: string, patch: Partial<SavedSearch>) => {
    const res = await apiClient.put(`/searches/${searchId}`, patch);
    return res.data as { ok: boolean };
  },

  deleteSavedSearch: async (searchId: string) => {
    const res = await apiClient.delete(`/searches/${searchId}`);
    return res.data as { ok: boolean };
  },

  getImageUrl: (path: string, size?: number) => {
    const encodedPath = encodeURIComponent(path);
    return `${API_BASE}/image/thumbnail?path=${encodedPath}${
      size ? `&size=${size}` : ''
    }`;
  },

  getServerConfig: async () => {
    const now = Date.now();
    if (
      serverConfigCache.value &&
      now - serverConfigCache.timestamp < SERVER_CONFIG_TTL_MS
    ) {
      return serverConfigCache.value;
    }
    if (serverConfigCache.promise) {
      return serverConfigCache.promise;
    }
    serverConfigCache.promise = apiClient
      .get('/server/config')
      .then((res) => {
        serverConfigCache = {
          value: res.data,
          timestamp: Date.now(),
          promise: null,
        };
        return res.data;
      })
      .catch((err) => {
        serverConfigCache.promise = null;
        throw err;
      });
    return serverConfigCache.promise;
  },

  // Obtain a signed thumbnail URL from the server (server must support /image/token and require auth).
  // Optimizations:
  // - Cache server config to avoid redundant /server/config calls.
  // - Short-circuit for local file paths (no token needed).
  // - Cache recently issued tokens per path until expiry to reduce duplicate token issuance.
  getSignedImageUrl: async (path: string, size?: number, ttl?: number) => {
    // Simple local path detection (same heuristic as ContextAnalyzer.isLocalFile)
    const isLocal = (() => {
      const localPatterns = [
        /^[A-Za-z]:\\/,
        /^\/[^\/]/,
        /^~\//,
        /^\.\//,
        /^file:\/\//,
      ];
      return localPatterns.some((r) => r.test(path));
    })();

    // If local, no need to request a token
    if (isLocal) {
      return `${API_BASE}/image/thumbnail?path=${encodeURIComponent(path)}${
        size ? `&size=${size}` : ''
      }`;
    }

    // Cached flags and token map (module-level singletons)
    // Implement lazy initialization
    if (!(api as any)._signedUrlEnabledCache)
      (api as any)._signedUrlEnabledCache = null;
    if (!(api as any)._tokenCache)
      (api as any)._tokenCache = new Map<
        string,
        { token: string; expiresAt: number }
      >();

    // Resolve whether server supports signed URLs (cache for 30s)
    if ((api as any)._signedUrlEnabledCache === null) {
      try {
        const cfg = await api.getServerConfig();
        (api as any)._signedUrlEnabledCache = !!cfg?.signed_url_enabled;
        (api as any)._signedUrlEnabledCacheExpires = Date.now() + 30 * 1000;
      } catch {
        (api as any)._signedUrlEnabledCache = false;
        (api as any)._signedUrlEnabledCacheExpires = Date.now() + 30 * 1000;
      }
    } else if (Date.now() > (api as any)._signedUrlEnabledCacheExpires) {
      // Refresh cache asynchronously (don't block); start refresh but proceed with current value
      (async () => {
        try {
          const cfg = await api.getServerConfig();
          (api as any)._signedUrlEnabledCache = !!cfg?.signed_url_enabled;
          (api as any)._signedUrlEnabledCacheExpires = Date.now() + 30 * 1000;
        } catch {
          (api as any)._signedUrlEnabledCache =
            (api as any)._signedUrlEnabledCache || false;
          (api as any)._signedUrlEnabledCacheExpires = Date.now() + 30 * 1000;
        }
      })();
    }

    const signedEnabled = !!(api as any)._signedUrlEnabledCache;
    if (!signedEnabled) {
      // Signed URLs are disabled, fall back to direct path
      return `${API_BASE}/image/thumbnail?path=${encodeURIComponent(path)}${
        size ? `&size=${size}` : ''
      }`;
    }

    // If we already have a cached token that is still valid, return it
    const existing = (api as any)._tokenCache.get(path);
    if (existing && existing.expiresAt > Date.now()) {
      return `${API_BASE}/image/thumbnail?token=${encodeURIComponent(
        existing.token
      )}${size ? `&size=${size}` : ''}`;
    }

    // Otherwise, request a new token from the server
    try {
      const res = await apiClient.post<{ token?: string; expires_in?: number }>(
        '/image/token',
        { path, ttl, scope: 'thumbnail' }
      );
      const token = res?.data?.token ?? null;
      const expiresIn = res?.data?.expires_in ?? ttl ?? undefined;

      if (token) {
        const expireMs = expiresIn ? expiresIn * 1000 : 60 * 60 * 1000;
        (api as any)._tokenCache.set(path, {
          token,
          expiresAt: Date.now() + expireMs,
        });
        return `${API_BASE}/image/thumbnail?token=${encodeURIComponent(token)}${
          size ? `&size=${size}` : ''
        }`;
      }

      // Fallback
      return `${API_BASE}/image/thumbnail?path=${encodeURIComponent(path)}${
        size ? `&size=${size}` : ''
      }`;
    } catch (e) {
      // On error, return path-based URL
      return `${API_BASE}/image/thumbnail?path=${encodeURIComponent(path)}${
        size ? `&size=${size}` : ''
      }`;
    }
  },

  // Serve the original file (no transcoding); set download=true to force attachment
  getFileUrl: (path: string, opts?: { download?: boolean }) => {
    const encodedPath = encodeURIComponent(path);
    const download = opts?.download ? '&download=true' : '';
    return `${API_BASE}/file?path=${encodedPath}${download}`;
  },

  // Set auth token (Bearer) for future requests
  setAuthToken: (token?: string | null) => {
    if (token)
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    else delete apiClient.defaults.headers.common['Authorization'];
  },

  // Set simple issuer key header for token issuance
  setIssuerKey: (key?: string | null) => {
    if (key) apiClient.defaults.headers.common['x-api-key'] = key;
    else delete apiClient.defaults.headers.common['x-api-key'];
  },

  // Check if file is a video
  isVideo: (path: string) => {
    const videoExts = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'];
    return videoExts.some((ext) => path.toLowerCase().endsWith(ext));
  },

  // Export selected photos as ZIP (see comprehensive exportPhotos below)

  // Trash (Recently Deleted)
  trashMove: async (filePaths: string[]) => {
    const res = await apiClient.post('/trash/move', { file_paths: filePaths });
    return res.data as { moved: Array<{ id: string }>; errors: string[] };
  },

  removeFromLibrary: async (filePaths: string[]) => {
    const res = await apiClient.post('/library/remove', {
      file_paths: filePaths,
    });
    return res.data as { removed: string[]; errors: string[] };
  },

  listTrash: async (limit: number = 200, offset: number = 0) => {
    const res = await apiClient.get('/trash', { params: { limit, offset } });
    return res.data as { items: TrashItem[] };
  },

  trashRestore: async (itemIds: string[]) => {
    const res = await apiClient.post('/trash/restore', { item_ids: itemIds });
    return res.data as { restored: string[]; errors: string[] };
  },

  trashEmpty: async (itemIds?: string[]) => {
    const res = await apiClient.post('/trash/empty', { item_ids: itemIds });
    return res.data as { deleted: string[]; errors: string[] };
  },

  // Tags
  listTags: async (limit: number = 200, offset: number = 0) => {
    const res = await apiClient.get('/tags', { params: { limit, offset } });
    return res.data as { tags: TagSummary[] };
  },

  createTag: async (name: string) => {
    const res = await apiClient.post('/tags', { name });
    return res.data as { ok: boolean };
  },

  deleteTag: async (name: string) => {
    const res = await apiClient.delete(`/tags/${encodeURIComponent(name)}`);
    return res.data as { ok: boolean };
  },

  addPhotosToTag: async (tagName: string, photoPaths: string[]) => {
    const res = await apiClient.post(
      `/tags/${encodeURIComponent(tagName)}/photos`,
      {
        photo_paths: photoPaths,
      }
    );
    return res.data as { added: number; total: number };
  },

  removePhotosFromTag: async (tagName: string, photoPaths: string[]) => {
    const res = await apiClient.delete(
      `/tags/${encodeURIComponent(tagName)}/photos`,
      {
        data: { photo_paths: photoPaths },
      }
    );
    return res.data as { removed: number };
  },

  getPhotoTags: async (photoPath: string) => {
    const encoded = encodeURIComponent(photoPath);
    const res = await apiClient.get(`/photos/${encoded}/tags`);
    return res.data as { tags: string[] };
  },

  // Get video URL for direct serving
  getVideoUrl: (path: string) => {
    const encodedPath = encodeURIComponent(path);
    return `${API_BASE}/video?path=${encodedPath}`;
  },

  // Pricing endpoints
  getPricingTiers: async () => {
    const res = await apiClient.get('/pricing');
    return res.data as PricingTier[];
  },

  getPricingTier: async (tierName: string) => {
    const res = await apiClient.get(`/pricing/${tierName}`);
    return res.data as PricingTier;
  },

  recommendPricingTier: async (imageCount: number) => {
    const res = await apiClient.get(
      `/pricing/recommend?image_count=${imageCount}`
    );
    return res.data as PricingTier;
  },

  getUsageStats: async (userId: string) => {
    const res = await apiClient.get(`/usage/${userId}`);
    return res.data as UsageStats;
  },

  checkUsageLimit: async (userId: string, additionalImages: number = 0) => {
    const res = await apiClient.get(
      `/usage/check/${userId}?additional_images=${additionalImages}`
    );
    return res.data;
  },

  upgradeUserTier: async (userId: string, newTier: string) => {
    const res = await apiClient.post(`/usage/upgrade/${userId}`, {
      new_tier: newTier,
    });
    return res.data;
  },

  // Favorites management
  toggleFavorite: async (filePath: string, notes: string = '') => {
    const res = await apiClient.post('/favorites/toggle', {
      file_path: filePath,
      notes,
    });
    // Invalidate cached favorite for this file
    try {
      if ((api as any)._favoriteCache)
        (api as any)._favoriteCache.delete(filePath);
    } catch {}
    return res.data;
  },

  // Duplicates
  getDuplicates: async (
    opts: { hashType?: string; limit?: number; offset?: number } = {}
  ) => {
    const res = await apiClient.get('/api/duplicates', {
      params: {
        hash_type: opts.hashType,
        limit: opts.limit,
        offset: opts.offset,
      },
    });
    return res.data;
  },
  getDuplicateStats: async () => {
    const res = await apiClient.get('/api/duplicates/stats');
    return res.data;
  },
  scanDuplicates: async (
    type: 'exact' | 'perceptual' = 'exact',
    limit: number = 1000
  ) => {
    const res = await apiClient.post('/api/duplicates/scan', null, {
      params: { type, limit },
    });
    return res.data;
  },
  resolveDuplicateGroup: async (
    groupId: string,
    resolution: 'keep_all' | 'keep_selected' | 'delete_all',
    keepFiles?: string[]
  ) => {
    const res = await apiClient.post(`/api/duplicates/${groupId}/resolve`, {
      resolution,
      keep_files: keepFiles,
    });
    return res.data;
  },
  cleanupDuplicates: async () => {
    const res = await apiClient.post('/api/duplicates/cleanup');
    return res.data;
  },
  deleteDuplicateGroup: async (groupId: string) => {
    const res = await apiClient.delete(`/api/duplicates/${groupId}`);
    return res.data;
  },

  // Additional duplicate methods for components
  getDuplicateGroups: async () => {
    const res = await apiClient.get('/api/duplicates/groups');
    return res.data;
  },

  scanDuplicatesWithPath: async (
    directoryPath: string,
    similarityThreshold: number = 5.0
  ) => {
    const res = await apiClient.post('/api/duplicates/scan', {
      directory_path: directoryPath,
      similarity_threshold: similarityThreshold,
    });
    return res.data;
  },

  // Photo edits (non-destructive settings)
  savePhotoEdit: async (photoPath: string, editData: PhotoEdit) => {
    const res = await apiClient.post(
      `/api/photos/${encodeURIComponent(photoPath)}/edit`,
      { edit_data: editData }
    );
    return res.data;
  },
  getPhotoEdit: async (photoPath: string) => {
    const res = await apiClient.get(
      `/api/photos/${encodeURIComponent(photoPath)}/edit`
    );
    return res.data;
  },

  // Face clusters per image
  getFacesForImage: async (photoPath: string) => {
    const res = await apiClient.get(
      `/faces/image/${encodeURIComponent(photoPath)}`
    );
    return res.data;
  },

  getFavorites: async (limit: number = 1000, offset: number = 0) => {
    const res = await apiClient.get('/favorites', {
      params: { limit, offset },
    });
    return res.data;
  },

  checkFavorite: async (filePath: string) => {
    // Simple in-memory cache to prevent duplicate per-photo requests within short window
    if (!(api as any)._favoriteCache)
      (api as any)._favoriteCache = new Map<
        string,
        { is_favorited: boolean; expiresAt: number }
      >();

    const cached = (api as any)._favoriteCache.get(filePath);
    if (cached && cached.expiresAt > Date.now()) {
      return { is_favorited: cached.is_favorited };
    }

    const res = await apiClient.get('/favorites/check', {
      params: { file_path: filePath },
    });

    // Cache for 30s
    try {
      (api as any)._favoriteCache.set(filePath, {
        is_favorited: res.data.is_favorited,
        expiresAt: Date.now() + 30 * 1000,
      });
    } catch {}

    return res.data;
  },

  removeFavorite: async (filePath: string) => {
    const res = await apiClient.delete('/favorites', {
      data: { file_path: filePath },
    });
    return res.data;
  },

  // Bulk operations
  bulkExportPhotos: async (filePaths: string[]) => {
    const res = await apiClient.post(
      '/bulk/export',
      { file_paths: filePaths },
      { responseType: 'blob' }
    );
    return res.data;
  },

  deletePhotos: async (filePaths: string[], confirm: boolean = false) => {
    const res = await apiClient.post('/bulk/delete', {
      file_paths: filePaths,
      confirm,
    });
    return res.data;
  },

  bulkFavorite: async (filePaths: string[], action: 'add' | 'remove') => {
    const res = await apiClient.post('/bulk/favorite', {
      file_paths: filePaths,
      action,
    });
    return res.data;
  },

  bulkTag: async (filePaths: string[], tag: string) => {
    const res = await apiClient.post('/bulk/tag', {
      file_paths: filePaths,
      tag,
    });
    return res.data;
  },

  bulkArchive: async (filePaths: string[]) => {
    const res = await apiClient.post('/bulk/archive', {
      file_paths: filePaths,
    });
    return res.data;
  },

  bulkMove: async (filePaths: string[], destination: string) => {
    const res = await apiClient.post('/bulk/move', {
      file_paths: filePaths,
      destination,
    });
    return res.data;
  },

  bulkCopy: async (filePaths: string[], destination: string) => {
    const res = await apiClient.post('/bulk/copy', {
      file_paths: filePaths,
      destination,
    });
    return res.data;
  },

  // Albums management
  listAlbums: async (includeSmart: boolean = true) => {
    const res = await apiClient.get('/albums', {
      params: { include_smart: includeSmart },
    });
    return res.data as { albums: Album[] };
  },

  createAlbum: async (name: string, description?: string) => {
    const res = await apiClient.post('/albums', { name, description });
    return res.data as { album: Album };
  },

  getAlbum: async (albumId: string, includePhotos: boolean = true) => {
    const res = await apiClient.get(`/albums/${albumId}`, {
      params: { include_photos: includePhotos },
    });
    return res.data as { album: Album; photos?: Photo[] };
  },

  updateAlbum: async (
    albumId: string,
    updates: {
      name?: string;
      description?: string;
      cover_photo_path?: string;
    }
  ) => {
    const res = await apiClient.put(`/albums/${albumId}`, updates);
    return res.data as { album: Album };
  },

  deleteAlbum: async (albumId: string) => {
    const res = await apiClient.delete(`/albums/${albumId}`);
    return res.data as { ok: boolean };
  },

  addPhotosToAlbum: async (albumId: string, photoPaths: string[]) => {
    const res = await apiClient.post(`/albums/${albumId}/photos`, {
      photo_paths: photoPaths,
    });
    return res.data as { ok: boolean; added_count: number };
  },

  removePhotosFromAlbum: async (albumId: string, photoPaths: string[]) => {
    const res = await apiClient.delete(`/albums/${albumId}/photos`, {
      data: { photo_paths: photoPaths },
    });
    return res.data as { ok: boolean; removed_count: number };
  },

  refreshSmartAlbum: async (albumId: string) => {
    const res = await apiClient.post(`/albums/${albumId}/refresh`);
    return res.data as { ok: boolean; photo_count: number };
  },

  getPhotoAlbums: async (photoPath: string) => {
    const encodedPath = encodeURIComponent(photoPath);
    const res = await apiClient.get(`/photos/${encodedPath}/albums`);
    return res.data as { albums: Album[] };
  },

  // ========== Image Transformation ==========

  rotatePhoto: async (
    path: string,
    degrees: 90 | -90 | 180 | 270,
    backup: boolean = true
  ) => {
    const res = await apiClient.post('/photos/rotate', {
      path,
      degrees,
      backup,
    });
    return res.data as {
      ok: boolean;
      path: string;
      operation: string;
      backup_created: boolean;
    };
  },

  flipPhoto: async (
    path: string,
    direction: 'horizontal' | 'vertical',
    backup: boolean = true
  ) => {
    const res = await apiClient.post('/photos/flip', {
      path,
      direction,
      backup,
    });
    return res.data as {
      ok: boolean;
      path: string;
      operation: string;
      backup_created: boolean;
    };
  },

  // Health check for backend connectivity
  healthCheck: async () => {
    try {
      const res = await apiClient.get('/', { timeout: 5000 });
      return res.data.status === 'ok';
    } catch {
      return false;
    }
  },

  // API Schema and Documentation
  getApiSchema: async () => {
    const res = await apiClient.get('/api/schema');
    return res.data;
  },

  // Cache Management
  getCacheStats: async () => {
    const res = await apiClient.get('/api/cache/stats');
    return res.data;
  },

  // clearCache is defined below with more comprehensive implementation

  cleanupCache: async () => {
    const res = await apiClient.get('/api/cache/cleanup');
    return res.data;
  },

  // Logging
  testLogging: async () => {
    const res = await apiClient.get('/api/logs/test');
    return res.data;
  },

  // Image Analysis
  analyzeImage: async (path: string) => {
    const res = await apiClient.post('/ai/analyze', { path });
    return res.data;
  },

  // Prefer a neutral name for the client-side helper; keep the old name as an alias for compatibility
  getAnalysis: async (path: string) => {
    const res = await apiClient.get(`/ai/analysis/${encodeURIComponent(path)}`);
    return res.data;
  },

  getAIAnalysis: async (path: string) => {
    // Backwards-compatible alias
    return await api.getAnalysis(path);
  },

  // Photo Rating System
  getPhotoRating: async (path: string) => {
    const res = await apiClient.get(
      `/api/photos/${encodeURIComponent(path)}/rating`
    );
    return res.data.rating;
  },

  setPhotoRating: async (path: string, rating: number) => {
    const res = await apiClient.post(
      `/api/photos/${encodeURIComponent(path)}/rating`,
      { rating }
    );
    return res.data;
  },

  removePhotoRating: async (path: string) => {
    const res = await apiClient.delete(
      `/api/photos/${encodeURIComponent(path)}/rating`
    );
    return res.data;
  },

  getPhotosByRating: async (
    rating: number,
    limit: number = 100,
    offset: number = 0
  ) => {
    const res = await apiClient.get(`/api/ratings/photos/${rating}`, {
      params: { limit, offset },
    });
    return res.data;
  },

  getRatingStats: async () => {
    const res = await apiClient.get('/api/ratings/stats');
    return res.data.stats;
  },

  // Notes management
  getPhotoNote: async (path: string) => {
    const res = await apiClient.get(
      `/api/photos/${encodeURIComponent(path)}/notes`
    );
    return res.data as { note: string | null; updated_at?: string | null };
  },

  setPhotoNote: async (path: string, note: string) => {
    const res = await apiClient.post(
      `/api/photos/${encodeURIComponent(path)}/notes`,
      { note }
    );
    return res.data;
  },

  deletePhotoNote: async (path: string) => {
    const res = await apiClient.delete(
      `/api/photos/${encodeURIComponent(path)}/notes`
    );
    return res.data;
  },

  searchNotes: async (
    query: string,
    limit: number = 100,
    offset: number = 0
  ) => {
    const res = await apiClient.get('/api/notes/search', {
      params: { query, limit, offset },
    });
    return res.data;
  },

  getNotesStats: async () => {
    const res = await apiClient.get('/api/notes/stats');
    return res.data.stats;
  },

  // Editing
  getPhotoEdits: async (path: string) => {
    const res = await apiClient.get(
      `/api/photos/${encodeURIComponent(path)}/edits`
    );
    return res.data.edit_data;
  },

  // Export and Share
  exportPhotos: async (paths: string[], options: ExportOptions) => {
    const res = await apiClient.post(
      '/export',
      { paths, options },
      { responseType: 'blob' }
    );
    return res.data;
  },

  getExportPresets: async () => {
    const res = await apiClient.get('/export/presets');
    return res.data.presets;
  },

  createShareLink: async (
    paths: string[],
    expirationHours: number = 24,
    password?: string
  ) => {
    const res = await apiClient.post('/share', {
      paths,
      expiration_hours: expirationHours,
      password,
    });
    return res.data;
  },

  getSharedContent: async (shareId: string, password?: string) => {
    const params: any = {};
    if (password) params.password = password;

    const res = await apiClient.get(`/shared/${encodeURIComponent(shareId)}`, {
      params,
    });

    // Backend returns { paths: string[], download_count: number }
    return res.data;
  },

  getNearbyLocations: async (
    latitude: number,
    longitude: number,
    radiusKm: number = 1.0
  ) => {
    const res = await apiClient.get('/locations/nearby', {
      params: { latitude, longitude, radius_km: radiusKm },
    });
    return res.data;
  },

  getPlaceClusters: async (minPhotos: number = 2) => {
    const res = await apiClient.get('/locations/clusters', {
      params: { min_photos: minPhotos },
    });
    return res.data.clusters;
  },

  // Intent-based search
  searchWithIntent: async (params: IntentSearchParams) => {
    const res = await apiClient.post('/search/intent', params);
    return res.data;
  },

  refineSearch: async (
    query: string,
    previousResults: SearchResult[],
    refinement: string
  ) => {
    const res = await apiClient.post('/search/refine', {
      query,
      previous_results: previousResults,
      refinement,
    });
    return res.data;
  },

  detectIntent: async (query: string) => {
    const res = await apiClient.get('/intent/detect', { params: { query } });
    return res.data;
  },

  getSearchSuggestions: async (query: string) => {
    const res = await apiClient.get('/intent/suggestions', {
      params: { query },
    });
    return res.data.suggestions;
  },

  getSearchBadges: async (query: string) => {
    const res = await apiClient.get('/intent/badges', { params: { query } });
    return res.data.badges;
  },

  // Smart Collections
  createSmartCollection: async (
    name: string,
    description: string,
    ruleDefinition: SmartCollectionRule,
    autoUpdate: boolean = true,
    privacyLevel: string = 'private'
  ) => {
    const res = await apiClient.post('/collections/smart', {
      name,
      description,
      rule_definition: ruleDefinition,
      auto_update: autoUpdate,
      privacy_level: privacyLevel,
    });
    return res.data;
  },

  getSmartCollections: async (limit: number = 50, offset: number = 0) => {
    const res = await apiClient.get('/collections/smart', {
      params: { limit, offset },
    });
    return res.data.collections;
  },

  getSmartCollection: async (collectionId: string) => {
    const res = await apiClient.get(
      `/collections/smart/${encodeURIComponent(collectionId)}`
    );
    return res.data.collection;
  },

  updateSmartCollection: async (
    collectionId: string,
    updates: SmartCollectionUpdate
  ) => {
    const res = await apiClient.put(
      `/collections/smart/${encodeURIComponent(collectionId)}`,
      updates
    );
    return res.data;
  },

  deleteSmartCollection: async (collectionId: string) => {
    const res = await apiClient.delete(
      `/collections/smart/${encodeURIComponent(collectionId)}`
    );
    return res.data;
  },

  getPhotosForCollection: async (collectionId: string) => {
    const res = await apiClient.get(
      `/collections/smart/${encodeURIComponent(collectionId)}/photos`
    );
    return res.data.photos;
  },

  getSmartCollectionsByRuleType: async (ruleType: string) => {
    const res = await apiClient.get(
      `/collections/smart/by-rule/${encodeURIComponent(ruleType)}`
    );
    return res.data.collections;
  },

  getSmartCollectionStats: async () => {
    const res = await apiClient.get('/collections/smart/stats');
    return res.data.stats;
  },

  // Performance and caching (getCacheStats already defined above)

  clearCache: async (_cacheType?: string) => {
    // Backend route is API-prefixed (see server/api/routers/system.py @ /api/cache/clear)
    const res = await apiClient.post('/api/cache/clear');
    return res.data;
  },

  getCacheHealth: async () => {
    const res = await apiClient.get('/cache/health');
    return res.data;
  },

  // Insights
  createAIInsight: async (
    photoPath: string,
    insightType: string,
    insightData: AIInsightData,
    confidence: number = 0.8
  ) => {
    const res = await apiClient.post('/ai/insights', {
      photo_path: photoPath,
      insight_type: insightType,
      insight_data: insightData,
      confidence,
    });
    return res.data;
  },

  getInsightsForPhoto: async (photoPath: string) => {
    const res = await apiClient.get(
      `/ai/insights/photo/${encodeURIComponent(photoPath)}`
    );
    return res.data.insights;
  },

  getInsightsByType: async (insightType: string, limit: number = 50) => {
    const res = await apiClient.get(
      `/ai/insights/type/${encodeURIComponent(insightType)}`,
      {
        params: { limit },
      }
    );
    return res.data.insights;
  },

  getAllInsights: async (limit: number = 100, offset: number = 0) => {
    const res = await apiClient.get('/ai/insights', {
      params: { limit, offset },
    });
    return res.data.insights;
  },

  updateInsightAppliedStatus: async (insightId: string, isApplied: boolean) => {
    const res = await apiClient.put(
      `/ai/insights/${encodeURIComponent(insightId)}`,
      {
        is_applied: isApplied,
      }
    );
    return res.data;
  },

  deleteInsight: async (insightId: string) => {
    const res = await apiClient.delete(
      `/ai/insights/${encodeURIComponent(insightId)}`
    );
    return res.data;
  },

  getInsightsStats: async () => {
    const res = await apiClient.get('/ai/insights/stats');
    return res.data.stats;
  },

  // analyzePhotographerPatterns already defined above

  // Collaborative Spaces
  createCollaborativeSpace: async (
    name: string,
    description: string,
    privacyLevel: string = 'private',
    maxMembers: number = 10
  ) => {
    const res = await apiClient.post('/collaborative/spaces', {
      name,
      description,
      privacy_level: privacyLevel,
      max_members: maxMembers,
    });
    return res.data;
  },

  getCollaborativeSpace: async (spaceId: string) => {
    const res = await apiClient.get(
      `/collaborative/spaces/${encodeURIComponent(spaceId)}`
    );
    return res.data.space;
  },

  getUserSpaces: async (
    userId: string,
    limit: number = 50,
    offset: number = 0
  ) => {
    const res = await apiClient.get(
      `/collaborative/spaces/user/${encodeURIComponent(userId)}`,
      {
        params: { limit, offset },
      }
    );
    return res.data.spaces;
  },

  addMemberToSpace: async (
    spaceId: string,
    userId: string,
    role: string = 'contributor'
  ) => {
    const res = await apiClient.post(
      `/collaborative/spaces/${encodeURIComponent(spaceId)}/members`,
      {
        user_id: userId,
        role,
      }
    );
    return res.data;
  },

  removeMemberFromSpace: async (spaceId: string, userId: string) => {
    const res = await apiClient.delete(
      `/collaborative/spaces/${encodeURIComponent(
        spaceId
      )}/members/${encodeURIComponent(userId)}`
    );
    return res.data;
  },

  getSpaceMembers: async (spaceId: string) => {
    const res = await apiClient.get(
      `/collaborative/spaces/${encodeURIComponent(spaceId)}/members`
    );
    return res.data.members;
  },

  addPhotoToSpace: async (
    spaceId: string,
    photoPath: string,
    caption?: string
  ) => {
    const res = await apiClient.post(
      `/collaborative/spaces/${encodeURIComponent(spaceId)}/photos`,
      {
        photo_path: photoPath,
        caption,
      }
    );
    return res.data;
  },

  removePhotoFromSpace: async (spaceId: string, photoPath: string) => {
    const res = await apiClient.delete(
      `/collaborative/spaces/${encodeURIComponent(
        spaceId
      )}/photos/${encodeURIComponent(photoPath)}`
    );
    return res.data;
  },

  getSpacePhotos: async (
    spaceId: string,
    limit: number = 50,
    offset: number = 0
  ) => {
    const res = await apiClient.get(
      `/collaborative/spaces/${encodeURIComponent(spaceId)}/photos`,
      {
        params: { limit, offset },
      }
    );
    return res.data.photos;
  },

  addCommentToSpacePhoto: async (
    spaceId: string,
    photoPath: string,
    comment: string
  ) => {
    const res = await apiClient.post(
      `/collaborative/spaces/${encodeURIComponent(
        spaceId
      )}/photos/${encodeURIComponent(photoPath)}/comments`,
      {
        comment,
      }
    );
    return res.data;
  },

  getPhotoComments: async (
    spaceId: string,
    photoPath: string,
    limit: number = 50,
    offset: number = 0
  ) => {
    const res = await apiClient.get(
      `/collaborative/spaces/${encodeURIComponent(
        spaceId
      )}/photos/${encodeURIComponent(photoPath)}/comments`,
      {
        params: { limit, offset },
      }
    );
    return res.data.comments;
  },

  getSpaceStats: async (spaceId: string) => {
    const res = await apiClient.get(
      `/collaborative/spaces/${encodeURIComponent(spaceId)}/stats`
    );
    return res.data;
  },

  // setPhotoEdits and deletePhotoEdits already defined above

  // People management
  getPeopleInPhoto: async (path: string) => {
    const res = await apiClient.get(
      `/api/photos/${encodeURIComponent(path)}/people`
    );
    return res.data.people;
  },

  addPersonToPhoto: async (
    path: string,
    personId: string,
    detectionId?: string
  ) => {
    const res = await apiClient.post(
      `/api/photos/${encodeURIComponent(path)}/people`,
      {
        person_id: personId,
        detection_id: detectionId,
      }
    );
    return res.data;
  },

  // Explicit alias for callers that want to be clear about intent.
  addPersonToPhotoWithDetection: async (
    path: string,
    personId: string,
    detectionId: string
  ) => {
    return await api.addPersonToPhoto(path, personId, detectionId);
  },

  // Compatibility alias used by some People/Cluster components
  getAllClusters: async () => {
    return await api.getFaceClusters();
  },

  removePersonFromPhoto: async (path: string, personId: string) => {
    const res = await apiClient.delete(
      `/api/photos/${encodeURIComponent(path)}/people/${encodeURIComponent(
        personId
      )}`
    );
    return res.data;
  },

  searchPeople: async (query: string, limit: number = 10) => {
    const res = await apiClient.get('/api/people/search', {
      params: { query, limit },
    });
    return res.data;
  },

  // Face Detection
  detectFaces: async (path: string) => {
    const res = await apiClient.post(
      `/api/photos/${encodeURIComponent(path)}/faces/detect`
    );
    return res.data;
  },

  getFacesInPhoto: async (path: string) => {
    const res = await apiClient.get(
      `/api/photos/${encodeURIComponent(path)}/faces`
    );
    return res.data;
  },

  getFaceThumbnail: async (detectionId: string) => {
    const res = await apiClient.get(
      `/api/faces/${encodeURIComponent(detectionId)}/thumbnail`
    );
    return res.data;
  },

  detectFacesBatch: async (photoPaths: string[]) => {
    const res = await apiClient.post('/api/photos/batch/faces/detect', {
      photo_paths: photoPaths,
    });
    return res.data;
  },

  // Automatic Clustering
  clusterFaces: async (
    similarityThreshold: number = 0.6,
    minSamples: number = 2
  ) => {
    const res = await apiClient.post('/api/faces/cluster', null, {
      params: {
        similarity_threshold: similarityThreshold,
        min_samples: minSamples,
      },
    });
    return res.data;
  },

  // Find similar faces with extended options (Phase 4)
  findSimilarFaces: async (
    detectionId: string,
    threshold: number = 0.5,
    limit: number = 20,
    includeSameCluster: boolean = false
  ) => {
    const res = await apiClient.get(
      `/api/faces/${encodeURIComponent(detectionId)}/similar`,
      {
        params: { threshold, limit, include_same_cluster: includeSameCluster },
      }
    );
    return res.data;
  },

  // Face Clustering
  getFaceClusters: async () => {
    const res = await apiClient.get('/api/faces/clusters');
    return res.data;
  },

  getFaceStats: async () => {
    const res = await apiClient.get('/api/faces/stats');
    return res.data;
  },

  scanFaces: async () => {
    const res = await apiClient.post('/api/faces/scan');
    return res.data;
  },

  setFaceClusterLabel: async (clusterId: string, label: string) => {
    const res = await apiClient.post(
      `/api/faces/clusters/${encodeURIComponent(clusterId)}/label`,
      { label }
    );
    return res.data;
  },

  deletePerson: async (clusterId: string): Promise<void> => {
    await apiClient.delete(`/api/faces/clusters/${encodeURIComponent(clusterId)}`);
  },

  getClusterQuality: async (clusterId: string) => {
    const res = await apiClient.get(
      `/api/clusters/${encodeURIComponent(clusterId)}/quality`
    );
    return res.data;
  },

  mergeClusters: async (clusterId: string, targetClusterId: string) => {
    const res = await apiClient.post(
      `/api/clusters/${encodeURIComponent(clusterId)}/merge`,
      {
        target_cluster_id: targetClusterId,
      }
    );
    return res.data;
  },

  // Phase 1: Reversibility and Trust APIs

  // Hide a cluster from the main gallery
  hideCluster: async (clusterId: string) => {
    const res = await apiClient.post(
      `/api/faces/clusters/${encodeURIComponent(clusterId)}/hide`
    );
    return res.data;
  },

  // Unhide a cluster
  unhideCluster: async (clusterId: string) => {
    const res = await apiClient.post(
      `/api/faces/clusters/${encodeURIComponent(clusterId)}/unhide`
    );
    return res.data;
  },

  // Get only visible (non-hidden) clusters
  getVisibleClusters: async () => {
    const res = await apiClient.get('/api/faces/clusters/visible');
    return res.data;
  },

  // Get hidden clusters
  getHiddenClusters: async () => {
    const res = await apiClient.get('/api/faces/clusters/hidden');
    return res.data;
  },

  // Confirm a face assignment (user verified)
  confirmFace: async (faceId: string, clusterId: string) => {
    const res = await apiClient.post(
      `/api/faces/${encodeURIComponent(faceId)}/confirm`,
      { cluster_id: clusterId }
    );
    return res.data;
  },

  // Reject a face from a cluster (not this person)
  rejectFace: async (faceId: string, clusterId: string) => {
    const res = await apiClient.post(
      `/api/faces/${encodeURIComponent(faceId)}/reject`,
      { cluster_id: clusterId }
    );
    return res.data;
  },

  // Split selected faces into a new person cluster
  splitFaces: async (detectionIds: string[], label?: string) => {
    const res = await apiClient.post('/api/faces/split', {
      detection_ids: detectionIds,
      label,
    });
    return res.data;
  },

  // Move a single face to a different cluster
  moveFace: async (detectionId: string, toClusterId: string) => {
    const res = await apiClient.post('/api/faces/move', {
      detection_id: detectionId,
      to_cluster_id: toClusterId,
    });
    return res.data;
  },

  // Merge clusters with full undo support
  mergeClustersWithUndo: async (sourceClusterId: string, targetClusterId: string) => {
    const res = await apiClient.post('/api/faces/merge', {
      source_cluster_id: sourceClusterId,
      target_cluster_id: targetClusterId,
    });
    return res.data;
  },

  // Undo the last person operation
  undoLastOperation: async () => {
    const res = await apiClient.post('/api/faces/undo');
    return res.data;
  },

  // Get unassigned faces (unknown bucket)
  getUnassignedFaces: async (limit: number = 100, offset: number = 0) => {
    const res = await apiClient.get('/api/faces/unassigned', {
      params: { limit, offset },
    });
    return res.data;
  },

  // Rename a cluster with undo support
  renameCluster: async (clusterId: string, label: string) => {
    const res = await apiClient.post(
      `/api/faces/clusters/${encodeURIComponent(clusterId)}/rename`,
      { label }
    );
    return res.data;
  },

  // Recompute prototype embeddings for all clusters
  recomputePrototypes: async () => {
    const res = await apiClient.post('/api/faces/prototypes/recompute');
    return res.data;
  },

  // Phase 2: Trust Signals APIs

  // Get coherence analysis for a cluster (detect mixed clusters)
  getClusterCoherence: async (clusterId: string) => {
    const res = await apiClient.get(
      `/api/faces/clusters/${encodeURIComponent(clusterId)}/coherence`
    );
    return res.data;
  },

  // Get all clusters suspected to contain multiple people
  getMixedClusters: async (threshold: number = 0.5) => {
    const res = await apiClient.get('/api/faces/mixed-clusters', {
      params: { threshold },
    });
    return res.data;
  },

  // Phase 5.4: Merge Suggestions

  // Get conservative merge suggestions based on prototype similarity
  getMergeSuggestions: async (threshold: number = 0.62, maxSuggestions: number = 10) => {
    const res = await apiClient.get('/api/faces/clusters/merge-suggestions', {
      params: { threshold, max_suggestions: maxSuggestions },
    });
    return res.data;
  },

  // Dismiss a merge suggestion so it won't appear again
  dismissMergeSuggestion: async (clusterAId: string, clusterBId: string) => {
    const res = await apiClient.post('/api/faces/clusters/merge-suggestions/dismiss', {
      cluster_a_id: clusterAId,
      cluster_b_id: clusterBId,
    });
    return res.data;
  },

  // Phase 6: Privacy Controls

  // Get indexing status for a specific person cluster
  getPersonIndexingStatus: async (clusterId: string) => {
    const res = await apiClient.get(`/api/faces/clusters/${clusterId}/indexing`);
    return res.data;
  },

  // Enable or disable auto-assignment to a specific person
  setPersonIndexingEnabled: async (clusterId: string, enabled: boolean, reason?: string) => {
    const res = await apiClient.post(`/api/faces/clusters/${clusterId}/indexing`, {
      enabled,
      reason,
    });
    return res.data;
  },

  // Get global face indexing pause status
  getGlobalIndexingStatus: async () => {
    const res = await apiClient.get('/api/faces/indexing/status');
    return res.data;
  },

  // Pause global face indexing
  pauseGlobalIndexing: async () => {
    const res = await apiClient.post('/api/faces/indexing/pause');
    return res.data;
  },

  // Resume global face indexing
  resumeGlobalIndexing: async () => {
    const res = await apiClient.post('/api/faces/indexing/resume');
    return res.data;
  },

  // Phase 3: Speed & Scale APIs


  // Assign a single face to the best matching cluster
  assignFaceToCluster: async (
    detectionId: string,
    embedding: number[],
    autoAssignMin: number = 0.55,
    reviewMin: number = 0.50
  ) => {
    const res = await apiClient.post('/api/faces/assign', {
      detection_id: detectionId,
      embedding,
      auto_assign_min: autoAssignMin,
      review_min: reviewMin,
    });
    return res.data;
  },

  // Batch assign multiple faces to clusters
  batchAssignFaces: async (
    faces: Array<{ detection_id: string; embedding: number[] }>,
    autoAssignMin: number = 0.55,
    reviewMin: number = 0.50
  ) => {
    const res = await apiClient.post('/api/faces/batch-assign', {
      faces,
      auto_assign_min: autoAssignMin,
      review_min: reviewMin,
    });
    return res.data;
  },

  // Get embedding index statistics
  getEmbeddingIndexStats: async () => {
    const res = await apiClient.get('/api/faces/index/stats');
    return res.data;
  },

  // Phase 4: Search & Retrieval APIs

  // Search photos by people IDs (co-occurrence)
  searchPhotosByPeopleIds: async (
    includePeople: string[],
    excludePeople?: string[],
    requireAll: boolean = true,
    limit: number = 100,
    offset: number = 0
  ) => {
    const res = await apiClient.post('/api/photos/by-people', {
      include_people: includePeople,
      exclude_people: excludePeople,
      require_all: requireAll,
      limit,
      offset,
    });
    return res.data;
  },

  // Search photos by people names (natural language-like)
  searchPhotosByPeopleNames: async (
    query: string,
    mode: 'and' | 'or' = 'and',
    limit: number = 100,
    offset: number = 0
  ) => {
    const res = await apiClient.get('/api/photos/by-people-names', {
      params: { query, mode, limit, offset },
    });
    return res.data;
  },

  // Privacy Controls

  setPhotoPrivacy: async (
    photoPath: string,
    ownerId: string,
    visibility: string = 'private',
    sharePermissions: Record<string, boolean> | null = null,
    encryptionEnabled: boolean = false,
    encryptionKeyHash?: string,
    allowedUsers?: string[],
    allowedGroups?: string[]
  ) => {
    const res = await apiClient.post(
      `/privacy/control/${encodeURIComponent(photoPath)}`,
      {
        owner_id: ownerId,
        visibility,
        share_permissions: sharePermissions,
        encryption_enabled: encryptionEnabled,
        encryption_key_hash: encryptionKeyHash,
        allowed_users: allowedUsers,
        allowed_groups: allowedGroups,
      }
    );
    return res.data;
  },

  getPhotoPrivacy: async (photoPath: string) => {
    const res = await apiClient.get(
      `/privacy/control/${encodeURIComponent(photoPath)}`
    );
    return res.data.privacy;
  },

  updatePhotoPrivacy: async (
    photoPath: string,
    updates: {
      visibility?: string;
      share_permissions?: Record<string, boolean>;
      encryption_enabled?: boolean;
      encryption_key_hash?: string;
      allowed_users?: string[];
      allowed_groups?: string[];
    }
  ) => {
    const res = await apiClient.put(
      `/privacy/control/${encodeURIComponent(photoPath)}`,
      updates
    );
    return res.data;
  },

  getPhotosByVisibility: async (
    visibility: string,
    ownerId: string,
    limit: number = 50,
    offset: number = 0
  ) => {
    const res = await apiClient.get(
      `/privacy/visible/${encodeURIComponent(visibility)}/${encodeURIComponent(
        ownerId
      )}`,
      {
        params: { limit, offset },
      }
    );
    return res.data.photos;
  },

  getPhotosAccessibleToUser: async (
    userId: string,
    limit: number = 50,
    offset: number = 0
  ) => {
    const res = await apiClient.get(
      `/privacy/access/${encodeURIComponent(userId)}`,
      {
        params: { limit, offset },
      }
    );
    return res.data.photos;
  },

  checkPhotoAccess: async (photoPath: string, userId: string) => {
    const res = await apiClient.get(
      `/privacy/check-access/${encodeURIComponent(
        photoPath
      )}/${encodeURIComponent(userId)}`
    );
    return res.data.has_access;
  },

  getEncryptedPhotos: async (ownerId: string) => {
    const res = await apiClient.get(
      `/privacy/encrypted/${encodeURIComponent(ownerId)}`
    );
    return res.data.encrypted_photos;
  },

  getPrivacyStats: async (ownerId: string) => {
    const res = await apiClient.get(
      `/privacy/stats/${encodeURIComponent(ownerId)}`
    );
    return res.data.stats;
  },

  revokeUserAccess: async (photoPath: string, userId: string) => {
    const res = await apiClient.delete(
      `/privacy/revoke-access/${encodeURIComponent(
        photoPath
      )}/${encodeURIComponent(userId)}`
    );
    return res.data;
  },

  // Timeline & Story Creation
  createStory: async (
    title: string,
    description: string,
    privacyLevel: string = 'private'
  ) => {
    const res = await apiClient.post('/stories', {
      title,
      description,
      privacy_level: privacyLevel,
    });
    return res.data;
  },

  getStory: async (storyId: string) => {
    const res = await apiClient.get(`/stories/${encodeURIComponent(storyId)}`);
    return res.data.story;
  },

  getStoriesByOwner: async (
    ownerId: string,
    includeUnpublished: boolean = false,
    limit: number = 50,
    offset: number = 0
  ) => {
    const res = await apiClient.get(
      `/stories/owner/${encodeURIComponent(ownerId)}`,
      {
        params: { include_unpublished: includeUnpublished, limit, offset },
      }
    );
    return res.data.stories;
  },

  updateStory: async (storyId: string, updates: StoryUpdate) => {
    const res = await apiClient.put(
      `/stories/${encodeURIComponent(storyId)}`,
      updates
    );
    return res.data;
  },

  addPhotoToStory: async (storyId: string, photoData: StoryPhotoData) => {
    const res = await apiClient.post(
      `/stories/${encodeURIComponent(storyId)}/photos`,
      photoData
    );
    return res.data;
  },

  getStoryTimeline: async (storyId: string) => {
    const res = await apiClient.get(
      `/stories/${encodeURIComponent(storyId)}/timeline`
    );
    return res.data.timeline;
  },

  updateTimelineEntry: async (
    entryId: string,
    updates: TimelineEntryUpdate
  ) => {
    const res = await apiClient.put(
      `/timeline/entries/${encodeURIComponent(entryId)}`,
      updates
    );
    return res.data;
  },

  removePhotoFromTimeline: async (entryId: string) => {
    const res = await apiClient.delete(
      `/timeline/entries/${encodeURIComponent(entryId)}`
    );
    return res.data;
  },

  getStoryStats: async (storyId: string) => {
    const res = await apiClient.get(
      `/stories/${encodeURIComponent(storyId)}/stats`
    );
    return res.data.stats;
  },

  getUserStoryStats: async (userId: string) => {
    const res = await apiClient.get(
      `/stories/user/${encodeURIComponent(userId)}/stats`
    );
    return res.data.stats;
  },

  toggleStoryPublish: async (storyId: string, publish: boolean) => {
    const res = await apiClient.post(
      `/stories/${encodeURIComponent(storyId)}/publish`,
      { publish }
    );
    return res.data;
  },

  // Bulk Actions with Undo
  recordBulkAction: async (
    actionType: string,
    paths: string[],
    operationData?: BulkActionOperationData
  ) => {
    const res = await apiClient.post('/bulk/action', {
      action_type: actionType,
      paths,
      operation_data: operationData,
    });
    return res.data;
  },

  getBulkActionHistory: async (
    userId: string,
    actionType?: string,
    limit: number = 50,
    offset: number = 0
  ) => {
    const res = await apiClient.get(
      `/bulk/history/${encodeURIComponent(userId)}`,
      {
        params: { action_type: actionType, limit, offset },
      }
    );
    return res.data;
  },

  undoBulkAction: async (actionId: string) => {
    const res = await apiClient.post(
      `/bulk/undo/${encodeURIComponent(actionId)}`
    );
    return res.data;
  },

  canUndoBulkAction: async (actionId: string) => {
    const res = await apiClient.get(
      `/bulk/can-undo/${encodeURIComponent(actionId)}`
    );
    return res.data;
  },

  getBulkActionsStats: async (userId: string) => {
    const res = await apiClient.get(
      `/bulk/stats/${encodeURIComponent(userId)}`
    );
    return res.data;
  },

  // Multi-tag Filtering
  createTagFilter: async (
    name: string,
    tagExpressions: TagExpression[],
    combinationOperator: string = 'AND'
  ) => {
    const res = await apiClient.post('/tag-filters', {
      name,
      tag_expressions: tagExpressions,
      combination_operator: combinationOperator,
    });
    return res.data;
  },

  getTagFilter: async (filterId: string) => {
    const res = await apiClient.get(
      `/tag-filters/${encodeURIComponent(filterId)}`
    );
    return res.data.tag_filter;
  },

  getTagFilters: async (limit: number = 50, offset: number = 0) => {
    const res = await apiClient.get('/tag-filters', {
      params: { limit, offset },
    });
    return res.data.filters;
  },

  updateTagFilter: async (filterId: string, updates: TagFilterUpdate) => {
    const res = await apiClient.put(
      `/tag-filters/${encodeURIComponent(filterId)}`,
      updates
    );
    return res.data;
  },

  deleteTagFilter: async (filterId: string) => {
    const res = await apiClient.delete(
      `/tag-filters/${encodeURIComponent(filterId)}`
    );
    return res.data;
  },

  applyTagFilter: async (
    tagExpressions: TagExpression[],
    combinationOperator: string = 'AND'
  ) => {
    const res = await apiClient.post('/tag-filters/apply', {
      tag_expressions: tagExpressions,
      combination_operator: combinationOperator,
    });
    return res.data;
  },

  getPhotosByTags: async (
    tags: string[],
    operator: string = 'OR',
    excludeTags?: string[]
  ) => {
    const params: any = {
      tags: tags.join(','),
      operator,
    };

    if (excludeTags) {
      params.exclude_tags = excludeTags.join(',');
    }

    const res = await apiClient.get('/photos/by-tags', { params });
    return res.data;
  },

  getCommonTags: async (photoPaths: string[], limit: number = 10) => {
    const res = await apiClient.get('/tags/common', {
      params: { photo_paths: photoPaths.join(','), limit },
    });
    return res.data.common_tags;
  },

  searchTags: async (query: string, limit: number = 20) => {
    const res = await apiClient.get('/tags/search', {
      params: { query, limit },
    });
    return res.data.tags;
  },

  getTagStats: async () => {
    const res = await apiClient.get('/tags/stats');
    return res.data.stats;
  },

  // Version Stacks
  createPhotoVersion: async (
    originalPath: string,
    versionPath: string,
    versionType: string = 'edit',
    versionName?: string,
    versionDescription?: string,
    editInstructions?: EditInstructions,
    parentVersionId?: string
  ) => {
    const res = await apiClient.post('/versions', {
      original_path: originalPath,
      version_path: versionPath,
      version_type: versionType,
      version_name: versionName,
      version_description: versionDescription,
      edit_instructions: editInstructions,
      parent_version_id: parentVersionId,
    });
    return res.data;
  },

  getPhotoVersions: async (photoPath: string) => {
    const res = await apiClient.get(
      `/versions/photo/${encodeURIComponent(photoPath)}`
    );
    return res.data;
  },

  getVersionStack: async (originalPath: string) => {
    const res = await apiClient.get(
      `/versions/stack/${encodeURIComponent(originalPath)}`
    );
    return res.data.stack;
  },

  updateVersionMetadata: async (
    versionPath: string,
    updates: { versionName?: string; versionDescription?: string }
  ) => {
    const res = await apiClient.put(
      `/versions/${encodeURIComponent(versionPath)}`,
      updates
    );
    return res.data;
  },

  deleteVersion: async (versionId: string) => {
    const res = await apiClient.delete(
      `/versions/${encodeURIComponent(versionId)}`
    );
    return res.data;
  },

  getAllVersionStacks: async (limit: number = 50, offset: number = 0) => {
    const res = await apiClient.get('/versions/stacks', {
      params: { limit, offset },
    });
    return res.data.stacks;
  },

  getVersionStats: async () => {
    const res = await apiClient.get('/versions/stats');
    return res.data.stats;
  },

  mergeVersionStacks: async (path1: string, path2: string) => {
    const res = await apiClient.post('/versions/merge-stacks', {
      path1,
      path2,
    });
    return res.data;
  },

  // Location Clustering & Correction
  correctPhotoLocation: async (
    photoPath: string,
    correction: {
      corrected_place_name?: string | null;
      country?: string | null;
      region?: string | null;
      city?: string | null;
    }
  ) => {
    const res = await apiClient.post(
      `/locations/correct/${encodeURIComponent(photoPath)}`,
      correction
    );
    return res.data;
  },

  getPhotoLocation: async (photoPath: string) => {
    const res = await apiClient.get(
      `/locations/photo/${encodeURIComponent(photoPath)}`
    );
    return res.data.location;
  },

  getPhotosNearby: async (
    latitude: number,
    longitude: number,
    radiusKm: number = 1.0
  ) => {
    const res = await apiClient.get('/locations/nearby', {
      params: { latitude, longitude, radius_km: radiusKm },
    });
    return res.data;
  },

  getLocationClusters: async (minPhotos: number = 2) => {
    const res = await apiClient.get('/locations/clusters', {
      params: { min_photos: minPhotos },
    });
    return res.data;
  },

  getPhotosInCluster: async (
    clusterId: string,
    limit: number = 50,
    offset: number = 0
  ) => {
    const res = await apiClient.get(
      `/locations/clusters/${encodeURIComponent(clusterId)}/photos`,
      {
        params: { limit, offset },
      }
    );
    return res.data;
  },

  getPhotoCluster: async (photoPath: string) => {
    const res = await apiClient.get(
      `/locations/photo/${encodeURIComponent(photoPath)}/cluster`
    );
    return res.data.cluster;
  },

  createLocationClusters: async (
    minPhotos: number = 2,
    maxDistanceMeters: number = 100
  ) => {
    const res = await apiClient.post('/locations/clusterize', null, {
      params: { min_photos: minPhotos, max_distance_meters: maxDistanceMeters },
    });
    return res.data;
  },

  getLocationStats: async () => {
    const res = await apiClient.get('/locations/stats');
    return res.data;
  },

  bulkCorrectPlaceNames: async (
    photoPaths: string[],
    correctedName: string
  ) => {
    const res = await apiClient.post('/locations/correct-bulk', {
      photo_paths: photoPaths,
      corrected_name: correctedName,
    });
    return res.data;
  },

  // ===================================================================
  // Phase 5: Review Queue API
  // ===================================================================

  getReviewQueue: async (
    limit: number = 20,
    offset: number = 0,
    sort: string = 'similarity_desc'
  ) => {
    const res = await apiClient.get('/api/faces/review-queue', {
      params: { limit, offset, sort },
    });
    return res.data;
  },

  getReviewQueueCount: async () => {
    const res = await apiClient.get('/api/faces/review-queue/count');
    return res.data.count;
  },

  resolveReviewItem: async (
    detectionId: string,
    action: 'confirm' | 'reject' | 'skip',
    clusterId?: string
  ) => {
    const res = await apiClient.post(
      `/api/faces/review-queue/${detectionId}/resolve`,
      {
        action,
        cluster_id: clusterId,
      }
    );
    return res.data;
  },
};
