/**
 * Person Detail Page - Shows photos containing a specific person
 *
 * Phase 2 Features:
 * - Confirm/reject controls on each face
 * - Assignment state badges (auto/confirmed/rejected)
 * - Multi-select mode for split flow
 * - Move selected faces to another person
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  User,
  Camera,
  RefreshCw,
  Check,
  X,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Move,
  UserPlus,
  Loader2,
  Undo2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Scissors,
  ToggleLeft,
  ToggleRight,
  Trash2,
  Download,
  Search,
} from 'lucide-react';
import { api } from '../api';
import { isLocalStorageAvailable, localGetItem } from '../utils/storage';
import { glass } from '../design/glass';
import SecureLazyImage from '../components/gallery/SecureLazyImage';
import { usePhotoViewer } from '../contexts/PhotoViewerContext';
import type { Photo } from '../api';

interface PersonPhoto {
  path: string;
  face_id: number;
  detection_id?: string;
  bounding_box: number[] | null;
  confidence: number;
  assignment_state?: 'auto' | 'user_confirmed' | 'user_rejected';
}

interface ClusterInfo {
  id: string;
  label: string;
  face_count: number;
}

type AssignmentState = 'auto' | 'user_confirmed' | 'user_rejected';

type PersonAnalytics = {
  person_id?: string;
  person_name?: string;
  face_count?: number;
  photo_count?: number;
  first_seen?: string;
  last_seen?: string;
  cluster_ids?: string[];
  [key: string]: unknown;
};

export default function PersonDetail() {
  const { clusterId } = useParams<{ clusterId: string }>();
  const navigate = useNavigate();
  const { openForPhoto } = usePhotoViewer();
  const [photos, setPhotos] = useState<PersonPhoto[]>([]);
  const [clusterInfo, setClusterInfo] = useState<ClusterInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Phase 2 state
  const [selectedFaces, setSelectedFaces] = useState<Set<string>>(new Set());
  const [selectionMode, setSelectionMode] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [canUndo, setCanUndo] = useState(false);
  const [showSplitDialog, setShowSplitDialog] = useState(false);
  const [newPersonName, setNewPersonName] = useState('');

  // Phase 5.2: Mixed cluster warning state
  interface CoherenceData {
    coherence_score: number;
    variance: number;
    low_quality_ratio: number;
    is_mixed_suspected: boolean;
    face_count: number;
    avg_confidence: number;
  }
  const [coherence, setCoherence] = useState<CoherenceData | null>(null);
  const [showMixedDetails, setShowMixedDetails] = useState(false);

  // Phase 6: Privacy controls state
  const [indexingEnabled, setIndexingEnabled] = useState(true);
  const [indexingLoading, setIndexingLoading] = useState(false);

  // Analytics (Hidden Genius: expose backend analytics)
  const [analytics, setAnalytics] = useState<PersonAnalytics | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  // Move faces to another person
  const [clustersForMove, setClustersForMove] = useState<ClusterInfo[]>([]);
  const [moveModal, setMoveModal] = useState<{
    open: boolean;
    faceIds: string[];
    targetClusterId: string;
  }>({ open: false, faceIds: [], targetClusterId: '' });
  const [moveLoading, setMoveLoading] = useState(false);

  // Similar face search
  const [similarModal, setSimilarModal] = useState<{
    open: boolean;
    loading: boolean;
    detectionId?: string;
    results?: Array<{
      detection_id: string;
      photo_path: string;
      similarity: number;
      person_id?: string;
      person_label?: string;
    }>;
    error?: string | null;
  }>({ open: false, loading: false, results: undefined, error: null });

  const refreshUndoStatus = useCallback(async () => {
    try {
      const status = await api.getUndoStatus();
      setCanUndo(!!status?.can_undo);
    } catch (err) {
      console.error('Failed to fetch undo status:', err);
      setCanUndo(false);
    }
  }, []);

  const loadClustersForMove = useCallback(async () => {
    try {
      const data = await api.getFaceClusters();
      const clusters = (data?.clusters || [])
        .map((c: any) => ({ id: c.id, label: c.label || `Person ${c.id}` }))
        .filter((c: ClusterInfo) => c.id !== clusterId);
      setClustersForMove(clusters);
      if (!moveModal.targetClusterId && clusters.length > 0) {
        setMoveModal((prev) => ({ ...prev, targetClusterId: clusters[0].id }));
      }
    } catch (err) {
      console.error('Failed to load clusters for move:', err);
    }
  }, [clusterId]);

  const fetchPhotos = useCallback(async () => {
    if (!clusterId) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${
          import.meta.env.VITE_API_URL || 'http://localhost:8000'
        }/api/faces/clusters/${clusterId}/photos`
      );
      const data = await response.json();
      setPhotos(data.photos || []);

      // Also fetch cluster info
      const clustersRes = await fetch(
        `${
          import.meta.env.VITE_API_URL || 'http://localhost:8000'
        }/api/faces/clusters`
      );
      const clustersData = await clustersRes.json();
      const cluster = clustersData.clusters?.find(
        (c: any) => c.id === clusterId
      );
      if (cluster) {
        setClusterInfo({
          id: cluster.id,
          label: cluster.label || `Person ${cluster.id}`,
          face_count: cluster.face_count,
        });
      }
    } catch (err) {
      console.error('Failed to fetch person photos:', err);
      setError('Failed to load photos');
    } finally {
      setLoading(false);
    }
  }, [clusterId]);

  const fetchAnalytics = useCallback(async () => {
    if (!clusterId) return;
    try {
      setAnalyticsLoading(true);
      setAnalyticsError(null);
      const data = await api.get(
        `/api/people/${encodeURIComponent(clusterId)}/analytics`
      );
      setAnalytics(data || null);
    } catch (err: any) {
      console.error('Failed to fetch analytics:', err);
      setAnalytics(null);
      setAnalyticsError(err?.message || 'Failed to load analytics');
    } finally {
      setAnalyticsLoading(false);
    }
  }, [clusterId]);

  useEffect(() => {
    fetchPhotos();
  }, [fetchPhotos]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  useEffect(() => {
    loadClustersForMove();
  }, [loadClustersForMove]);

  useEffect(() => {
    refreshUndoStatus();
  }, [refreshUndoStatus]);

  // Fetch coherence data for mixed cluster detection
  useEffect(() => {
    if (clusterId) {
      api
        .getClusterCoherence(clusterId)
        .then(setCoherence)
        .catch(console.error);
    }
  }, [clusterId]);

  // Fetch indexing status for privacy controls
  useEffect(() => {
    if (clusterId) {
      api
        .getPersonIndexingStatus(clusterId)
        .then((data) => setIndexingEnabled(data.enabled))
        .catch(console.error);
    }
  }, [clusterId]);

  // Toggle indexing enabled/disabled
  const handleToggleIndexing = async () => {
    if (!clusterId) return;
    setIndexingLoading(true);
    try {
      await api.setPersonIndexingEnabled(clusterId, !indexingEnabled);
      setIndexingEnabled(!indexingEnabled);
    } catch (err) {
      console.error('Failed to toggle indexing:', err);
    } finally {
      setIndexingLoading(false);
    }
  };

  // Clear success message after delay
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  // Confirm a face assignment
  const handleConfirm = async (photo: PersonPhoto) => {
    if (!clusterId) return;
    const faceId = photo.detection_id || String(photo.face_id);

    try {
      setActionLoading(faceId);
      await api.confirmFace(faceId, clusterId);
      setSuccessMessage('Face confirmed');
      await refreshUndoStatus();

      // Update local state
      setPhotos((prev) =>
        prev.map((p) =>
          (p.detection_id || String(p.face_id)) === faceId
            ? { ...p, assignment_state: 'user_confirmed' as AssignmentState }
            : p
        )
      );
    } catch (err) {
      console.error('Failed to confirm face:', err);
      setError('Failed to confirm face');
    } finally {
      setActionLoading(null);
    }
  };

  // Reject a face from this cluster
  const handleReject = async (photo: PersonPhoto) => {
    if (!clusterId) return;
    const faceId = photo.detection_id || String(photo.face_id);

    try {
      setActionLoading(faceId);
      await api.rejectFace(faceId, clusterId);
      setSuccessMessage('Face rejected - moved to Unknown');
      await refreshUndoStatus();

      // Remove from local state
      setPhotos((prev) =>
        prev.filter((p) => (p.detection_id || String(p.face_id)) !== faceId)
      );
    } catch (err) {
      console.error('Failed to reject face:', err);
      setError('Failed to reject face');
    } finally {
      setActionLoading(null);
    }
  };

  // Toggle face selection
  const toggleFaceSelection = (photo: PersonPhoto) => {
    const faceId = photo.detection_id || String(photo.face_id);
    setSelectedFaces((prev) => {
      const next = new Set(prev);
      if (next.has(faceId)) {
        next.delete(faceId);
      } else {
        next.add(faceId);
      }
      return next;
    });
  };

  // Split selected faces to new person
  const handleSplit = async () => {
    if (selectedFaces.size === 0) return;

    try {
      setActionLoading('split');
      const detectionIds = Array.from(selectedFaces);
      const result = await api.splitFaces(
        detectionIds,
        newPersonName || undefined
      );

      setSuccessMessage(`Created new person with ${result.faces_moved} faces`);
      await refreshUndoStatus();
      setSelectedFaces(new Set());
      setSelectionMode(false);
      setShowSplitDialog(false);
      setNewPersonName('');

      // Refresh photos
      await fetchPhotos();
    } catch (err) {
      console.error('Failed to split faces:', err);
      setError('Failed to split faces');
    } finally {
      setActionLoading(null);
    }
  };

  // Undo last operation
  const handleUndo = useCallback(async () => {
    setActionLoading('undo');
    try {
      await api.undoLastOperation();
      await fetchPhotos(); // Refresh list
      await refreshUndoStatus();
    } catch (err) {
      console.error(err);
      setError('Failed to undo');
    } finally {
      setActionLoading(null);
    }
  }, [fetchPhotos, refreshUndoStatus]);

  const openMoveModalForFaces = (faceIds: string[]) => {
    if (!faceIds.length) return;
    const defaultTarget = clustersForMove.find((c) => c.id !== clusterId);
    setMoveModal({
      open: true,
      faceIds,
      targetClusterId: defaultTarget?.id || '',
    });
  };

  const handleMoveFaces = async () => {
    if (!moveModal.targetClusterId || moveModal.faceIds.length === 0) return;
    setMoveLoading(true);
    try {
      await Promise.all(
        moveModal.faceIds.map((fid) =>
          api.moveFace(fid, moveModal.targetClusterId)
        )
      );
      setSuccessMessage(
        moveModal.faceIds.length === 1
          ? 'Face moved to selected person'
          : `${moveModal.faceIds.length} faces moved to selected person`
      );
      setMoveModal({ open: false, faceIds: [], targetClusterId: '' });
      setSelectedFaces(new Set());
      setSelectionMode(false);
      await fetchPhotos();
      await refreshUndoStatus();
    } catch (err) {
      console.error('Failed to move faces:', err);
      setError('Failed to move faces');
    } finally {
      setMoveLoading(false);
    }
  };

  const openSimilarModal = async (detectionId: string) => {
    setSimilarModal({
      open: true,
      loading: true,
      detectionId,
      results: [],
      error: null,
    });
    try {
      const data = await api.getSimilarFaces(detectionId, 12);
      setSimilarModal({
        open: true,
        loading: false,
        detectionId,
        results: data?.similar_faces || [],
        error: null,
      });
    } catch (err: any) {
      setSimilarModal({
        open: true,
        loading: false,
        detectionId,
        results: [],
        error: err?.message || 'Failed to load similar faces',
      });
    }
  };

  const handleDeletePerson = useCallback(async () => {
    if (!clusterId) return;
    if (
      window.confirm(
        'Are you sure you want to delete this person? All faces will be unassigned. You can undo this action immediately.'
      )
    ) {
      setActionLoading('delete');
      try {
        await api.deletePerson(clusterId);
        navigate('/people');
      } catch (err) {
        setError('Failed to delete person');
        setActionLoading(null);
      }
    }
  }, [clusterId, navigate]);

  const handleExport = useCallback(async () => {
    if (!clusterId) return;
    try {
      setActionLoading('export');
      const data = await api.exportPersonData(clusterId);

      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `person_${clusterId}_export.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      setError('Failed to export data');
    } finally {
      setActionLoading(null);
    }
  }, [clusterId]);

  // Get assignment state badge
  const getStateBadge = (state?: AssignmentState) => {
    switch (state) {
      case 'user_confirmed':
        return (
          <div
            className='absolute top-2 left-2 bg-green-500/80 backdrop-blur-sm rounded-full p-1'
            title='Confirmed'
          >
            <CheckCircle2 size={14} className='text-white' />
          </div>
        );
      case 'user_rejected':
        return (
          <div
            className='absolute top-2 left-2 bg-red-500/80 backdrop-blur-sm rounded-full p-1'
            title='Rejected'
          >
            <XCircle size={14} className='text-white' />
          </div>
        );
      case 'auto':
      default:
        return (
          <div
            className='absolute top-2 left-2 bg-blue-500/80 backdrop-blur-sm rounded-full p-1'
            title='Auto-detected'
          >
            <AlertCircle size={14} className='text-white' />
          </div>
        );
    }
  };

  return (
    <div className='min-h-screen'>
      {/* Header */}
      <div className='border-b border-white/10'>
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center gap-4'>
              <button
                onClick={() => navigate('/people')}
                className='btn-glass btn-glass--muted p-2'
                aria-label='Back to People'
                title='Back to People'
              >
                <ArrowLeft size={20} />
              </button>

              <div className='flex items-center gap-3'>
                <div
                  className={`${glass.surface} p-3 rounded-xl border border-white/10`}
                >
                  <User size={24} className='text-primary' />
                </div>
                <div>
                  <h1 className='text-xl font-semibold text-foreground'>
                    {clusterInfo?.label || `Person ${clusterId}`}
                  </h1>
                  <p className='text-sm text-muted-foreground'>
                    {photos.length} photos • {clusterInfo?.face_count || 0}{' '}
                    appearances
                  </p>
                </div>
              </div>
            </div>

            {/* Action buttons */}
            <div className='flex items-center gap-2'>
              {/* Indexing toggle - Phase 6 */}
              <button
                onClick={handleToggleIndexing}
                disabled={indexingLoading}
                className={`btn-glass px-3 py-2 flex items-center gap-1 ${
                  indexingEnabled
                    ? 'btn-glass--muted'
                    : 'bg-yellow-500/20 border-yellow-500/30 text-yellow-400'
                }`}
                title={
                  indexingEnabled
                    ? 'Auto-assignment enabled'
                    : 'Auto-assignment disabled'
                }
              >
                {indexingLoading ? (
                  <Loader2 className='animate-spin' size={16} />
                ) : indexingEnabled ? (
                  <ToggleRight size={16} className='text-green-400' />
                ) : (
                  <ToggleLeft size={16} />
                )}
                <span className='hidden sm:inline'>
                  {indexingEnabled ? 'Auto-assign ON' : 'Auto-assign OFF'}
                </span>
              </button>

              {/* Undo button */}
              {canUndo && (
                <button
                  onClick={handleUndo}
                  disabled={actionLoading === 'undo'}
                  className='btn-glass btn-glass--muted px-3 py-2 flex items-center gap-1'
                >
                  {actionLoading === 'undo' ? (
                    <Loader2 className='animate-spin' size={16} />
                  ) : (
                    <Undo2 size={16} />
                  )}
                  <span>Undo</span>
                </button>
              )}

              {/* Export button */}
              <button
                onClick={handleExport}
                disabled={!!actionLoading}
                className='btn-glass px-3 py-2 flex items-center gap-1'
                title='Export Data'
              >
                {actionLoading === 'export' ? (
                  <Loader2 className='animate-spin' size={16} />
                ) : (
                  <Download size={16} />
                )}
              </button>

              {/* Delete button */}
              <button
                onClick={handleDeletePerson}
                disabled={!!actionLoading}
                className='btn-glass px-3 py-2 flex items-center gap-1 text-red-400 border-red-500/30 hover:bg-red-500/10'
                title='Delete Person'
              >
                {actionLoading === 'delete' ? (
                  <Loader2 className='animate-spin' size={16} />
                ) : (
                  <Trash2 size={16} />
                )}
              </button>

              {/* Selection mode toggle */}
              <button
                onClick={() => {
                  setSelectionMode(!selectionMode);
                  if (selectionMode) {
                    setSelectedFaces(new Set());
                  }
                }}
                className={`btn-glass px-3 py-2 flex items-center gap-1 ${
                  selectionMode ? 'btn-glass--primary' : 'btn-glass--muted'
                }`}
              >
                <Move size={16} />
                <span>
                  {selectionMode ? `${selectedFaces.size} selected` : 'Select'}
                </span>
              </button>

              {/* Split button (when faces selected) */}
              {selectionMode && selectedFaces.size > 0 && (
                <button
                  onClick={() => setShowSplitDialog(true)}
                  className='btn-glass btn-glass--primary px-3 py-2 flex items-center gap-1'
                >
                  <UserPlus size={16} />
                  <span>Move to New Person</span>
                </button>
              )}

              {selectionMode && selectedFaces.size > 0 && (
                <button
                  onClick={() =>
                    openMoveModalForFaces(Array.from(selectedFaces))
                  }
                  className='btn-glass btn-glass--muted px-3 py-2 flex items-center gap-1'
                >
                  <Move size={16} />
                  <span>Move to Existing</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Success message */}
      {successMessage && (
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4'>
          <div className='p-3 bg-green-500/20 border border-green-500/30 rounded-lg text-green-400 flex items-center gap-2'>
            <Check size={16} />
            <span>{successMessage}</span>
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4'>
          <div className='p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 flex items-center justify-between'>
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              aria-label='Dismiss error'
              title='Dismiss error'
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Mixed Cluster Warning Panel - Phase 5.2 */}
      {coherence?.is_mixed_suspected && (
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4'>
          <div className='p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg'>
            <div className='flex items-start justify-between'>
              <div className='flex items-start gap-3'>
                <AlertTriangle size={20} className='text-yellow-500 mt-0.5' />
                <div>
                  <h3 className='font-semibold text-yellow-400'>
                    This cluster may contain multiple people
                  </h3>
                  <p className='text-sm text-yellow-400/80 mt-1'>
                    Our analysis detected higher than normal variance in face
                    embeddings. Review the faces below and use Split mode to
                    separate different people.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowMixedDetails(!showMixedDetails)}
                className='text-yellow-400 hover:text-yellow-300 p-1'
              >
                {showMixedDetails ? (
                  <ChevronUp size={18} />
                ) : (
                  <ChevronDown size={18} />
                )}
              </button>
            </div>

            {/* Expandable stats */}
            {showMixedDetails && (
              <div className='mt-4 pt-4 border-t border-yellow-500/20 grid grid-cols-2 sm:grid-cols-4 gap-4'>
                <div className='text-center'>
                  <div className='text-2xl font-bold text-yellow-400'>
                    {(coherence.coherence_score * 100).toFixed(0)}%
                  </div>
                  <div className='text-xs text-yellow-400/60'>Coherence</div>
                </div>
                <div className='text-center'>
                  <div className='text-2xl font-bold text-yellow-400'>
                    {coherence.variance.toFixed(3)}
                  </div>
                  <div className='text-xs text-yellow-400/60'>Variance</div>
                </div>
                <div className='text-center'>
                  <div className='text-2xl font-bold text-yellow-400'>
                    {(coherence.low_quality_ratio * 100).toFixed(0)}%
                  </div>
                  <div className='text-xs text-yellow-400/60'>Low Quality</div>
                </div>
                <div className='text-center'>
                  <div className='text-2xl font-bold text-yellow-400'>
                    {(coherence.avg_confidence * 100).toFixed(0)}%
                  </div>
                  <div className='text-xs text-yellow-400/60'>
                    Avg Confidence
                  </div>
                </div>
              </div>
            )}

            {/* Split Mode CTA */}
            <div className='mt-4 flex gap-3'>
              <button
                onClick={() => setSelectionMode(true)}
                className='flex items-center gap-2 px-4 py-2 bg-yellow-500 hover:bg-yellow-400 text-black font-medium rounded-lg transition-colors'
              >
                <Scissors size={16} />
                Enter Split Mode
              </button>
              <button
                onClick={() => setShowMixedDetails(!showMixedDetails)}
                className='text-yellow-400/70 hover:text-yellow-400 text-sm'
              >
                {showMixedDetails ? 'Hide' : 'Show'} Details
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8'>
        {/* Analytics */}
        <div
          className={`${glass.surface} rounded-xl border border-white/10 p-4 mb-6`}
        >
          <div className='flex items-start justify-between gap-4'>
            <div>
              <h2 className='text-lg font-semibold text-foreground'>
                Person analytics
              </h2>
              <p className='text-sm text-muted-foreground'>
                Powered by{' '}
                <code>
                  GET /api/people/{'{'}person_id{'}'}/analytics
                </code>
              </p>
            </div>
            <button
              onClick={fetchAnalytics}
              disabled={!clusterId || analyticsLoading}
              className='btn-glass btn-glass--muted px-3 py-2 flex items-center gap-2'
              title='Refresh analytics'
              aria-label='Refresh analytics'
            >
              {analyticsLoading ? (
                <RefreshCw size={16} className='animate-spin' />
              ) : (
                <RefreshCw size={16} />
              )}
              <span className='hidden sm:inline'>Refresh</span>
            </button>
          </div>

          {analyticsError && (
            <div className='mt-3 text-sm text-red-400'>{analyticsError}</div>
          )}

          {!analyticsError && analytics && (
            <div className='mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3'>
              <div className='p-3 bg-white/5 rounded-lg border border-white/10'>
                <div className='text-xs text-muted-foreground'>Faces</div>
                <div className='text-lg font-semibold text-foreground'>
                  {analytics.face_count ?? '—'}
                </div>
              </div>
              <div className='p-3 bg-white/5 rounded-lg border border-white/10'>
                <div className='text-xs text-muted-foreground'>Photos</div>
                <div className='text-lg font-semibold text-foreground'>
                  {analytics.photo_count ?? '—'}
                </div>
              </div>
              <div className='p-3 bg-white/5 rounded-lg border border-white/10'>
                <div className='text-xs text-muted-foreground'>First seen</div>
                <div className='text-sm font-medium text-foreground truncate'>
                  {analytics.first_seen ?? '—'}
                </div>
              </div>
              <div className='p-3 bg-white/5 rounded-lg border border-white/10'>
                <div className='text-xs text-muted-foreground'>Last seen</div>
                <div className='text-sm font-medium text-foreground truncate'>
                  {analytics.last_seen ?? '—'}
                </div>
              </div>
            </div>
          )}

          {/* Developer Mode: Raw JSON */}
          {analytics &&
            isLocalStorageAvailable() &&
            localGetItem('lm:developerMode') === '1' && (
              <details className='mt-4 bg-black/20 rounded-lg border border-white/10'>
                <summary className='px-4 py-2 text-sm font-medium text-muted-foreground cursor-pointer hover:text-foreground'>
                  Raw JSON (Developer Mode)
                </summary>
                <pre className='px-4 py-3 text-xs text-muted-foreground overflow-x-auto'>
                  {JSON.stringify(analytics, null, 2)}
                </pre>
              </details>
            )}
        </div>

        {/* Loading */}
        {loading && (
          <div className='flex items-center justify-center py-20'>
            <div className='flex items-center gap-3'>
              <RefreshCw
                size={20}
                className='animate-spin text-muted-foreground'
              />
              <span className='text-muted-foreground'>Loading photos...</span>
            </div>
          </div>
        )}

        {/* No Photos */}
        {!loading && !error && photos.length === 0 && (
          <div className='text-center py-20'>
            <Camera size={48} className='mx-auto text-muted-foreground mb-4' />
            <h3 className='text-lg font-medium text-foreground mb-2'>
              No Photos Found
            </h3>
            <p className='text-muted-foreground'>
              This person doesn't appear in any photos yet.
            </p>
          </div>
        )}

        {/* Photo Grid */}
        {!loading && !error && photos.length > 0 && (
          <div className='grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4'>
            {photos.map((photo, index) => {
              const faceId = photo.detection_id || String(photo.face_id);
              const isSelected = selectedFaces.has(faceId);
              const isLoading = actionLoading === faceId;

              return (
                <div
                  key={`${photo.path}-${index}`}
                  className={`${
                    glass.surface
                  } rounded-xl overflow-hidden border transition-all relative group ${
                    isSelected
                      ? 'border-blue-400 ring-2 ring-blue-400/50'
                      : 'border-white/10 hover:border-white/20'
                  } ${selectionMode ? 'cursor-pointer' : ''}`}
                  onClick={() => {
                    if (selectionMode) {
                      toggleFaceSelection(photo);
                    } else {
                      // Open in photo viewer
                      const photoAsPhotoType: Photo = {
                        path: photo.path,
                        filename: photo.path.split('/').pop() || '',
                        score: photo.confidence,
                        metadata: {},
                      };
                      const allPhotosAsPhotoType: Photo[] = photos.map((p) => ({
                        path: p.path,
                        filename: p.path.split('/').pop() || '',
                        score: p.confidence,
                        metadata: {},
                      }));
                      openForPhoto(allPhotosAsPhotoType, photoAsPhotoType);
                    }
                  }}
                >
                  <div className='aspect-square relative'>
                    <SecureLazyImage
                      path={photo.path}
                      size={400}
                      alt={`Photo containing ${clusterInfo?.label || 'person'}`}
                      className='w-full h-full object-cover'
                      showBadge={false}
                    />

                    {/* Assignment state badge */}
                    {getStateBadge(photo.assignment_state)}

                    {/* Selection checkbox */}
                    {selectionMode && (
                      <div
                        className={`absolute top-2 right-2 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
                          isSelected
                            ? 'bg-blue-500 border-blue-500'
                            : 'bg-black/40 border-white/50'
                        }`}
                      >
                        {isSelected && (
                          <Check size={14} className='text-white' />
                        )}
                      </div>
                    )}

                    {/* Confidence badge */}
                    <div className='absolute bottom-2 right-2 bg-black/60 backdrop-blur-sm rounded px-2 py-1 text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity'>
                      {Math.round(photo.confidence * 100)}% match
                    </div>

                    {/* Loading overlay */}
                    {isLoading && (
                      <div className='absolute inset-0 bg-black/50 flex items-center justify-center'>
                        <Loader2
                          className='animate-spin text-white'
                          size={24}
                        />
                      </div>
                    )}
                  </div>

                  {/* Confirm/Reject controls (shown on hover, not in selection mode) */}
                  {!selectionMode && !isLoading && (
                    <div className='absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity'>
                      <div className='flex gap-2 justify-center flex-wrap'>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleConfirm(photo);
                          }}
                          className='px-3 py-1.5 bg-green-500/80 hover:bg-green-500 rounded-lg text-xs text-white flex items-center gap-1 transition-colors'
                          title='Confirm: This is the right person'
                        >
                          <CheckCircle2 size={14} />
                          <span>Confirm</span>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleReject(photo);
                          }}
                          className='px-3 py-1.5 bg-red-500/80 hover:bg-red-500 rounded-lg text-xs text-white flex items-center gap-1 transition-colors'
                          title='Reject: Not this person'
                        >
                          <XCircle size={14} />
                          <span>Not them</span>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            openMoveModalForFaces([faceId]);
                          }}
                          className='px-3 py-1.5 bg-blue-500/80 hover:bg-blue-500 rounded-lg text-xs text-white flex items-center gap-1 transition-colors'
                          title='Move this face to another person'
                        >
                          <Move size={14} />
                          <span>Move</span>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            openSimilarModal(faceId);
                          }}
                          className='px-3 py-1.5 bg-purple-500/80 hover:bg-purple-500 rounded-lg text-xs text-white flex items-center gap-1 transition-colors'
                          title='Find similar faces'
                        >
                          <Search size={14} />
                          <span>Similar</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Split Dialog */}
      {showSplitDialog && (
        <div className='fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50'>
          <div
            className={`${glass.surfaceStrong} rounded-xl p-6 max-w-md w-full mx-4 border border-white/10`}
          >
            <h2 className='text-lg font-semibold text-foreground mb-4'>
              Move {selectedFaces.size} Faces to New Person
            </h2>

            <div className='mb-4'>
              <label className='block text-sm text-muted-foreground mb-2'>
                New Person Name (optional)
              </label>
              <input
                type='text'
                value={newPersonName}
                onChange={(e) => setNewPersonName(e.target.value)}
                placeholder='Enter name...'
                className='w-full px-4 py-2 bg-white/10 rounded-lg outline-none border border-white/10 focus:border-blue-400'
              />
            </div>

            <div className='flex gap-3'>
              <button
                onClick={() => {
                  setShowSplitDialog(false);
                  setNewPersonName('');
                }}
                className='btn-glass btn-glass--muted flex-1'
              >
                Cancel
              </button>
              <button
                onClick={handleSplit}
                disabled={actionLoading === 'split'}
                className='btn-glass btn-glass--primary flex-1 flex items-center justify-center gap-2'
              >
                {actionLoading === 'split' ? (
                  <Loader2 className='animate-spin' size={16} />
                ) : (
                  <UserPlus size={16} />
                )}
                <span>Create Person</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Move Faces Modal */}
      {moveModal.open && (
        <div className='fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50'>
          <div
            className={`${glass.surfaceStrong} rounded-xl p-6 max-w-md w-full mx-4 border border-white/10`}
          >
            <h2 className='text-lg font-semibold text-foreground mb-4'>
              Move {moveModal.faceIds.length} face
              {moveModal.faceIds.length === 1 ? '' : 's'} to another person
            </h2>

            <div className='mb-4'>
              <label className='block text-sm text-muted-foreground mb-2'>
                Destination person
              </label>
              <select
                className='w-full bg-white/10 border border-white/10 rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-blue-400'
                value={moveModal.targetClusterId}
                onChange={(e) =>
                  setMoveModal((prev) => ({
                    ...prev,
                    targetClusterId: e.target.value,
                  }))
                }
              >
                {clustersForMove.length === 0 && (
                  <option value=''>No other people available</option>
                )}
                {clustersForMove.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            <div className='flex gap-3'>
              <button
                onClick={() =>
                  setMoveModal({
                    open: false,
                    faceIds: [],
                    targetClusterId: '',
                  })
                }
                className='btn-glass btn-glass--muted flex-1'
                disabled={moveLoading}
              >
                Cancel
              </button>
              <button
                onClick={handleMoveFaces}
                disabled={moveLoading || !moveModal.targetClusterId}
                className='btn-glass btn-glass--primary flex-1 flex items-center justify-center gap-2'
              >
                {moveLoading ? (
                  <Loader2 className='animate-spin' size={16} />
                ) : (
                  <Move size={16} />
                )}
                <span>Move</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Similar Faces Modal */}
      {similarModal.open && (
        <div className='fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50'>
          <div
            className={`${glass.surfaceStrong} rounded-xl p-6 max-w-3xl w-full mx-4 border border-white/10`}
          >
            <div className='flex justify-between items-center mb-4'>
              <h2 className='text-lg font-semibold text-foreground'>
                Similar faces
              </h2>
              <button
                onClick={() =>
                  setSimilarModal({
                    open: false,
                    loading: false,
                    results: [],
                    error: null,
                  })
                }
                className='btn-glass btn-glass--muted px-3 py-1'
              >
                Close
              </button>
            </div>

            {similarModal.loading && (
              <div className='flex items-center gap-2 text-muted-foreground'>
                <Loader2 className='animate-spin' size={16} />
                <span>Finding similar faces...</span>
              </div>
            )}

            {similarModal.error && (
              <div className='text-red-400 text-sm mb-2'>
                {similarModal.error}
              </div>
            )}

            {!similarModal.loading &&
              !similarModal.error &&
              (similarModal.results?.length || 0) === 0 && (
                <div className='text-sm text-muted-foreground'>
                  No similar faces found.
                </div>
              )}

            {!similarModal.loading &&
              (similarModal.results?.length || 0) > 0 && (
                <div className='grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3'>
                  {similarModal.results?.map((sim) => (
                    <div
                      key={sim.detection_id}
                      className='p-2 bg-white/5 rounded-lg border border-white/10'
                    >
                      <img
                        src={`${
                          import.meta.env.VITE_API_URL ||
                          'http://localhost:8000'
                        }/api/faces/crop/${sim.detection_id}?size=200`}
                        alt='Similar face'
                        className='w-full h-32 object-cover rounded'
                      />
                      <div className='mt-2 text-xs text-muted-foreground flex items-center justify-between gap-2'>
                        <span>{Math.round(sim.similarity * 100)}% match</span>
                        {sim.person_label && (
                          <span
                            className='px-2 py-0.5 bg-white/10 rounded text-foreground truncate'
                            title={sim.person_label}
                          >
                            {sim.person_label}
                          </span>
                        )}
                      </div>
                      {sim.person_id && (
                        <button
                          onClick={() => navigate(`/people/${sim.person_id}`)}
                          className='mt-2 w-full btn-glass btn-glass--muted text-xs'
                        >
                          Open person
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
          </div>
        </div>
      )}
    </div>
  );
}
