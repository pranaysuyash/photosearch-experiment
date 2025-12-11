import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export interface Photo {
  path: string;
  filename: string;
  score: number;
  metadata: Record<string, any>;
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
  result?: any;
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
    const res = await axios.post(`${API_BASE}/scan`, { path, background });
    return res.data; // Returns { job_id, status } if background=true
  },

  getJobStatus: async (jobId: string) => {
    const res = await axios.get(`${API_BASE}/jobs/${jobId}`);
    return res.data as Job;
  },
  
  search: async (
    query: string, 
    mode: string = 'metadata', 
    limit: number = 50, 
    offset: number = 0,
    sortBy: string = 'date_desc',
    typeFilter: string = 'all'
  ) => {
    const res = await axios.get(`${API_BASE}/search`, { 
      params: { query, mode, limit, offset, sort_by: sortBy, type_filter: typeFilter } 
    });
    return res.data;
  },
  
  getTimeline: async () => {
    const res = await axios.get(`${API_BASE}/timeline`);
    return res.data.timeline as TimelineData[];
  },
  
  getImageUrl: (path: string, size?: number) => {
    const encodedPath = encodeURIComponent(path);
    return `${API_BASE}/image/thumbnail?path=${encodedPath}${size ? `&size=${size}` : ''}`;
  },

  // Check if file is a video
  isVideo: (path: string) => {
    const videoExts = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'];
    return videoExts.some(ext => path.toLowerCase().endsWith(ext));
  },

  // Export selected photos as ZIP
  exportPhotos: async (paths: string[]) => {
    const res = await axios.post(`${API_BASE}/export`, { paths }, {
      responseType: 'blob'
    });
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
    const res = await axios.get(`${API_BASE}/pricing`);
    return res.data as PricingTier[];
  },
  
  getPricingTier: async (tierName: string) => {
    const res = await axios.get(`${API_BASE}/pricing/${tierName}`);
    return res.data as PricingTier;
  },
  
  recommendPricingTier: async (imageCount: number) => {
    const res = await axios.get(`${API_BASE}/pricing/recommend?image_count=${imageCount}`);
    return res.data as PricingTier;
  },
  
  getUsageStats: async (userId: string) => {
    const res = await axios.get(`${API_BASE}/usage/${userId}`);
    return res.data as UsageStats;
  },
  
  checkUsageLimit: async (userId: string, additionalImages: number = 0) => {
    const res = await axios.get(`${API_BASE}/usage/check/${userId}?additional_images=${additionalImages}`);
    return res.data;
  },
  
  upgradeUserTier: async (userId: string, newTier: string) => {
    const res = await axios.post(`${API_BASE}/usage/upgrade/${userId}`, { new_tier: newTier });
    return res.data;
  }
};
