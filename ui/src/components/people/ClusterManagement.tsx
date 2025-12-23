/**
 * Cluster Management Component
 *
 * Provides visual cluster organization and management interface
 * Allows users to view, edit, and organize face clusters
 *
 * Phase 1 Features:
 * - Hide/unhide persons
 * - Undo button for reversible operations
 * - Show hidden toggle
 * - Unknown faces bucket tab
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  User, Search, Edit, Trash2, Loader2, AlertTriangle, Check, X,
  EyeOff, Eye, Undo2, UserX, Users, ChevronRight
} from 'lucide-react';
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

type ViewMode = 'people' | 'unknown';

interface UndoState {
  canUndo: boolean;
  lastOperation?: string;
}

export function ClusterManagement({ onClusterSelected, showControls = true }: ClusterManagementProps) {
  const [clusters, setClusters] = useState<FaceCluster[]>([]);
  const [hiddenClusters, setHiddenClusters] = useState<FaceCluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<FaceCluster | null>(null);
  const [qualityAnalysis, setQualityAnalysis] = useState<ClusterQualityResult | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [merging, setMerging] = useState(false);
  const [mergeTarget, setMergeTarget] = useState<string | null>(null);

  // Phase 1 state
  const [viewMode, setViewMode] = useState<ViewMode>('people');
  const [showHidden, setShowHidden] = useState(false);
  const [undoState, setUndoState] = useState<UndoState>({ canUndo: false });
  const [undoing, setUndoing] = useState(false);
  const [unknownFaces, setUnknownFaces] = useState<any[]>([]);
  const [unknownCount, setUnknownCount] = useState(0);
  const [hidingCluster, setHidingCluster] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Load clusters on mount
  const loadClusters = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Get visible clusters
      const result = await api.getAllClusters();
      setClusters(result.clusters || []);

      // Get hidden clusters count for badge
      try {
        const hiddenResult = await api.getHiddenClusters();
        setHiddenClusters(hiddenResult.clusters || []);
      } catch {
        // Hidden clusters API might not exist on older backends
        setHiddenClusters([]);
      }

    } catch (err) {
      console.error('Failed to load clusters:', err);
      setError('Failed to load clusters');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load unknown faces
  const loadUnknownFaces = useCallback(async () => {
    try {
      const result = await api.getUnassignedFaces(50, 0);
      setUnknownFaces(result.faces || []);
      setUnknownCount(result.total || 0);
    } catch (err) {
      console.error('Failed to load unknown faces:', err);
    }
  }, []);

  useEffect(() => {
    loadClusters();
    loadUnknownFaces();
  }, [loadClusters, loadUnknownFaces]);

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

  // Clear success message after delay
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  // Search clusters
  const searchClusters = () => {
    if (!searchQuery.trim()) {
      loadClusters();
      return;
    }

    const search = async () => {
      try {
        const result: any = await api.searchPeople(searchQuery);
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

  // Hide cluster
  const hideCluster = async (clusterId: string) => {
    try {
      setHidingCluster(clusterId);
      await api.hideCluster(clusterId);
      setUndoState({ canUndo: true, lastOperation: 'hide' });
      setSuccessMessage('Person hidden');
      await loadClusters();
      setSelectedCluster(null);
    } catch (err) {
      console.error('Failed to hide cluster:', err);
      setError('Failed to hide person');
    } finally {
      setHidingCluster(null);
    }
  };

  // Unhide cluster
  const unhideCluster = async (clusterId: string) => {
    try {
      setHidingCluster(clusterId);
      await api.unhideCluster(clusterId);
      setUndoState({ canUndo: true, lastOperation: 'unhide' });
      setSuccessMessage('Person restored');
      await loadClusters();
    } catch (err) {
      console.error('Failed to unhide cluster:', err);
      setError('Failed to restore person');
    } finally {
      setHidingCluster(null);
    }
  };

  // Undo last operation
  const handleUndo = async () => {
    try {
      setUndoing(true);
      const result = await api.undoLastOperation();
      if (result.success) {
        setSuccessMessage(`Undid ${result.operation_type} operation`);
        setUndoState({ canUndo: false });
        await loadClusters();
        await loadUnknownFaces();
      } else {
        setError(result.message || 'Nothing to undo');
      }
    } catch (err) {
      console.error('Undo failed:', err);
      setError('Failed to undo');
    } finally {
      setUndoing(false);
    }
  };

  // Merge clusters with undo support
  const mergeClusters = async () => {
    if (!selectedCluster || !mergeTarget) return;

    try {
      setMerging(true);
      const result = await api.mergeClustersWithUndo(
        selectedCluster.cluster_id,
        mergeTarget
      );

      if (result.success) {
        setUndoState({ canUndo: true, lastOperation: 'merge' });
        setSuccessMessage('Clusters merged');
        await loadClusters();
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

  // Get displayed clusters based on showHidden toggle
  const displayedClusters = showHidden ? [...clusters, ...hiddenClusters] : clusters;

  return (
    <div className="min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-foreground">People</h1>
          <div className="flex items-center gap-3">
            {/* Undo button */}
            {undoState.canUndo && (
              <button
                onClick={handleUndo}
                disabled={undoing}
                className="btn-glass btn-glass--muted px-3 py-2 flex items-center gap-1"
                title={`Undo ${undoState.lastOperation || 'last operation'}`}
              >
                {undoing ? (
                  <Loader2 className="animate-spin" size={16} />
                ) : (
                  <Undo2 size={16} />
                )}
                <span>Undo</span>
              </button>
            )}

            {/* Show Hidden toggle */}
            <button
              onClick={() => setShowHidden(!showHidden)}
              className={`btn-glass px-3 py-2 flex items-center gap-1 ${showHidden ? 'btn-glass--primary' : 'btn-glass--muted'
                }`}
              title={showHidden ? 'Hide hidden people' : 'Show hidden people'}
            >
              {showHidden ? <Eye size={16} /> : <EyeOff size={16} />}
              <span>Hidden ({hiddenClusters.length})</span>
            </button>

            {showControls && (
              <button
                onClick={() => {
                  const cluster = async () => {
                    try {
                      setLoading(true);
                      const result: ClusteringResult = await api.clusterFaces(0.6, 2);
                      if (result.success) {
                        await loadClusters();
                        await loadUnknownFaces();
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
            )}
          </div>
        </div>

        {/* Success message */}
        {successMessage && (
          <div className="mb-4 p-3 bg-green-500/20 border border-green-500/30 rounded-lg text-green-400 flex items-center gap-2">
            <Check size={16} />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <div className="text-red-400 p-4 bg-red-500/10 rounded-lg mb-4 flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)}>
              <X size={16} />
            </button>
          </div>
        )}

        {/* View mode tabs */}
        <div className="flex gap-2 mb-6 border-b border-white/10 pb-4">
          <button
            onClick={() => setViewMode('people')}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 ${viewMode === 'people'
                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                : 'text-muted-foreground hover:text-foreground'
              }`}
          >
            <Users size={18} />
            <span>People ({clusters.length})</span>
          </button>
          <button
            onClick={() => setViewMode('unknown')}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 ${viewMode === 'unknown'
                ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                : 'text-muted-foreground hover:text-foreground'
              }`}
          >
            <UserX size={18} />
            <span>Unknown ({unknownCount})</span>
          </button>
        </div>

        {/* People view */}
        {viewMode === 'people' && (
          <>
            {/* Search */}
            <div className="mb-6">
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Search people..."
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
                  <span className="text-foreground">Loading people...</span>
                </div>
              </div>
            )}

            {/* No clusters */}
            {!loading && displayedClusters.length === 0 && (
              <div className="text-center py-20">
                <User className="mx-auto text-muted-foreground mb-4" size={48} />
                <h3 className="text-lg font-medium text-foreground mb-2">No People Found</h3>
                <p className="text-muted-foreground">
                  {searchQuery ? 'No people match your search' : 'No people have been identified yet'}
                </p>
              </div>
            )}

            {/* Clusters grid */}
            {!loading && displayedClusters.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {displayedClusters.map((cluster) => {
                  const isHidden = hiddenClusters.some(h => h.cluster_id === cluster.cluster_id);

                  return (
                    <div
                      key={cluster.cluster_id}
                      className={`${glass.surface} p-4 rounded-lg cursor-pointer hover:border-blue-400 transition-all ${selectedCluster?.cluster_id === cluster.cluster_id ? 'border-2 border-blue-400' : 'border border-white/10'
                        } ${isHidden ? 'opacity-60' : ''}`}
                      onClick={() => setSelectedCluster(cluster)}
                    >
                      {/* Cluster header */}
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium text-foreground truncate">
                            {cluster.label || `Person ${cluster.cluster_id.slice(-4)}`}
                          </h3>
                          {isHidden && (
                            <span className="px-1.5 py-0.5 text-xs bg-white/10 rounded text-muted-foreground">
                              Hidden
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1">
                          {selectedCluster?.cluster_id === cluster.cluster_id && (
                            <Check className="text-green-400" size={16} />
                          )}
                          {/* Hide/Unhide button */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              isHidden ? unhideCluster(cluster.cluster_id) : hideCluster(cluster.cluster_id);
                            }}
                            disabled={hidingCluster === cluster.cluster_id}
                            className="p-1 hover:bg-white/10 rounded"
                            title={isHidden ? 'Unhide person' : 'Hide person'}
                          >
                            {hidingCluster === cluster.cluster_id ? (
                              <Loader2 className="animate-spin" size={14} />
                            ) : isHidden ? (
                              <Eye size={14} className="text-muted-foreground" />
                            ) : (
                              <EyeOff size={14} className="text-muted-foreground" />
                            )}
                          </button>
                        </div>
                      </div>

                      {/* Cluster stats */}
                      <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
                        <div>
                          <div className="text-muted-foreground text-xs">Faces</div>
                          <div className="font-medium text-foreground">{cluster.face_count}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground text-xs">Photos</div>
                          <div className="font-medium text-foreground">{cluster.photo_count || cluster.face_count}</div>
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
                            onClick={(e) => {
                              e.stopPropagation();
                              if (onClusterSelected) {
                                onClusterSelected(cluster.cluster_id);
                              }
                            }}
                            className="btn-glass btn-glass--primary flex-1 text-sm py-1"
                          >
                            <ChevronRight size={14} />
                            <span>View</span>
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setMergeTarget(cluster.cluster_id);
                            }}
                            className="btn-glass btn-glass--muted flex-1 text-sm py-1"
                          >
                            <Users size={14} />
                            <span>Merge</span>
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Selected cluster details */}
            {selectedCluster && qualityAnalysis && (
              <div className={`${glass.surfaceStrong} mt-8 p-6 rounded-lg`}>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-bold text-foreground">
                    {selectedCluster.label || `Person ${selectedCluster.cluster_id.slice(-4)}`}
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
                    <div className={`px-3 py-1 rounded-full text-sm font-medium ${qualityAnalysis.quality_analysis.quality_rating === 'Excellent' ? 'bg-green-500/20 text-green-400' :
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
                          <Users size={16} />
                          <span>Confirm Merge</span>
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* Unknown faces view */}
        {viewMode === 'unknown' && (
          <div>
            <div className="mb-4 p-4 bg-orange-500/10 border border-orange-500/20 rounded-lg">
              <div className="flex items-center gap-2 text-orange-400">
                <AlertTriangle size={18} />
                <span className="font-medium">Unidentified Faces</span>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                These faces haven't been assigned to any person yet. Click on a face to assign it to an existing person or create a new one.
              </p>
            </div>

            {unknownFaces.length === 0 ? (
              <div className="text-center py-20">
                <Check className="mx-auto text-green-400 mb-4" size={48} />
                <h3 className="text-lg font-medium text-foreground mb-2">All Caught Up!</h3>
                <p className="text-muted-foreground">
                  No unidentified faces. All detected faces have been assigned to people.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
                {unknownFaces.map((face) => (
                  <div
                    key={face.detection_id}
                    className="aspect-square bg-white/5 rounded-lg border border-white/10 hover:border-blue-400 transition-all cursor-pointer flex items-center justify-center overflow-hidden"
                    onClick={() => {
                      // TODO: Open assignment dialog
                      console.log('Assign face:', face.detection_id);
                    }}
                  >
                    <UserX className="text-muted-foreground" size={24} />
                  </div>
                ))}
              </div>
            )}

            {unknownCount > unknownFaces.length && (
              <div className="mt-4 text-center">
                <button
                  onClick={() => loadUnknownFaces()}
                  className="btn-glass btn-glass--muted"
                >
                  Load More ({unknownCount - unknownFaces.length} remaining)
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
