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

export interface Photo {
  path: string;
  filename: string;
  score: number;
  metadata: PhotoMetadata;
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

export const api = {
  scan: async (path: string, background: boolean = true) => {
    const res = await apiClient.post('/scan', { path, background });
    return res.data; // Returns { job_id, status } if background=true
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
    dateFrom?: string | null,
    dateTo?: string | null,
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
        favorites_filter: favoritesFilter,
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

  // Serve the original file (no transcoding); set download=true to force attachment
  getFileUrl: (path: string, opts?: { download?: boolean }) => {
    const encodedPath = encodeURIComponent(path);
    const download = opts?.download ? '&download=true' : '';
    return `${API_BASE}/file?path=${encodedPath}${download}`;
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

  // Health check for backend connectivity
  healthCheck: async () => {
    try {
      const res = await apiClient.get('/', { timeout: 5000 });
      return res.data.status === 'ok';
    } catch {
      return false;
    }
  },
};
