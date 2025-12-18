/**
 * Performance Dashboard Page
 * 
 * Displays cache statistics, API schema, and performance metrics
 */

import { useState, useEffect } from 'react';
import { api } from '../api';

interface CacheStats {
  memory: {
    total_entries: number;
    valid_entries: number;
    expired_entries: number;
    max_size: number;
    total_accesses: number;
    utilization_percent: number;
  };
  disk: {
    total_entries: number;
    valid_entries: number;
    expired_entries: number;
    total_accesses: number;
  };
  operation_stats: {
    hits: number;
    misses: number;
    sets: number;
    deletes: number;
  };
  hit_rate: number;
  hit_count: number;
  miss_count: number;
}

interface ApiEndpoint {
  path: string;
  method: string;
  summary: string;
  description: string;
}

interface ApiSchema {
  version: string;
  endpoints: ApiEndpoint[];
}

const PerformanceDashboard = () => {
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [apiSchema, setApiSchema] = useState<ApiSchema | null>(null);
  const [loading, setLoading] = useState({
    cache: false,
    schema: false,
  });
  const [error, setError] = useState<string | null>(null);

  const loadCacheStats = async () => {
    setLoading(prev => ({ ...prev, cache: true }));
    try {
      const data = await api.getCacheStats();
      setCacheStats(data);
      setError(null);
    } catch (err) {
      setError('Failed to load cache statistics');
      console.error(err);
    } finally {
      setLoading(prev => ({ ...prev, cache: false }));
    }
  };

  const loadApiSchema = async () => {
    setLoading(prev => ({ ...prev, schema: true }));
    try {
      const data = await api.getApiSchema();
      setApiSchema(data);
      setError(null);
    } catch (err) {
      setError('Failed to load API schema');
      console.error(err);
    } finally {
      setLoading(prev => ({ ...prev, schema: false }));
    }
  };

  // Load initial data
  useEffect(() => {
    loadCacheStats();
    loadApiSchema();
  }, []);

  const clearCache = async () => {
    try {
      await api.clearCache();
      // Reload stats after clearing
      loadCacheStats();
    } catch (err) {
      setError('Failed to clear cache');
      console.error(err);
    }
  };

  const testLogging = async () => {
    try {
      await api.testLogging();
      setError(null); // Clear any previous errors
    } catch (err) {
      setError('Failed to test logging');
      console.error(err);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8 text-center">Performance Dashboard</h1>
      
      {error && (
        <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          Error: {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Cache Statistics Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Cache Statistics</h2>
            <button
              onClick={clearCache}
              disabled={loading.cache}
              className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
            >
              {loading.cache ? 'Clearing...' : 'Clear Cache'}
            </button>
          </div>
          
          {cacheStats ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-100 dark:bg-gray-700 p-4 rounded">
                  <h3 className="font-medium mb-2">Memory Cache</h3>
                  <div className="text-sm space-y-1">
                    <p>Valid Entries: {cacheStats.memory.valid_entries}</p>
                    <p>Expired Entries: {cacheStats.memory.expired_entries}</p>
                    <p>Total Entries: {cacheStats.memory.total_entries}</p>
                    <p>Utilization: {cacheStats.memory.utilization_percent.toFixed(2)}%</p>
                  </div>
                </div>
                
                <div className="bg-gray-100 dark:bg-gray-700 p-4 rounded">
                  <h3 className="font-medium mb-2">Disk Cache</h3>
                  <div className="text-sm space-y-1">
                    <p>Valid Entries: {cacheStats.disk.valid_entries}</p>
                    <p>Expired Entries: {cacheStats.disk.expired_entries}</p>
                    <p>Total Entries: {cacheStats.disk.total_entries}</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-gray-100 dark:bg-gray-700 p-4 rounded">
                <h3 className="font-medium mb-2">Performance</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p>Hit Rate: {(cacheStats.hit_rate * 100).toFixed(2)}%</p>
                    <p>Total Hits: {cacheStats.hit_count}</p>
                    <p>Total Misses: {cacheStats.miss_count}</p>
                  </div>
                  <div>
                    <p>Sets: {cacheStats.operation_stats.sets}</p>
                    <p>Deletes: {cacheStats.operation_stats.deletes}</p>
                    <p>Total Accesses: {cacheStats.memory.total_accesses}</p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 dark:text-gray-400">Loading cache statistics...</p>
          )}
          
          <button
            onClick={loadCacheStats}
            disabled={loading.cache}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {loading.cache ? 'Loading...' : 'Refresh Cache Stats'}
          </button>
        </div>

        {/* API Schema Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">API Schema</h2>
            <button
              onClick={loadApiSchema}
              disabled={loading.schema}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
            >
              {loading.schema ? 'Loading...' : 'Refresh Schema'}
            </button>
          </div>
          
          {apiSchema ? (
            <div>
              <div className="mb-4 p-3 bg-blue-100 dark:bg-blue-900 rounded">
                <p className="font-medium">Version: {apiSchema.version}</p>
                <p>Endpoints: {apiSchema.endpoints.length}</p>
              </div>
              
              <div className="max-h-96 overflow-y-auto">
                {apiSchema.endpoints.map((endpoint, index) => (
                  <div 
                    key={index} 
                    className="mb-3 p-3 bg-gray-50 dark:bg-gray-700 rounded border-l-4 border-blue-500"
                  >
                    <div className="flex items-center">
                      <span className={`px-2 py-1 rounded text-xs font-medium mr-2 ${
                        endpoint.method === 'GET' ? 'bg-green-100 text-green-800' :
                        endpoint.method === 'POST' ? 'bg-blue-100 text-blue-800' :
                        endpoint.method === 'PUT' ? 'bg-yellow-100 text-yellow-800' :
                        endpoint.method === 'DELETE' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {endpoint.method}
                      </span>
                      <code className="text-sm font-mono">{endpoint.path}</code>
                    </div>
                    <p className="mt-2 text-sm">{endpoint.summary}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-gray-500 dark:text-gray-400">Loading API schema...</p>
          )}
        </div>

        {/* Logging Test Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 lg:col-span-2">
          <h2 className="text-xl font-semibold mb-4">Logging Test</h2>
          
          <div className="flex flex-col sm:flex-row gap-4">
            <button
              onClick={testLogging}
              className="px-6 py-3 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
            >
              Test Logging
            </button>
            
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-2 sm:mt-0 sm:ml-auto">
              Send a test log message to verify logging functionality
            </p>
          </div>
          
          <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded">
            <h3 className="font-medium mb-2">Logging Information</h3>
            <p className="text-sm">
              The logging system captures structured information about search operations,
              performance metrics, and system events. Logs are stored in JSON format
              for easy parsing and analysis.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PerformanceDashboard;