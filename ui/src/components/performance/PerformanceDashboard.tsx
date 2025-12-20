/**
 * Performance Optimization & Caching Dashboard
 *
 * Provides insights and controls for the caching and performance optimization system.
 */
import React, { useState, useEffect } from 'react';
import {
  Activity,
  HardDrive,
  Zap,
  Clock,
  Trash2,
  RefreshCw,
  BarChart3,
  Database,
  Cpu
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface CacheStats {
  thumbnail_cache: {
    size: number;
    max_size: number;
    ttl: number;
  };
  search_results_cache: {
    size: number;
    max_size: number;
    ttl: number;
  };
  metadata_cache: {
    size: number;
    max_size: number;
    ttl: number;
  };
  embeddings_cache: {
    size: number;
    max_size: number;
    ttl: number;
  };
}

interface CacheHealth {
  status: string;
  caches: string[];
  total_entries: number;
  timestamp: string;
}

export function PerformanceDashboard() {
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [health, setHealth] = useState<CacheHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cacheClearing, setCacheClearing] = useState(false);
  const [cacheType, setCacheType] = useState<string>('all');

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Load cache statistics
      const statsResponse = await api.get('/cache/stats');
      setCacheStats(statsResponse.stats);
      
      // Load health check
      const healthResponse = await api.get('/cache/health');
      setHealth(healthResponse);
    } catch (err) {
      console.error('Failed to load performance stats:', err);
      setError('Failed to load performance statistics');
    } finally {
      setLoading(false);
    }
  };

  const clearCache = async () => {
    setCacheClearing(true);
    try {
      await api.post('/cache/clear', {}, {
        params: { cache_type: cacheType === 'all' ? null : cacheType }
      });
      loadStats(); // Reload stats after clearing
    } catch (err) {
      console.error('Failed to clear cache:', err);
      setError('Failed to clear cache');
    } finally {
      setCacheClearing(false);
    }
  };

  const getCachePercentage = (size: number, maxSize: number): number => {
    return Math.min(100, Math.round((size / maxSize) * 100));
  };

  if (loading) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-6`}>
        <div className="flex items-center justify-center h-32">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-6`}>
        <div className="text-destructive">{error}</div>
      </div>
    );
  }

  if (!cacheStats || !health) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-6`}>
        <div className="text-muted-foreground">No cache data available</div>
      </div>
    );
  }

  // Calculate total cache usage
  const totalUsed = Object.values(cacheStats).reduce((sum, cache) => sum + cache.size, 0);
  const totalMaxCapacity = Object.values(cacheStats).reduce((sum, cache) => sum + cache.max_size, 0);
  const totalUsagePercentage = Math.round((totalUsed / totalMaxCapacity) * 100);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-foreground">Performance & Caching</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={loadStats}
            className="btn-glass btn-glass--muted px-3 py-2 flex items-center gap-2"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </div>

      {/* Health Summary */}
      <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}>
        <div className="flex items-center gap-3 mb-4">
          <Activity className={`w-8 h-8 ${health.status === 'healthy' ? 'text-green-400' : 'text-yellow-400'}`} />
          <div>
            <h3 className="font-medium text-foreground">System Health</h3>
            <p className="text-sm text-muted-foreground">
              {health.status.charAt(0).toUpperCase() + health.status.slice(1)} - {health.total_entries} entries
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <Cpu size={16} className="text-muted-foreground" />
            <span>Total Entries: {health.total_entries}</span>
          </div>
          <div className="flex items-center gap-2">
            <Clock size={16} className="text-muted-foreground" />
            <span>Updated: {new Date(health.timestamp).toLocaleTimeString()}</span>
          </div>
        </div>
      </div>

      {/* Total Cache Usage */}
      <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium text-foreground flex items-center gap-2">
            <BarChart3 size={16} />
            Total Cache Usage
          </h3>
          <span className="text-sm font-medium">{totalUsed} / {totalMaxCapacity} ({totalUsagePercentage}%)</span>
        </div>
        <div className="w-full bg-white/10 rounded-full h-3">
          <div 
            className={`h-3 rounded-full ${
              totalUsagePercentage < 70 ? 'bg-green-500' : 
              totalUsagePercentage < 90 ? 'bg-yellow-500' : 'bg-red-500'
            }`}
            style={{ width: `${totalUsagePercentage}%` }}
          />
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          Total cached items across all systems
        </p>
      </div>

      {/* Individual Cache Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Object.entries(cacheStats).map(([cacheName, cacheData]) => {
          const percentage = getCachePercentage(cacheData.size, cacheData.max_size);
          const displayName = cacheName
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());

          // Get appropriate icon based on cache type
          const getIcon = () => {
            if (cacheName.includes('thumbnail')) return <HardDrive size={20} />;
            if (cacheName.includes('search')) return <Zap size={20} />;
            if (cacheName.includes('meta')) return <Database size={20} />;
            if (cacheName.includes('embed')) return <Activity size={20} />;
            return <BarChart3 size={20} />;
          };

          return (
            <div 
              key={cacheName} 
              className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 text-foreground">
                  {getIcon()}
                  <h4 className="font-medium text-sm">{displayName}</h4>
                </div>
                <span className="text-xs font-medium">{percentage}%</span>
              </div>
              
              <div className="mb-2">
                <div className="w-full bg-white/10 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${
                      percentage < 70 ? 'bg-green-500' : 
                      percentage < 90 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
              
              <div className="text-xs text-muted-foreground space-y-1">
                <div className="flex justify-between">
                  <span>Entries:</span>
                  <span>{cacheData.size}</span>
                </div>
                <div className="flex justify-between">
                  <span>Max:</span>
                  <span>{cacheData.max_size}</span>
                </div>
                <div className="flex justify-between">
                  <span>TTL (s):</span>
                  <span>{cacheData.ttl}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Cache Management */}
      <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}>
        <h3 className="font-medium text-foreground mb-4 flex items-center gap-2">
          <Trash2 size={16} />
          Cache Management
        </h3>
        
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
          <div className="flex-1">
            <label className="block text-sm font-medium text-foreground mb-2">
              Select cache to clear
            </label>
            <select
              value={cacheType}
              onChange={(e) => setCacheType(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="all">All Caches</option>
              <option value="thumbnail">Thumbnail Cache</option>
              <option value="search">Search Results Cache</option>
              <option value="metadata">Metadata Cache</option>
              <option value="embeddings">Embeddings Cache</option>
            </select>
          </div>
          
          <button
            onClick={clearCache}
            disabled={cacheClearing}
            className={`btn-glass ${
              cacheClearing ? 'btn-glass--muted' : 'btn-glass--danger'
            } px-4 py-2 flex items-center gap-2 mt-6 sm:mt-0`}
          >
            {cacheClearing ? (
              <>
                <RefreshCw size={16} className="animate-spin" />
                Clearing...
              </>
            ) : (
              <>
                <Trash2 size={16} />
                Clear Cache
              </>
            )}
          </button>
        </div>
      </div>

      {/* Performance Tips */}
      <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}>
        <h3 className="font-medium text-foreground mb-3 flex items-center gap-2">
          <Zap size={16} />
          Performance Tips
        </h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 flex-shrink-0"></div>
            <span>Regularly clear caches to free up memory</span>
          </li>
          <li className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 flex-shrink-0"></div>
            <span>Increase TTL for frequently accessed data</span>
          </li>
          <li className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 flex-shrink-0"></div>
            <span>Monitor cache hit rates to optimize performance</span>
          </li>
          <li className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 flex-shrink-0"></div>
            <span>Consider increasing cache size for large libraries</span>
          </li>
        </ul>
      </div>
    </div>
  );
}