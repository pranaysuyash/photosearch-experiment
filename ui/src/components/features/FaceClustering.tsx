/**
 * Face Clustering Component
 *
 * Displays face clusters and allows management of face groups
 */

import React, { useState, useEffect } from 'react';
import './FaceClustering.css';

interface ClusterImage {
  path: string;
  filename?: string;
}

interface Cluster {
  id: string;
  label?: string;
  face_count: number;
  image_count: number;
  created_at?: string;
  images?: ClusterImage[];
}

interface FaceStats {
  total_clusters: number;
  total_faces: number;
  avg_cluster_size?: number;
}

const FaceClustering: React.FC = () => {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<Cluster | null>(null);
  const [editingLabel, setEditingLabel] = useState<boolean>(false);
  const [newLabel, setNewLabel] = useState<string>('');
  const [stats, setStats] = useState<FaceStats | null>(null);
  const [isClustering, setIsClustering] = useState<boolean>(false);

  // Fetch all clusters on mount
  const fetchClusters = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/faces/clusters');
      if (!response.ok) {
        throw new Error('Failed to fetch face clusters');
      }

      const data = await response.json();
      setClusters(data.clusters || []);

      // Fetch statistics
      const statsResponse = await fetch('/api/faces/stats');
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData.stats);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error fetching face clusters:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClusters();
  }, []);

  // Start clustering process
  const startClustering = async () => {
    try {
      setIsClustering(true);
      setError(null);

      // In a real app, you would get the list of images to cluster
      // For now, we'll cluster all images
      const response = await fetch('/api/faces/cluster', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image_paths: [], // Empty means cluster all
          eps: 0.6,
          min_samples: 2,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start clustering');
      }

      const result = await response.json();
      console.log('Clustering result:', result);

      // Refresh clusters
      fetchClusters();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error during clustering:', err);
    } finally {
      setIsClustering(false);
    }
  };

  // Update cluster label
  const updateLabel = async () => {
    if (!selectedCluster || !newLabel.trim()) return;

    try {
      const response = await fetch(
        `/api/faces/clusters/${selectedCluster.id}/label`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            label: newLabel.trim(),
          }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to update label');
      }

      // Refresh clusters
      fetchClusters();
      setEditingLabel(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error updating label:', err);
    }
  };

  // Delete cluster
  const deleteCluster = async (clusterId: string) => {
    if (window.confirm('Are you sure you want to delete this cluster?')) {
      try {
        const response = await fetch(`/api/faces/clusters/${clusterId}`, {
          method: 'DELETE',
        });

        if (!response.ok) {
          throw new Error('Failed to delete cluster');
        }

        // Refresh clusters
        fetchClusters();
        setSelectedCluster(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        console.error('Error deleting cluster:', err);
      }
    }
  };

  // Get color index for cluster based on ID (maps to CSS classes)
  const getClusterColorIndex = (clusterId: string) => {
    const colors = [
      '#3498db',
      '#2ecc71',
      '#e74c3c',
      '#f39c12',
      '#9b59b6',
      '#1abc9c',
      '#e91e63',
      '#00bcd4',
      '#ff9800',
      '#607d8b',
    ];
    const numericId = parseInt(clusterId, 10) || 0;
    return numericId % colors.length;
  };

  if (loading) {
    return <div className='loading'>Loading face clusters...</div>;
  }

  if (error) {
    return <div className='error'>Error: {error}</div>;
  }

  return (
    <div className='face-clustering'>
      <div className='header'>
        <h2>Face Clustering</h2>
        <div className='controls'>
          <button
            onClick={startClustering}
            disabled={isClustering}
            className='cluster-btn'
          >
            {isClustering ? 'Clustering...' : 'Cluster Faces'}
          </button>
          <button onClick={fetchClusters} className='refresh-btn'>
            Refresh
          </button>
        </div>
      </div>

      {stats && (
        <div className='stats'>
          <div className='stat-item'>
            <span className='stat-label'>Total Clusters:</span>
            <span className='stat-value'>{stats.total_clusters}</span>
          </div>
          <div className='stat-item'>
            <span className='stat-label'>Total Faces:</span>
            <span className='stat-value'>{stats.total_faces}</span>
          </div>
          <div className='stat-item'>
            <span className='stat-label'>Avg Cluster Size:</span>
            <span className='stat-value'>
              {stats.avg_cluster_size?.toFixed(1)}
            </span>
          </div>
        </div>
      )}

      {clusters.length === 0 ? (
        <div className='empty-state'>
          <p>No face clusters found.</p>
          <p>Click "Cluster Faces" to analyze your photos for faces.</p>
        </div>
      ) : (
        <div className='clusters-container'>
          <div className='clusters-list'>
            {clusters.map((cluster) => (
              <div
                key={cluster.id}
                className={`cluster-item ${
                  selectedCluster?.id === cluster.id ? 'selected' : ''
                }`}
                onClick={() => setSelectedCluster(cluster)}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    setSelectedCluster(cluster);
                  }
                }}
              >
                <div
                  className={`cluster-color cluster-color-${getClusterColorIndex(
                    cluster.id
                  )}`}
                  aria-hidden='true'
                  title={cluster.label || `Cluster ${cluster.id}`}
                ></div>
                <div className='cluster-info'>
                  <h3>{cluster.label || `Cluster ${cluster.id}`}</h3>
                  <p>
                    {cluster.face_count} faces in {cluster.image_count} images
                  </p>
                </div>
                <div className='cluster-actions'>
                  <button
                    className='edit-btn'
                    title={`Edit cluster ${cluster.label || cluster.id}`}
                    aria-label={`Edit cluster ${cluster.label || cluster.id}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedCluster(cluster);
                      setEditingLabel(true);
                      setNewLabel(cluster.label || '');
                    }}
                  >
                    Edit
                  </button>
                  <button
                    className='delete-btn'
                    title={`Delete cluster ${cluster.label || cluster.id}`}
                    aria-label={`Delete cluster ${cluster.label || cluster.id}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteCluster(cluster.id);
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>

          {selectedCluster && (
            <div className='cluster-detail'>
              <div className='detail-header'>
                <h3>
                  {selectedCluster.label || `Cluster ${selectedCluster.id}`}
                </h3>
                <div
                  className={`detail-color cluster-color-${getClusterColorIndex(
                    selectedCluster.id
                  )}`}
                  aria-hidden='true'
                  title={
                    selectedCluster.label || `Cluster ${selectedCluster.id}`
                  }
                ></div>
              </div>

              {editingLabel ? (
                <div className='edit-label'>
                  <input
                    type='text'
                    value={newLabel}
                    onChange={(e) => setNewLabel(e.target.value)}
                    placeholder='Enter cluster label'
                  />
                  <div className='edit-actions'>
                    <button onClick={updateLabel} className='save-btn'>
                      Save
                    </button>
                    <button
                      onClick={() => setEditingLabel(false)}
                      className='cancel-btn'
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className='detail-stats'>
                  <div className='stat'>
                    <span className='stat-label'>Faces:</span>
                    <span className='stat-value'>
                      {selectedCluster.face_count}
                    </span>
                  </div>
                  <div className='stat'>
                    <span className='stat-label'>Images:</span>
                    <span className='stat-value'>
                      {selectedCluster.image_count}
                    </span>
                  </div>
                  <div className='stat'>
                    <span className='stat-label'>Created:</span>
                    <span className='stat-value'>
                      {selectedCluster.created_at
                        ? new Date(selectedCluster.created_at).toLocaleString()
                        : ''}
                    </span>
                  </div>
                </div>
              )}

              <div className='detail-images'>
                <h4>Images in this cluster:</h4>
                <div className='image-grid'>
                  {selectedCluster.images?.map(
                    (image: ClusterImage, index: number) => (
                      <div key={index} className='image-item'>
                        <img
                          src={`/api/image/thumbnail?path=${encodeURIComponent(
                            image.path
                          )}&size=150`}
                          alt={`Face cluster ${index + 1}`}
                          onError={(
                            e: React.SyntheticEvent<HTMLImageElement>
                          ) => {
                            (e.target as HTMLImageElement).src =
                              '/placeholder-face.jpg';
                            (e.target as HTMLImageElement).onerror = null;
                          }}
                        />
                        <p className='image-name'>{image.filename}</p>
                      </div>
                    )
                  ) || <p>No images available for this cluster.</p>}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FaceClustering;
