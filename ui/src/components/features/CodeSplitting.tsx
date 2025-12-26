/**
 * Code Splitting Component
 *
 * Manages code splitting configuration and performance tracking
 */

import { useState, useEffect } from 'react';
import './CodeSplitting.css';

const CodeSplitting = () => {
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);
  const [enabled, setEnabled] = useState<boolean>(false);
  interface PerformanceStats {
    total_loads?: number;
    avg_load_time?: number;
    avg_size?: number;
    component_count?: number;
  }

  interface ChunkStats {
    load_count?: number;
    avg_load_time?: number;
    avg_size?: number;
    max_load_time?: number;
  }

  const [performanceStats, setPerformanceStats] =
    useState<PerformanceStats | null>(null);
  const [chunkPerformance, setChunkPerformance] = useState<Record<
    string,
    ChunkStats
  > | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);
  const [newChunk, setNewChunk] = useState<{
    name: string;
    config: string;
  }>({
    name: '',
    config: '{"lazy": true, "preload": false}',
  });

  // Fetch code splitting configuration
  const fetchConfig = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get main config
      const configResponse = await fetch('/api/code-splitting/config');
      if (configResponse.ok) {
        const configData = await configResponse.json();
        setConfig(configData.config);
      }

      // Get enabled status
      const enabledResponse = await fetch('/api/code-splitting/enabled');
      if (enabledResponse.ok) {
        const enabledData = await enabledResponse.json();
        setEnabled(enabledData.enabled);
      }

      // Get performance stats
      const performanceResponse = await fetch(
        '/api/code-splitting/performance'
      );
      if (performanceResponse.ok) {
        const performanceData = await performanceResponse.json();
        setPerformanceStats(performanceData.stats);
      }

      // Get chunk performance
      const chunkResponse = await fetch(
        '/api/code-splitting/performance/chunks'
      );
      if (chunkResponse.ok) {
        const chunkData = await chunkResponse.json();
        setChunkPerformance(chunkData.stats);
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      console.error('Error fetching code splitting config:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  // Toggle code splitting
  const toggleCodeSplitting = async () => {
    try {
      const response = await fetch('/api/code-splitting/enabled', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(!enabled),
      });

      if (!response.ok) {
        throw new Error('Failed to update code splitting status');
      }

      setEnabled(!enabled);
    } catch (err) {
      setError(new Error(err instanceof Error ? err.message : 'Unknown error'));
      console.error('Error toggling code splitting:', err);
    }
  };

  // Add or update chunk configuration
  const saveChunkConfig = async () => {
    if (!newChunk.name.trim()) return;

    try {
      let configObj;
      try {
        configObj = JSON.parse(newChunk.config);
      } catch (err) {
        setError(new Error('Invalid JSON configuration'));
        console.debug('JSON parse error in chunk config', err);
        return;
      }

      const response = await fetch(
        `/api/code-splitting/chunk/${newChunk.name}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            chunk_name: newChunk.name,
            config: configObj,
          }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to save chunk configuration');
      }

      // Reset form and refresh
      setNewChunk({
        name: '',
        config: '{"lazy": true, "preload": false}',
      });
      fetchConfig();
    } catch (err) {
      setError(new Error(err instanceof Error ? err.message : 'Unknown error'));
      console.error('Error saving chunk config:', err);
    }
  };

  // Record performance data (simulated)
  const recordPerformance = async () => {
    try {
      const response = await fetch('/api/code-splitting/performance', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          component_name: 'test-component',
          chunk_name: 'test-chunk',
          load_time_ms: Math.random() * 1000,
          size_kb: Math.random() * 500,
          timestamp: new Date().toISOString(),
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to record performance');
      }

      fetchConfig();
    } catch (err) {
      setError(new Error(err instanceof Error ? err.message : 'Unknown error'));
      console.error('Error recording performance:', err);
    }
  };

  if (loading) {
    return (
      <div className='loading'>Loading code splitting configuration...</div>
    );
  }

  if (error) {
    return <div className='error'>Error: {error.message}</div>;
  }

  return (
    <div className='code-splitting'>
      <div className='header'>
        <h2>Code Splitting Configuration</h2>
        <div className='controls'>
          <button onClick={fetchConfig} className='refresh-btn'>
            Refresh
          </button>
        </div>
      </div>

      <div className='main-controls'>
        <div className='control-item'>
          <span className='control-label'>Code Splitting Enabled:</span>
          <label className='toggle-switch'>
            <input
              type='checkbox'
              checked={enabled}
              onChange={toggleCodeSplitting}
              aria-label='Toggle code splitting'
              title='Toggle code splitting'
            />
            <span className='toggle-slider'></span>
          </label>
        </div>

        <button onClick={recordPerformance} className='record-btn'>
          Record Test Performance
        </button>
      </div>

      {config && (
        <div className='config-section'>
          <h3>Current Configuration</h3>
          <pre className='config-json'>{JSON.stringify(config, null, 2)}</pre>
        </div>
      )}

      <div className='chunk-config'>
        <h3>Chunk Configuration</h3>
        <div className='chunk-form'>
          <div className='form-group'>
            <label htmlFor='chunk-name-input'>Chunk Name:</label>
            <input
              id='chunk-name-input'
              type='text'
              value={newChunk.name}
              onChange={(e) =>
                setNewChunk({ ...newChunk, name: e.target.value })
              }
              placeholder='e.g., photo-grid, face-clustering'
              aria-label='Chunk name'
              title='Chunk name'
            />
          </div>

          <div className='form-group'>
            <label htmlFor='chunk-config-textarea'>Configuration (JSON):</label>
            <textarea
              id='chunk-config-textarea'
              value={newChunk.config}
              onChange={(e) =>
                setNewChunk({ ...newChunk, config: e.target.value })
              }
              placeholder='{"lazy": true, "preload": false, "priority": "medium"}'
              aria-label='Chunk configuration JSON'
              title='Chunk configuration JSON'
            />
          </div>

          <button onClick={saveChunkConfig} className='save-btn'>
            Save Chunk Configuration
          </button>
        </div>
      </div>

      {performanceStats && (
        <div className='performance-section'>
          <h3>Performance Statistics</h3>
          <div className='stats-grid'>
            <div className='stat-card'>
              <span className='stat-label'>Total Loads:</span>
              <span className='stat-value'>
                {performanceStats.total_loads || 0}
              </span>
            </div>
            <div className='stat-card'>
              <span className='stat-label'>Avg Load Time:</span>
              <span className='stat-value'>
                {performanceStats.avg_load_time
                  ? `${performanceStats.avg_load_time.toFixed(2)}ms`
                  : 'N/A'}
              </span>
            </div>
            <div className='stat-card'>
              <span className='stat-label'>Avg Size:</span>
              <span className='stat-value'>
                {performanceStats.avg_size
                  ? `${performanceStats.avg_size.toFixed(2)}KB`
                  : 'N/A'}
              </span>
            </div>
            <div className='stat-card'>
              <span className='stat-label'>Components:</span>
              <span className='stat-value'>
                {performanceStats.component_count || 0}
              </span>
            </div>
          </div>
        </div>
      )}

      {chunkPerformance && (
        <div className='chunk-performance'>
          <h3>Chunk Performance</h3>
          <div className='chunk-list'>
            {Object.entries(chunkPerformance).map(([chunkName, stats]) => (
              <div key={chunkName} className='chunk-item'>
                <div className='chunk-header'>
                  <h4>{chunkName}</h4>
                  <span className='chunk-loads'>{stats.load_count} loads</span>
                </div>
                <div className='chunk-stats'>
                  <div className='stat'>
                    <span className='stat-label'>Avg Time:</span>
                    <span className='stat-value'>
                      {stats.avg_load_time !== undefined
                        ? `${stats.avg_load_time.toFixed(2)}ms`
                        : 'N/A'}
                    </span>
                  </div>
                  <div className='stat'>
                    <span className='stat-label'>Avg Size:</span>
                    <span className='stat-value'>
                      {stats.avg_size !== undefined
                        ? `${stats.avg_size.toFixed(2)}KB`
                        : 'N/A'}
                    </span>
                  </div>
                  <div className='stat'>
                    <span className='stat-label'>Max Time:</span>
                    <span className='stat-value'>
                      {stats.max_load_time !== undefined
                        ? `${stats.max_load_time.toFixed(2)}ms`
                        : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className='integration-guide'>
        <h3>Frontend Integration Guide</h3>
        <div className='guide-content'>
          <p>To integrate code splitting in your React frontend:</p>
          <ol>
            <li>
              Use <code>React.lazy()</code> for lazy loading components
            </li>
            <li>Configure chunk names in your build system</li>
            <li>Use the performance tracking API to monitor load times</li>
            <li>Adjust chunk configurations based on performance data</li>
          </ol>

          <div className='code-example'>
            <pre>{`// Example: Lazy loading a component
const PhotoGrid = React.lazy(() =>
  import(/* webpackChunkName: "photo-grid" */ './PhotoGrid')
);

// Example: Recording performance
const startTime = performance.now();
const component = await import('./MyComponent');
const endTime = performance.now();

fetch('/api/code-splitting/performance', {
  method: 'POST',
  body: JSON.stringify({
    component_name: 'MyComponent',
    chunk_name: 'my-component-chunk',
    load_time_ms: endTime - startTime,
    size_kb: 150 // Approximate size
  })
});`}</pre>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CodeSplitting;
