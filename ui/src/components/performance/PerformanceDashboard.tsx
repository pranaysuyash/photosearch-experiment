/**
 * Performance Dashboard Component - Phase 8
 *
 * Real-time performance monitoring and system optimization interface.
 * Provides comprehensive performance metrics, system health monitoring,
 * and optimization controls for the face recognition system.
 *
 * Features:
 * - Real-time performance metrics visualization
 * - Memory usage monitoring with trend analysis
 * - Cache performance statistics and management
 * - Database optimization controls
 * - System health indicators and recommendations
 * - Resource cleanup and optimization tools
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  Database,
  HardDrive,
  Zap,
  TrendingUp,
  Settings,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  Gauge
} from 'lucide-react';

interface PerformanceMetrics {
  performance_summary: {
    total_operations: number;
    successful_operations: number;
    failed_operations: number;
    avg_processing_time: number;
    avg_memory_delta_mb: number;
    total_items_processed: number;
    cache_hit_rate: number;
  };
  current_system_state: {
    memory_usage: {
      rss_mb: number;
      percent: number;
      available_mb: number;
    };
    memory_trend: {
      trend: string;
      avg_memory_mb: number;
      max_memory_mb: number;
      current_memory_mb: number;
    };
    cache_stats: {
      hit_rate: number;
      total_requests: number;
      cache_size_mb: number;
      entries: number;
      hits: number;
      misses: number;
      evictions: number;
    };
    optimization_stats: {
      cache_enabled: boolean;
      concurrent_processing: boolean;
      memory_monitoring: boolean;
      database_optimized: boolean;
    };
  };
  recommendations: string[];
}

interface SystemHealth {
  overall_health: 'healthy' | 'warning' | 'critical';
  memory_health: {
    status: 'healthy' | 'warning' | 'critical';
    usage_percent: number;
    usage_mb: number;
  };
  cache_health: {
    status: 'healthy' | 'warning' | 'critical';
    enabled: boolean;
    stats: Record<string, unknown>;
  };
  optimization_status: Record<string, unknown>;
  recommendations: string[];
}

export const PerformanceDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const refreshInterval = 5000; // 5 seconds

  // Fetch performance metrics
  const fetchMetrics = useCallback(async () => {
    try {
      const response = await fetch('/api/performance/status');
      if (response.ok) {
        const data = await response.json();
        setMetrics(data.performance_report);
      }
    } catch (error) {
      console.error('Failed to fetch performance metrics:', error);
    }
  }, []);

  // Fetch system health
  const fetchHealth = useCallback(async () => {
    try {
      const response = await fetch('/api/performance/health');
      if (response.ok) {
        const data = await response.json();
        setHealth(data.health_check);
      }
    } catch (error) {
      console.error('Failed to fetch system health:', error);
    }
  }, []);

  // Refresh all data
  const refreshData = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchMetrics(), fetchHealth()]);
    setLoading(false);
  }, [fetchMetrics, fetchHealth]);

  // Optimize system
  const optimizeSystem = async () => {
    setOptimizing(true);
    try {
      const response = await fetch('/api/performance/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enable_caching: true,
          cache_size_mb: 512,
          max_concurrent_threads: 4,
          batch_size: 32,
          memory_limit_mb: 2048,
          enable_gpu_acceleration: true,
          enable_query_optimization: true
        })
      });

      if (response.ok) {
        await refreshData();
      }
    } catch (error) {
      console.error('System optimization failed:', error);
    } finally {
      setOptimizing(false);
    }
  };

  // Clear cache
  const clearCache = async () => {
    const confirmed = window.confirm(
      'Clear the server-side cache? Cached thumbnails and computed results will be rebuilt on demand.'
    );
    if (!confirmed) return;
    try {
      const response = await fetch('/api/performance/cache/clear', {
        method: 'POST'
      });
      if (response.ok) {
        await refreshData();
      }
    } catch (error) {
      console.error('Cache clearing failed:', error);
    }
  };

  // Optimize memory
  const optimizeMemory = async () => {
    try {
      const response = await fetch('/api/performance/memory/optimize', {
        method: 'POST'
      });
      if (response.ok) {
        await refreshData();
      }
    } catch (error) {
      console.error('Memory optimization failed:', error);
    }
  };

  // Auto-refresh effect
  useEffect(() => {
    refreshData();
  }, [refreshData]);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(refreshData, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, refreshData]);

  // Health status color
  const getHealthColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600';
      case 'warning': return 'text-yellow-600';
      case 'critical': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  // Health status icon
  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="w-5 h-5" />;
      case 'warning': return <AlertTriangle className="w-5 h-5" />;
      case 'critical': return <AlertTriangle className="w-5 h-5" />;
      default: return <Activity className="w-5 h-5" />;
    }
  };

  if (loading && !metrics) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2">
          <RefreshCw className="w-5 h-5 animate-spin" />
          <span>Loading performance data…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Performance Dashboard</h2>
          <p className="text-gray-600">
            Real-time system performance monitoring and optimization
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm">Auto-refresh</span>
          </label>

          <button
            onClick={refreshData}
            disabled={loading}
            className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={optimizeSystem}
            disabled={optimizing}
            className="flex items-center space-x-2 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            <Zap className="w-4 h-4" />
            <span>{optimizing ? 'Optimizing…' : 'Optimize'}</span>
          </button>
        </div>
      </div>

      {/* System Health Overview */}
      {health && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 tabular-nums">
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">System Health</h3>
              <div className={`flex items-center space-x-2 ${getHealthColor(health.overall_health)}`}>
                {getHealthIcon(health.overall_health)}
                <span className="capitalize font-medium">{health.overall_health}</span>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Memory Health</span>
                <div className={`flex items-center space-x-1 ${getHealthColor(health.memory_health.status)}`}>
                  {getHealthIcon(health.memory_health.status)}
                  <span className="text-sm">{health.memory_health.usage_percent.toFixed(1)}%</span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Cache Health</span>
                <div className={`flex items-center space-x-1 ${getHealthColor(health.cache_health.status)}`}>
                  {getHealthIcon(health.cache_health.status)}
                  <span className="text-sm">{health.cache_health.enabled ? 'Enabled' : 'Disabled'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Memory Usage */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Memory Usage</h3>
              <HardDrive className="w-5 h-5 text-blue-600" />
            </div>

            {metrics && (
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Current Usage</span>
                    <span>{metrics.current_system_state.memory_usage.rss_mb.toFixed(1)} MB</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${Math.min(metrics.current_system_state.memory_usage.percent, 100)}%` }}
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Trend</span>
                  <div className="flex items-center space-x-1">
                    <TrendingUp className={`w-4 h-4 ${
                      metrics.current_system_state.memory_trend.trend === 'increasing' ? 'text-red-500' :
                      metrics.current_system_state.memory_trend.trend === 'decreasing' ? 'text-green-500' :
                      'text-gray-500'
                    }`} />
                    <span className="capitalize">{metrics.current_system_state.memory_trend.trend}</span>
                  </div>
                </div>

                <button
                  onClick={optimizeMemory}
                  className="w-full mt-3 px-3 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 text-sm"
                >
                  Optimize Memory
                </button>
              </div>
            )}
          </div>

          {/* Cache Performance */}
          <div className="bg-white rounded-lg shadow-sm border p-6 tabular-nums">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Cache Performance</h3>
              <Database className="w-5 h-5 text-green-600" />
            </div>

            {metrics && metrics.current_system_state.cache_stats && (
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Hit Rate</span>
                    <span>{(metrics.current_system_state.cache_stats.hit_rate * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-600 h-2 rounded-full"
                      style={{ width: `${metrics.current_system_state.cache_stats.hit_rate * 100}%` }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-600">Size</span>
                    <div className="font-medium">{metrics.current_system_state.cache_stats.cache_size_mb.toFixed(1)} MB</div>
                  </div>
                  <div>
                    <span className="text-gray-600">Entries</span>
                    <div className="font-medium">{metrics.current_system_state.cache_stats.entries}</div>
                  </div>
                </div>

                <button
                  onClick={clearCache}
                  className="w-full mt-3 px-3 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 text-sm"
                >
                  Clear Cache
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Performance Metrics */}
      {metrics && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 tabular-nums">
          {/* Processing Statistics */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Processing Statistics</h3>
              <BarChart3 className="w-5 h-5 text-purple-600" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">
                  {metrics.performance_summary.total_operations}
                </div>
                <div className="text-sm text-gray-600">Total Operations</div>
              </div>

              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {metrics.performance_summary.successful_operations}
                </div>
                <div className="text-sm text-gray-600">Successful</div>
              </div>

              <div className="text-center p-4 bg-yellow-50 rounded-lg">
                <div className="text-2xl font-bold text-yellow-600">
                  {metrics.performance_summary.avg_processing_time.toFixed(2)}s
                </div>
                <div className="text-sm text-gray-600">Avg Processing Time</div>
              </div>

              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">
                  {metrics.performance_summary.total_items_processed}
                </div>
                <div className="text-sm text-gray-600">Items Processed</div>
              </div>
            </div>
          </div>

          {/* Optimization Status */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Optimization Status</h3>
              <Settings className="w-5 h-5 text-gray-600" />
            </div>

            <div className="space-y-3">
              {Object.entries(metrics.current_system_state.optimization_stats).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 capitalize">
                    {key.replace(/_/g, ' ')}
                  </span>
                  <div className={`flex items-center space-x-2 ${value ? 'text-green-600' : 'text-gray-400'}`}>
                    {value ? <CheckCircle className="w-4 h-4" /> : <div className="w-4 h-4 rounded-full border-2 border-gray-300" />}
                    <span className="text-sm">{value ? 'Enabled' : 'Disabled'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Recommendations */}
      {metrics && metrics.recommendations && metrics.recommendations.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Gauge className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold">Performance Recommendations</h3>
          </div>

          <div className="space-y-2">
            {metrics.recommendations.map((recommendation, index) => (
              <div key={index} className="flex items-start space-x-3 p-3 bg-blue-50 rounded-lg">
                <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0" />
                <span className="text-sm text-blue-800">{recommendation}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
