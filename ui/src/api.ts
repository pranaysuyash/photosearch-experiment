import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

export const api = {
  scan: async (path: string, background: boolean = true) => {
    const res = await axios.post(`${API_BASE}/scan`, { path, background });
    return res.data; // Returns { job_id, status } if background=true
  },

  getJobStatus: async (jobId: string) => {
    const res = await axios.get(`${API_BASE}/jobs/${jobId}`);
    return res.data as Job;
  },
  
  search: async (query: string, mode: string = 'metadata', limit: number = 50) => {
    const res = await axios.get(`${API_BASE}/search`, { 
      params: { query, mode, limit } 
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

  // Get video URL for direct serving
  getVideoUrl: (path: string) => {
    const encodedPath = encodeURIComponent(path);
    return `${API_BASE}/video?path=${encodedPath}`;
  }
};
