import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

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
    signal?: AbortSignal
  ) => {
    const res = await apiClient.get('/search', {
      params: {
        query,
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
    const res = await apiClient.get('/server/config');
    return res.data;
  },

  // Obtain a signed thumbnail URL from the server (server must support /image/token and require auth)
  getSignedImageUrl: async (path: string, size?: number, ttl?: number) => {
    try {
      const res = await apiClient.post('/image/token', {
        path,
        ttl,
        scope: 'thumbnail',
      });
      const token = res.data?.token;
      if (!token) return null;
      return `${API_BASE}/image/thumbnail?token=${encodeURIComponent(token)}${
        size ? `&size=${size}` : ''
      }`;
    } catch {
      // If token issuance failed (unauthenticated or server error), fall back to regular image URL
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

  // Export selected photos as ZIP
  exportPhotos: async (paths: string[]) => {
    const res = await apiClient.post(
      '/export',
      { paths },
      {
        responseType: 'blob',
      }
    );
    // Trigger download
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'photos_export.zip');
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

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
    return res.data;
  },

  getFavorites: async (limit: number = 1000, offset: number = 0) => {
    const res = await apiClient.get('/favorites', {
      params: { limit, offset },
    });
    return res.data;
  },

  checkFavorite: async (filePath: string) => {
    const res = await apiClient.get('/favorites/check', {
      params: { file_path: filePath },
    });
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

  clearCache: async () => {
    const res = await apiClient.post('/api/cache/clear');
    return res.data;
  },

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
    const res = await apiClient.get(`/api/photos/${encodeURIComponent(path)}/rating`);
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
    const res = await apiClient.delete(`/api/photos/${encodeURIComponent(path)}/rating`);
    return res.data;
  },

  getPhotosByRating: async (rating: number, limit: number = 100, offset: number = 0) => {
    const res = await apiClient.get(`/api/ratings/photos/${rating}`, {
      params: { limit, offset }
    });
    return res.data;
  },

  getRatingStats: async () => {
    const res = await apiClient.get('/api/ratings/stats');
    return res.data.stats;
  },
};
