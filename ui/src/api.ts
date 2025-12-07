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

export const api = {
  scan: async (path: string) => {
    const res = await axios.post(`${API_BASE}/scan`, { path });
    return res.data;
  },
  
  search: async (query: string) => {
    const res = await axios.get(`${API_BASE}/search`, { params: { query } });
    return res.data;
  },
  
  getTimeline: async () => {
    const res = await axios.get(`${API_BASE}/timeline`);
    return res.data.timeline as TimelineData[];
  },
  
  getImageUrl: (path: string, size?: number) => {
    const encodedPath = encodeURIComponent(path);
    return `${API_BASE}/image/thumbnail?path=${encodedPath}${size ? `&size=${size}` : ''}`;
  }
};
