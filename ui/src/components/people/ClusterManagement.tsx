/**
 * Cluster Management Component
 * 
 * Provides visual cluster organization and management interface
 * Allows users to view, edit, and organize face clusters
 */

import React, { useState, useEffect } from 'react';
import { User, Search, Edit, Trash2, Loader2, AlertTriangle, Check, X } from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';
import {
  type FaceCluster,
  type ClusteringResult,
  type ClusterQuality,
  type ClusterQualityResult,
  type MergeClustersResult
} from '../../api';

interface ClusterManagementProps {
  onClusterSelected?: (clusterId: string) => void;
  showControls?: boolean;
}

export function ClusterManagement({ onClusterSelected, showControls = true }: ClusterManagementProps) {
  const [clusters, setClusters] = useState<FaceCluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<FaceCluster | null>(null);
  const [qualityAnalysis, setQualityAnalysis] = useState<ClusterQualityResult | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [merging, setMerging] = useState(false);
  const [mergeTarget, setMergeTarget] = useState<string | null>(null);

  // Load clusters on mount
  useEffect(() => {
    const loadClusters = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Get all clusters
        const result = await api.getAllClusters();
        setClusters(result.clusters || []);
      } catch (err) {
        console.error('Failed to load clusters:', err);
        setError('Failed to load clusters');
      } finally {
        setLoading(false);
      }
    };

    loadClusters();
  }, []);

  // Analyze cluster quality when selected
  useEffect(() => {
    const analyzeQuality = async () => {
      if (!selectedCluster) {
        setQualityAnalysis(null);
        return;
      }

      try {
        const result = await api.getClusterQuality(selectedCluster.cluster_id);
        setQualityAnalysis(result);
      } catch (err) {
        console.error('Failed to analyze cluster quality:', err);
      }
    };

    analyzeQuality();
  }, [selectedCluster]);

  // Search clusters
  const searchClusters = () => {
    if (!searchQuery.trim()) {
      // Reset to show all clusters
      const loadAll = async () => {
        try {
          const result = await api.getAllClusters();
          setClusters(result.clusters || []);
        } catch (err) {
          console.error('Failed to load all clusters:', err);
        }
      };
      loadAll();
      return;
    }

    // Search by name
    const search = async () => {
      try {
        const result: any = await api.searchPeople(searchQuery);
        // Convert search results to cluster format
        const foundClusters = result.people.map((person: any) => ({
          cluster_id: person.cluster_id,
          label: person.label,
          face_count: person.face_count,
          detection_ids: []
        }));
        setClusters(foundClusters);
      } catch (err) {
        console.error('Search failed:', err);
      }
    };

    search();
  };

  // Merge clusters
  const mergeClusters = async () => {
    if (!selectedCluster || !mergeTarget) return;

    try {
      setMerging(true);
      const result: MergeClustersResult = await api.mergeClusters(
        selectedCluster.cluster_id,
        mergeTarget
      );
      
      if (result.success) {
        // Refresh clusters
        const updatedResult = await api.getAllClusters();
        setClusters(updatedResult.clusters || []);
        setSelectedCluster(null);
        setMergeTarget(null);
      }
    } catch (err) {
      console.error('Failed to merge clusters:', err);
      setError('Failed to merge clusters');
    } finally {
      setMerging(false);
    }
  };

  // Get quality rating color
  const getQualityColor = (rating: string) => {
    switch (rating) {
      case 'Excellent': return 'text-green-400';
      case 'Good': return 'text-blue-400';
      case 'Fair': return 'text-yellow-400';
      case 'Poor': return 'text-orange-400';
      case 'Low': return 'text-red-400';
      default: return 'text-muted-foreground';
    }
  };

  return (
    <div className="min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-foreground">Cluster Management</h1>
          {showControls && (
            <div className="flex gap-2">
              <button
                onClick={() => {
                  // Trigger automatic clustering
                  const cluster = async () => {
                    try {
                      setLoading(true);
                      const result: ClusteringResult = await api.clusterFaces(0.6, 2);
                      if (result.success) {
                        const updated = await api.getAllClusters();
                        setClusters(updated.clusters || []);
                      }
                    } catch (err) {
                      console.error('Clustering failed:', err);
                    } finally {
                      setLoading(false);
                    }
                  };
                  cluster();
                }}
                disabled={loading}
                className="btn-glass btn-glass--primary px-3 py-2 flex items-center gap-1"
              >
                <User size={16} />
                <span>Auto Cluster</span>
              </button>
            </div>
          )}
        </div>

        {/* Search */}
        <div className="mb-6">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Search clusters..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && searchClusters()}
              className="flex-1 px-4 py-2 bg-white/10 rounded-lg outline-none"
            />
            <button
              onClick={searchClusters}
              disabled={loading}
              className="btn-glass btn-glass--primary px-4 py-2"
            >
              <Search size={16} />
            </button>
          </div>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-2">
              <Loader2 className="animate-spin text-blue-400" size={20} />
              <span className="text-foreground">Loading clusters...</span>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <div className="text-red-400 p-4 bg-red-500/10 rounded-lg mb-4">
            {error}
          </div>
        )}

        {/* No clusters */}
        {!loading && clusters.length === 0 && (
          <div className="text-center py-20">
            <User className="mx-auto text-muted-foreground mb-4" size={48} />
            <h3 className="text-lg font-medium text-foreground mb-2">No Clusters Found</h3>
            <p className="text-muted-foreground">
              {searchQuery ? 'No clusters match your search' : 'No clusters have been created yet'}
            </p>
          </div>
        )}

        {/* Clusters grid */}
        {!loading && clusters.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {clusters.map((cluster) => (
              <div
                key={cluster.cluster_id}
                className={`${glass.surface} p-4 rounded-lg cursor-pointer hover:border-blue-400 transition-all ${
                  selectedCluster?.cluster_id === cluster.cluster_id ? 'border-2 border-blue-400' : 'border border-white/10'
                }`}
                onClick={() => setSelectedCluster(cluster)}
              >
                {/* Cluster header */}
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-foreground truncate">
                    {cluster.label || `Cluster ${cluster.cluster_id.slice(-4)}`}
                  </h3>
                  {selectedCluster?.cluster_id === cluster.cluster_id && (
                    <Check className="text-green-400" size={16} />
                  )}
                </div>

                {/* Cluster stats */}
                <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
                  <div>
                    <div className="text-muted-foreground text-xs">Faces</div>
                    <div className="font-medium text-foreground">{cluster.face_count}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs">Photos</div>
                    <div className="font-medium text-foreground">{cluster.face_count}</div>
                  </div>
                </div>

                {/* Quality indicator */}
                {qualityAnalysis?.quality_analysis?.cluster_id === cluster.cluster_id && (
                  <div className="flex items-center gap-2 text-sm">
                    <div className="text-muted-foreground">Quality:</div>
                    <div className={`font-medium ${getQualityColor(qualityAnalysis.quality_analysis.quality_rating)}`}>
                      {qualityAnalysis.quality_analysis.quality_rating}
                    </div>
                  </div>
                )}

                {/* Actions */}
                {showControls && selectedCluster?.cluster_id === cluster.cluster_id && (
                  <div className="mt-3 pt-3 border-t border-white/10 flex gap-2">
                    <button
                      onClick={() => {
                        if (onClusterSelected) {
                          onClusterSelected(cluster.cluster_id);
                        }
                      }}
                      className="btn-glass btn-glass--primary flex-1 text-sm py-1"
                    >
                      <Edit size={14} />
                      <span>View Details</span>
                    </button>
                    <button
                      onClick={() => setMergeTarget(cluster.cluster_id)}
                      className="btn-glass btn-glass--muted flex-1 text-sm py-1"
                    >
                      <User size={14} />
                      <span>Merge</span>
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Selected cluster details */}
        {selectedCluster && qualityAnalysis && (
          <div className={`${glass.surfaceStrong} mt-8 p-6 rounded-lg`}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-foreground">
                {selectedCluster.label || `Cluster ${selectedCluster.cluster_id.slice(-4)}`}
              </h2>
              <button
                onClick={() => setSelectedCluster(null)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X size={20} />
              </button>
            </div>

            {/* Cluster statistics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="text-center p-3 bg-white/5 rounded-lg">
                <div className="text-2xl font-bold text-foreground">
                  {qualityAnalysis.quality_analysis.face_count}
                </div>
                <div className="text-xs text-muted-foreground mt-1">Total Faces</div>
              </div>
              <div className="text-center p-3 bg-white/5 rounded-lg">
                <div className="text-2xl font-bold text-foreground">
                  {qualityAnalysis.quality_analysis.face_count}
                </div>
                <div className="text-xs text-muted-foreground mt-1">Total Photos</div>
              </div>
              <div className="text-center p-3 bg-white/5 rounded-lg">
                <div className="text-2xl font-bold text-foreground">
                  {qualityAnalysis.quality_analysis.avg_confidence.toFixed(2)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">Avg Confidence</div>
              </div>
              <div className="text-center p-3 bg-white/5 rounded-lg">
                <div className="text-2xl font-bold text-foreground">
                  {qualityAnalysis.quality_analysis.coherence_score.toFixed(2)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">Coherence</div>
              </div>
            </div>

            {/* Quality rating */}
            <div className="mb-4">
              <div className="text-sm font-medium text-foreground mb-2">Quality Rating</div>
              <div className="flex items-center gap-2">
                <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                  qualityAnalysis.quality_analysis.quality_rating === 'Excellent' ? 'bg-green-500/20 text-green-400' :
                  qualityAnalysis.quality_analysis.quality_rating === 'Good' ? 'bg-blue-500/20 text-blue-400' :
                  qualityAnalysis.quality_analysis.quality_rating === 'Fair' ? 'bg-yellow-500/20 text-yellow-400' :
                  qualityAnalysis.quality_analysis.quality_rating === 'Poor' ? 'bg-orange-500/20 text-orange-400' :
                  'bg-red-500/20 text-red-400'
                }`}>
                  {qualityAnalysis.quality_analysis.quality_rating}
                </div>
                <div className="text-sm text-muted-foreground">
                  {(qualityAnalysis.quality_analysis.avg_quality_score * 100).toFixed(0)}% quality score
                </div>
              </div>
            </div>

            {/* Merge controls */}
            {mergeTarget && (
              <div className="p-4 bg-white/5 rounded-lg mb-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-foreground">
                    Merge with: <span className="font-medium">{mergeTarget.slice(-4)}</span>
                  </span>
                  <button
                    onClick={() => setMergeTarget(null)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X size={16} />
                  </button>
                </div>
                <button
                  onClick={mergeClusters}
                  disabled={merging}
                  className={`btn-glass ${merging ? 'btn-glass--muted' : 'btn-glass--primary'} w-full mt-2`}
                >
                  {merging ? (
                    <>
                      <Loader2 className="animate-spin" size={16} />
                      <span>Merging...</span>
                    </>
                  ) : (
                    <>
                      <User size={16} />
                      <span>Confirm Merge</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}