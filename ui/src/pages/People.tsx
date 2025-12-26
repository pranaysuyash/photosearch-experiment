/**
 * People Page - Face Recognition Interface
 *
 * Displays face clusters and allows management of people in photos.
 * Uses the glass design system consistent with the rest of the app.
 */
import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Users,
  Camera,
  Search,
  RefreshCw,
  User,
  Tag,
  Clock,
  Image as ImageIcon,
  Trash2,
  AlertCircle,
  CheckCircle,
  EyeOff,
  Pause,
  Play,
  ToggleLeft,
  Shield,
  Star,
  Undo2,
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';
import ReviewQueue from '../components/people/ReviewQueue';
import MergeSuggestions from '../components/people/MergeSuggestions';
import SplitClusterModal from '../components/people/SplitClusterModal';
import BooleanPeopleSearch from '../components/people/BooleanPeopleSearch';

interface FaceCluster {
  id: string;
  label?: string;
  face_count: number;
  image_count: number;
  face_ids?: number[]; // IDs for face crop endpoint
  images: string[];
  created_at?: string;
  is_mixed?: boolean;
  representative_face?: {
    detection_id: string;
    photo_path: string;
    quality_score?: number;
  };
  indexing_disabled?: boolean;
  coherence_score?: number; // Quality metric from backend
  hidden?: boolean;
}

interface FaceStats {
  total_photos: number;
  faces_detected: number;
  clusters_found: number;
  unidentified_faces: number;
  singletons: number;
  low_confidence: number;
}

interface MixedCluster {
  cluster_id: string;
  label?: string;
  face_count: number;
  coherence_score?: number;
  low_quality_ratio?: number;
  variance?: number;
  is_mixed_suspected?: boolean;
}

export function People() {
  const navigate = useNavigate();
  const [clusters, setClusters] = useState<FaceCluster[]>([]);
  const [stats, setStats] = useState<FaceStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState<{
    progress: number;
    message: string;
  } | null>(null);

  // Phase 6: Privacy controls
  const [isIndexingPaused, setIsIndexingPaused] = useState(false);
  const [pauseLoading, setPauseLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState<
    'people' | 'hidden' | 'review' | 'merge'
  >('people');
  const [reviewCount, setReviewCount] = useState(0);

  // Hidden Genius: surface remaining face scan/name endpoints
  const [showFaceTools, setShowFaceTools] = useState(false);
  const [personNameLookup, setPersonNameLookup] = useState('');
  const [personLookupLoading, setPersonLookupLoading] = useState(false);
  const [personLookupError, setPersonLookupError] = useState<string | null>(
    null
  );
  const [personLookupResult, setPersonLookupResult] = useState<any>(null);

  const [scanSingleFilesText, setScanSingleFilesText] = useState('');
  const [scanSingleLoading, setScanSingleLoading] = useState(false);
  const [scanSingleError, setScanSingleError] = useState<string | null>(null);
  const [scanSingleResult, setScanSingleResult] = useState<any>(null);

  const [scanStatusJobId, setScanStatusJobId] = useState('');
  const [scanStatusLoading, setScanStatusLoading] = useState(false);
  const [scanStatusError, setScanStatusError] = useState<string | null>(null);
  const [scanStatusResult, setScanStatusResult] = useState<any>(null);

  // Modal states
  const [renameModal, setRenameModal] = useState<{
    open: boolean;
    clusterId: string;
    currentLabel: string;
  }>({
    open: false,
    clusterId: '',
    currentLabel: '',
  });
  const [deleteModal, setDeleteModal] = useState<{
    open: boolean;
    clusterId: string;
    label: string;
  }>({
    open: false,
    clusterId: '',
    label: '',
  });
  const [newLabel, setNewLabel] = useState('');
  const [renameLoading, setRenameLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Undo functionality
  const [canUndo, setCanUndo] = useState(false);
  const [undoLoading, setUndoLoading] = useState(false);
  const [lastUndoOperation, setLastUndoOperation] = useState<string | null>(
    null
  );

  // Hide/Unhide functionality
  const [hideLoading, setHideLoading] = useState(false);

  // Split cluster functionality
  const [splitModal, setSplitModal] = useState<{
    open: boolean;
    cluster: FaceCluster | null;
  }>({
    open: false,
    cluster: null,
  });

  // Boolean search functionality
  const [booleanSearchOpen, setBooleanSearchOpen] = useState(false);

  // Mixed cluster detection tools
  const [mixedClusters, setMixedClusters] = useState<MixedCluster[]>([]);
  const [mixedThreshold, setMixedThreshold] = useState('0.5');
  const [mixedLoading, setMixedLoading] = useState(false);
  const [mixedError, setMixedError] = useState<string | null>(null);
  const [mixedQueried, setMixedQueried] = useState(false);

  // Embedding index stats
  const [indexStats, setIndexStats] = useState<any>(null);
  const [indexStatsLoading, setIndexStatsLoading] = useState(false);
  const [indexStatsError, setIndexStatsError] = useState<string | null>(null);

  // Prototype recompute
  const [recomputeLoading, setRecomputeLoading] = useState(false);
  const [recomputeMessage, setRecomputeMessage] = useState<string | null>(null);

  const fetchIndexingStatus = useCallback(async () => {
    try {
      const status = await api.getGlobalIndexingStatus();
      setIsIndexingPaused(Boolean(status?.paused));
    } catch (err) {
      console.error('Failed to fetch indexing status:', err);
      setIsIndexingPaused(false);
    }
  }, []);

  const checkUndoAvailability = async () => {
    try {
      const status = await api.getUndoStatus();
      setCanUndo(Boolean(status?.can_undo));
      setLastUndoOperation(status?.operation_type || null);
    } catch (err) {
      console.error('Failed to check undo availability:', err);
      setCanUndo(false);
      setLastUndoOperation(null);
    }
  };

  const handleUndo = async () => {
    try {
      setUndoLoading(true);
      const result = await api.undoLastOperation();

      if (result.success) {
        // Refresh all data after undo
        await Promise.all([
          fetchClusters(),
          fetchStats(),
          fetchReviewCount(),
          checkUndoAvailability(),
        ]);

        // Show success message
        const operationType = result.operation_type || 'operation';
        alert(`Successfully undid ${operationType}`);
      } else {
        alert(result.message || 'Nothing to undo');
      }
    } catch (err) {
      console.error('Failed to undo operation:', err);
      alert('Failed to undo operation');
    } finally {
      setUndoLoading(false);
    }
  };

  const handleHidePerson = async (clusterId: string) => {
    try {
      setHideLoading(true);
      const response = await fetch(
        `${
          import.meta.env.VITE_API_URL || 'http://localhost:8000'
        }/api/faces/clusters/${clusterId}/hide`,
        { method: 'POST' }
      );

      if (response.ok) {
        // Mark as hidden locally and refresh stats
        setClusters((prev) =>
          prev.map((cluster) =>
            cluster.id === clusterId ? { ...cluster, hidden: true } : cluster
          )
        );
        await Promise.all([fetchStats(), checkUndoAvailability()]);
        alert('Person hidden successfully');
      } else {
        throw new Error('Failed to hide person');
      }
    } catch (err) {
      console.error('Failed to hide person:', err);
      alert('Failed to hide person');
    } finally {
      setHideLoading(false);
    }
  };

  const handleUnhidePerson = async (clusterId: string) => {
    try {
      setHideLoading(true);
      const response = await fetch(
        `${
          import.meta.env.VITE_API_URL || 'http://localhost:8000'
        }/api/faces/clusters/${clusterId}/unhide`,
        { method: 'POST' }
      );

      if (response.ok) {
        // Mark as visible locally and refresh stats
        setClusters((prev) =>
          prev.map((cluster) =>
            cluster.id === clusterId ? { ...cluster, hidden: false } : cluster
          )
        );
        await Promise.all([fetchStats(), checkUndoAvailability()]);
        alert('Person unhidden successfully');
      } else {
        throw new Error('Failed to unhide person');
      }
    } catch (err) {
      console.error('Failed to unhide person:', err);
      alert('Failed to unhide person');
    } finally {
      setHideLoading(false);
    }
  };

  const openSplitModal = (cluster: FaceCluster) => {
    setSplitModal({ open: true, cluster });
  };

  const closeSplitModal = () => {
    setSplitModal({ open: false, cluster: null });
  };

  const handleSplitComplete = async () => {
    // Refresh all data after split
    await Promise.all([
      fetchClusters(),
      fetchStats(),
      fetchReviewCount(),
      checkUndoAvailability(),
    ]);
    closeSplitModal();
  };

  const fetchReviewCount = useCallback(async () => {
    try {
      const count = await api.getReviewQueueCount();
      setReviewCount(count);
    } catch (err) {
      console.error('Failed to fetch review count:', err);
    }
  }, []);

  const fetchClusters = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.getFaceClusters();
      setClusters(response.clusters || []);
    } catch (err) {
      console.error('Failed to fetch face clusters:', err);
      setError('Failed to load face clusters');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await api.getFaceStats();
      setStats(response);
    } catch (err) {
      console.error('Failed to fetch face stats:', err);
    }
  };

  const handleScan = async () => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    try {
      setScanning(true);
      setScanProgress({ progress: 0, message: 'Starting scan...' });

      // Start async scan
      const startResponse = await fetch(`${apiUrl}/api/faces/scan-async`, {
        method: 'POST',
      });
      const startData = await startResponse.json();

      if (!startData.job_id) {
        // No job ID means immediate completion (no photos)
        setScanProgress(null);
        setScanning(false);
        return;
      }

      // Poll for progress
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(
            `${apiUrl}/api/faces/scan-status/${startData.job_id}`
          );
          const statusData = await statusResponse.json();

          setScanProgress({
            progress: statusData.progress || 0,
            message: statusData.message || 'Scanning...',
          });

          if (
            statusData.status === 'completed' ||
            statusData.status === 'error'
          ) {
            clearInterval(pollInterval);
            setScanProgress(null);
            setScanning(false);

            // Refresh data
            await fetchClusters();
            await fetchStats();
          }
        } catch {
          clearInterval(pollInterval);
          setScanProgress(null);
          setScanning(false);
        }
      }, 1000);
    } catch (err) {
      console.error('Failed to scan faces:', err);
      setError('Failed to scan for faces');
      setScanProgress(null);
      setScanning(false);
    }
  };

  const handleLookupPersonByName = async () => {
    const name = personNameLookup.trim();
    if (!name) return;

    try {
      setPersonLookupLoading(true);
      setPersonLookupError(null);
      setPersonLookupResult(null);

      const data = await api.get(
        `/api/faces/person/${encodeURIComponent(name)}`
      );
      setPersonLookupResult(data);
    } catch (err: any) {
      console.error('Failed to lookup person by name:', err);
      setPersonLookupError(err?.message || 'Failed to lookup person by name');
    } finally {
      setPersonLookupLoading(false);
    }
  };

  const handleScanSingle = async () => {
    const files = scanSingleFilesText
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean);

    if (files.length === 0) return;

    try {
      setScanSingleLoading(true);
      setScanSingleError(null);
      setScanSingleResult(null);

      const data = await api.post('/api/faces/scan-single', { files });
      setScanSingleResult(data);
    } catch (err: any) {
      console.error('Failed to scan single file(s) for faces:', err);
      setScanSingleError(
        err?.response?.data?.detail ||
          err?.message ||
          'Failed to scan file(s) for faces'
      );
    } finally {
      setScanSingleLoading(false);
    }
  };

  const handleCheckScanStatus = async () => {
    const jobId = scanStatusJobId.trim();
    if (!jobId) return;

    try {
      setScanStatusLoading(true);
      setScanStatusError(null);
      setScanStatusResult(null);

      const data = await api.get(
        `/api/faces/scan-status/${encodeURIComponent(jobId)}`
      );
      setScanStatusResult(data);
    } catch (err: any) {
      console.error('Failed to fetch scan job status:', err);
      setScanStatusError(
        err?.response?.data?.detail ||
          err?.message ||
          'Failed to fetch scan job status'
      );
    } finally {
      setScanStatusLoading(false);
    }
  };

  const handleLoadMixedClusters = async () => {
    const parsedThreshold = Number(mixedThreshold);
    const threshold = Number.isFinite(parsedThreshold) ? parsedThreshold : 0.5;
    try {
      setMixedLoading(true);
      setMixedError(null);
      setMixedQueried(true);
      const data = await api.getMixedClusters(threshold);
      setMixedClusters(data?.clusters || []);
    } catch (err: any) {
      console.error('Failed to load mixed clusters:', err);
      setMixedError(err?.message || 'Failed to load mixed clusters');
      setMixedClusters([]);
    } finally {
      setMixedLoading(false);
    }
  };

  const handleLoadIndexStats = async () => {
    try {
      setIndexStatsLoading(true);
      setIndexStatsError(null);
      const data = await api.getEmbeddingIndexStats();
      setIndexStats(data);
    } catch (err: any) {
      console.error('Failed to load index stats:', err);
      setIndexStatsError(err?.message || 'Failed to load index stats');
      setIndexStats(null);
    } finally {
      setIndexStatsLoading(false);
    }
  };

  const handleRecomputePrototypes = async () => {
    try {
      setRecomputeLoading(true);
      setRecomputeMessage(null);
      const data = await api.recomputePrototypes();
      setRecomputeMessage(data?.message || 'Prototypes recomputed');
      await handleLoadIndexStats();
    } catch (err: any) {
      console.error('Failed to recompute prototypes:', err);
      setRecomputeMessage(err?.message || 'Failed to recompute prototypes');
    } finally {
      setRecomputeLoading(false);
    }
  };

  const handleSetLabel = async (clusterId: string, newLabel: string) => {
    try {
      setRenameLoading(true);
      await api.renameCluster(clusterId, newLabel);

      // Update local state
      setClusters(
        clusters.map((cluster) =>
          cluster.id === clusterId ? { ...cluster, label: newLabel } : cluster
        )
      );

      // Refresh stats in case labels affect counts
      await Promise.all([fetchStats(), checkUndoAvailability()]);
    } catch (err) {
      console.error('Failed to set label:', err);
      setError('Failed to update label');
    } finally {
      setRenameLoading(false);
    }
  };

  const openDeleteModal = (clusterId: string, label: string) => {
    setDeleteModal({ open: true, clusterId, label });
  };

  const confirmDelete = async () => {
    const { clusterId } = deleteModal;
    try {
      setDeleteLoading(true);
      const response = await fetch(
        `${
          import.meta.env.VITE_API_URL || 'http://localhost:8000'
        }/api/faces/clusters/${clusterId}`,
        { method: 'DELETE' }
      );
      if (response.ok) {
        setClusters(clusters.filter((c) => c.id !== clusterId));
        await Promise.all([
          fetchStats(),
          fetchReviewCount(),
          checkUndoAvailability(),
        ]);
        setDeleteModal({ open: false, clusterId: '', label: '' });
      } else {
        throw new Error('Failed to delete cluster');
      }
    } catch (err) {
      console.error('Failed to delete cluster:', err);
      setError('Failed to delete person');
    } finally {
      setDeleteLoading(false);
    }
  };

  const openRenameModal = (clusterId: string, currentLabel: string) => {
    setNewLabel(currentLabel);
    setRenameModal({ open: true, clusterId, currentLabel });
  };

  const confirmRename = async () => {
    const { clusterId } = renameModal;
    if (newLabel.trim()) {
      await handleSetLabel(clusterId, newLabel.trim());
      setRenameModal({ open: false, clusterId: '', currentLabel: '' });
      setNewLabel('');
    }
  };

  const filteredClusters = clusters.filter(
    (cluster) =>
      cluster.label?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cluster.id.toLowerCase().includes(searchTerm.toLowerCase())
  );
  const hiddenCount = clusters.filter((cluster) => cluster.hidden).length;
  const visibleClusters = filteredClusters.filter((cluster) => !cluster.hidden);
  const hiddenClusters = filteredClusters.filter((cluster) => cluster.hidden);
  const showHidden = activeTab === 'hidden';
  const displayedClusters = showHidden ? hiddenClusters : visibleClusters;
  const noResults = !loading && displayedClusters.length === 0;

  const formatUndoLabel = (operationType?: string | null) => {
    if (!operationType) return 'last operation';
    const labels: Record<string, string> = {
      delete_person: 'delete person',
      review_confirm: 'review confirm',
      review_reject: 'review reject',
    };
    return labels[operationType] || operationType.replace(/_/g, ' ');
  };

  // Coherence Badge Component
  const CoherenceBadge = ({ coherenceScore }: { coherenceScore?: number }) => {
    if (coherenceScore === undefined) return null;

    const getQualityInfo = (score: number) => {
      if (score >= 0.8)
        return {
          label: 'High Quality',
          color: 'text-green-400 bg-green-400/10 border-green-400/20',
          icon: Star,
        };
      if (score >= 0.6)
        return {
          label: 'Good Quality',
          color: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
          icon: Shield,
        };
      return {
        label: 'Needs Review',
        color: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
        icon: AlertCircle,
      };
    };

    const quality = getQualityInfo(coherenceScore);
    const Icon = quality.icon;

    return (
      <div
        className={`px-2 py-1 rounded-full text-xs border flex items-center gap-1 ${quality.color}`}
        title={`Cluster coherence: ${(coherenceScore * 100).toFixed(0)}%`}
      >
        <Icon size={10} />
        <span className='hidden sm:inline'>{quality.label}</span>
      </div>
    );
  };

  return (
    <div className='min-h-screen'>
      {/* Header */}
      <div className='border-b border-white/10'>
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center gap-3'>
              <Users className='text-foreground' size={28} />
              <div>
                <h1 className='text-2xl font-bold text-foreground'>People</h1>
                <p className='text-sm text-muted-foreground'>
                  Face recognition and person management
                </p>
              </div>
            </div>

            <div className='flex items-center gap-3'>
              {/* Advanced Search Button */}
              <button
                onClick={() => setBooleanSearchOpen(true)}
                className='flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors bg-white/5 border-white/10 hover:bg-white/10 text-foreground'
                title='Advanced people search with AND/OR/NOT logic'
              >
                <Search size={14} />
                <span className='hidden sm:inline'>Advanced Search</span>
              </button>

              {/* Undo Button */}
              <button
                onClick={handleUndo}
                disabled={!canUndo || undoLoading}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors ${
                  canUndo && !undoLoading
                    ? 'bg-white/5 border-white/10 hover:bg-white/10 text-foreground'
                    : 'bg-white/5 border-white/5 text-muted-foreground cursor-not-allowed'
                }`}
                title={
                  canUndo
                    ? `Undo ${formatUndoLabel(lastUndoOperation)}`
                    : 'No operations to undo'
                }
              >
                {undoLoading ? (
                  <RefreshCw size={14} className='animate-spin' />
                ) : (
                  <Undo2 size={14} />
                )}
                <span className='hidden sm:inline'>
                  {undoLoading ? 'Undoing...' : 'Undo'}
                </span>
              </button>

              {/* Global Pause Button - Phase 6 */}
              <button
                onClick={handleTogglePause}
                disabled={pauseLoading}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors ${
                  isIndexingPaused
                    ? 'bg-yellow-500/20 border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/30'
                    : 'bg-white/5 border-white/10 hover:bg-white/10'
                }`}
                title={
                  isIndexingPaused
                    ? 'Resume Face Indexing'
                    : 'Pause Face Indexing'
                }
              >
                {pauseLoading ? (
                  <RefreshCw size={14} className='animate-spin' />
                ) : isIndexingPaused ? (
                  <Play size={14} /> // Show Play when paused (to resume)
                ) : (
                  <Pause size={14} /> // Show Pause when active (to pause)
                )}
                <span className='hidden sm:inline'>
                  {isIndexingPaused ? 'Resume Indexing' : 'Pause Indexing'}
                </span>
              </button>

              <button
                onClick={handleScan}
                disabled={scanning}
                className={`btn-glass ${
                  scanning ? 'btn-glass--muted' : 'btn-glass--primary'
                } text-sm px-4 py-2`}
              >
                {scanning ? (
                  <div className='flex items-center gap-2'>
                    <RefreshCw size={16} className='animate-spin' />
                    Scanning...
                  </div>
                ) : (
                  <div className='flex items-center gap-2'>
                    <Camera size={16} />
                    Scan Faces
                  </div>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className='border-b border-white/10'>
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='flex gap-1'>
            <button
              onClick={() => setActiveTab('people')}
              className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
                activeTab === 'people'
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <Users size={16} className='inline mr-2' />
              People
            </button>
            <button
              onClick={() => setActiveTab('hidden')}
              className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === 'hidden'
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <EyeOff size={16} />
              Hidden
              {hiddenCount > 0 && (
                <span className='bg-yellow-500 text-black text-xs rounded-full px-2 py-0.5 min-w-[20px] text-center'>
                  {hiddenCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('review')}
              className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === 'review'
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <CheckCircle size={16} />
              Needs Review
              {reviewCount > 0 && (
                <span className='bg-orange-500 text-white text-xs rounded-full px-2 py-0.5 min-w-[20px] text-center'>
                  {reviewCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('merge')}
              className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 flex items-center gap-2 ${
                activeTab === 'merge'
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <Users size={16} />
              Merge Suggestions
            </button>
          </div>
        </div>
      </div>

      {/* Review Queue Tab Content */}
      {activeTab === 'review' && (
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6'>
          <ReviewQueue onCountChange={setReviewCount} />
        </div>
      )}

      {/* Merge Suggestions Tab Content */}
      {activeTab === 'merge' && (
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6'>
          <MergeSuggestions />
        </div>
      )}

      {/* People Tab Content */}
      {(activeTab === 'people' || activeTab === 'hidden') && (
        <>
          {/* Stats and Search */}
          <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6'>
            <div className='grid grid-cols-1 md:grid-cols-4 gap-4 mb-6'>
              {/* Stats Cards */}
              {stats && (
                <>
                  <div
                    className={`${glass.surface} rounded-xl p-4 border border-white/10`}
                  >
                    <div className='flex items-center gap-3'>
                      <div className='w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center'>
                        <ImageIcon className='text-blue-400' size={18} />
                      </div>
                      <div>
                        <div className='text-2xl font-bold text-foreground'>
                          {(stats.total_photos ?? 0).toLocaleString()}
                        </div>
                        <div className='text-xs text-muted-foreground'>
                          Total Photos
                        </div>
                      </div>
                    </div>
                  </div>

                  <div
                    className={`${glass.surface} rounded-xl p-4 border border-white/10 hover:border-primary/50 cursor-pointer transition-colors`}
                    onClick={() =>
                      document
                        .getElementById('clusters-section')
                        ?.scrollIntoView({ behavior: 'smooth' })
                    }
                  >
                    <div className='flex items-center gap-3'>
                      <div className='w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center'>
                        <Users className='text-green-400' size={18} />
                      </div>
                      <div>
                        <div className='text-2xl font-bold text-foreground'>
                          {stats.clusters_found}
                        </div>
                        <div className='text-xs text-muted-foreground'>
                          People Found
                        </div>
                      </div>
                    </div>
                  </div>

                  <div
                    className={`${glass.surface} rounded-xl p-4 border border-white/10 hover:border-primary/50 cursor-pointer transition-colors`}
                    onClick={() => navigate('/people/all-photos')}
                  >
                    <div className='flex items-center gap-3'>
                      <div className='w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center'>
                        <Camera className='text-purple-400' size={18} />
                      </div>
                      <div>
                        <div className='text-2xl font-bold text-foreground'>
                          {(stats.faces_detected ?? 0).toLocaleString()}
                        </div>
                        <div className='text-xs text-muted-foreground'>
                          Faces Detected
                        </div>
                      </div>
                    </div>
                  </div>

                  <div
                    className={`${glass.surface} rounded-xl p-4 border border-white/10 hover:border-orange-500/50 cursor-pointer transition-colors`}
                    onClick={() =>
                      (stats.unidentified_faces ?? 0) > 0 &&
                      navigate('/people/unidentified')
                    }
                  >
                    <div className='flex items-center gap-3'>
                      <div className='w-10 h-10 rounded-full bg-orange-500/20 flex items-center justify-center'>
                        <User className='text-orange-400' size={18} />
                      </div>
                      <div>
                        <div className='text-2xl font-bold text-foreground'>
                          {stats.unidentified_faces}
                        </div>
                        <div className='text-xs text-muted-foreground'>
                          Name These
                        </div>
                      </div>
                    </div>
                  </div>

                  <div
                    className={`${glass.surface} rounded-xl p-4 border border-white/10 hover:border-yellow-500/50 cursor-pointer transition-colors`}
                    onClick={() =>
                      stats.singletons > 0 && navigate('/people/singletons')
                    }
                  >
                    <div className='flex items-center gap-3'>
                      <div className='w-10 h-10 rounded-full bg-yellow-500/20 flex items-center justify-center'>
                        <User className='text-yellow-400' size={18} />
                      </div>
                      <div>
                        <div className='text-2xl font-bold text-foreground'>
                          {stats.singletons}
                        </div>
                        <div className='text-xs text-muted-foreground'>
                          Seen Once
                        </div>
                      </div>
                    </div>
                  </div>

                  <div
                    className={`${glass.surface} rounded-xl p-4 border border-white/10 hover:border-red-500/50 cursor-pointer transition-colors`}
                    onClick={() =>
                      stats.low_confidence > 0 &&
                      navigate('/people/low-confidence')
                    }
                  >
                    <div className='flex items-center gap-3'>
                      <div className='w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center'>
                        <AlertCircle className='text-red-400' size={18} />
                      </div>
                      <div>
                        <div className='text-2xl font-bold text-foreground'>
                          {stats.low_confidence}
                        </div>
                        <div className='text-xs text-muted-foreground'>
                          Review These
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Search Row */}
            <div className='mb-6'>
              <div
                className={`${glass.surface} rounded-xl p-4 border border-white/10`}
              >
                <div className='flex items-center gap-2'>
                  <Search className='text-muted-foreground' size={16} />
                  <input
                    type='text'
                    placeholder='Search people...'
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className='flex-1 bg-transparent outline-none text-sm placeholder:text-muted-foreground'
                  />
                </div>
              </div>
            </div>

            {/* Scan Progress */}
            {scanProgress && (
              <div
                className={`${glass.surface} rounded-xl p-4 border border-white/10 mb-6`}
              >
                <div className='flex items-center gap-3 mb-2'>
                  <RefreshCw size={16} className='animate-spin text-primary' />
                  <span className='text-sm text-foreground'>
                    Scanning for faces...
                  </span>
                </div>
                <div className='w-full bg-white/10 rounded-full h-2 mb-2'>
                  <div
                    className='bg-primary h-2 rounded-full transition-all duration-300'
                    style={{ width: `${scanProgress.progress}%` }}
                  />
                </div>
                <div className='text-xs text-muted-foreground'>
                  {scanProgress.message}
                </div>
              </div>
            )}

            {/* Hidden Genius: scan/status/name tools */}
            <div
              className={`${glass.surface} rounded-xl p-4 border border-white/10 mb-6`}
            >
              <button
                onClick={() => setShowFaceTools((v) => !v)}
                className='w-full flex items-center justify-between gap-3'
              >
                <div className='flex items-center gap-2'>
                  <Camera size={16} className='text-muted-foreground' />
                  <span className='text-sm font-medium text-foreground'>
                    Face scan & lookup tools
                  </span>
                </div>
                <span className='text-xs text-muted-foreground'>
                  {showFaceTools ? 'Hide' : 'Show'}
                </span>
              </button>

              {showFaceTools && (
                <div className='mt-4 space-y-6'>
                  {/* Person name lookup */}
                  <div>
                    <div className='flex items-center justify-between gap-3 mb-2'>
                      <div className='flex items-center gap-2'>
                        <Search size={14} className='text-muted-foreground' />
                        <span className='text-sm text-foreground'>
                          Lookup person by name
                        </span>
                      </div>
                    </div>
                    <div className='flex gap-2'>
                      <input
                        type='text'
                        value={personNameLookup}
                        onChange={(e) => setPersonNameLookup(e.target.value)}
                        placeholder='Exact label (e.g. “John”)'
                        className='flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                      />
                      <button
                        onClick={handleLookupPersonByName}
                        className='btn-glass btn-glass--muted px-3 py-2 text-sm'
                        disabled={
                          personLookupLoading || !personNameLookup.trim()
                        }
                      >
                        {personLookupLoading ? (
                          <RefreshCw size={16} className='animate-spin' />
                        ) : (
                          'Lookup'
                        )}
                      </button>
                    </div>
                    {personLookupError && (
                      <div className='mt-2 text-xs text-red-400'>
                        {personLookupError}
                      </div>
                    )}
                    {personLookupResult && (
                      <div className='mt-3 space-y-2'>
                        <div className='text-xs text-muted-foreground'>
                          Found {personLookupResult?.total ?? 0} photo(s)
                        </div>
                        <div className='flex items-center gap-2'>
                          {(() => {
                            const match = clusters.find(
                              (c) =>
                                (c.label || '').trim() ===
                                personNameLookup.trim()
                            );
                            if (!match) return null;
                            return (
                              <button
                                onClick={() => navigate(`/people/${match.id}`)}
                                className='btn-glass btn-glass--primary px-3 py-2 text-sm'
                              >
                                Open person
                              </button>
                            );
                          })()}
                        </div>
                        <details className='mt-2'>
                          <summary className='text-xs text-muted-foreground cursor-pointer'>
                            Raw response
                          </summary>
                          <pre className='mt-2 text-xs overflow-auto bg-black/30 rounded-lg p-3 border border-white/10 text-foreground/90'>
                            {JSON.stringify(personLookupResult, null, 2)}
                          </pre>
                        </details>
                      </div>
                    )}
                  </div>

                  {/* Scan single */}
                  <div>
                    <div className='flex items-center gap-2 mb-2'>
                      <Camera size={14} className='text-muted-foreground' />
                      <span className='text-sm text-foreground'>
                        Scan single file(s)
                      </span>
                    </div>
                    <textarea
                      value={scanSingleFilesText}
                      onChange={(e) => setScanSingleFilesText(e.target.value)}
                      placeholder={
                        'Enter absolute file paths, one per line\n(e.g. /Users/you/Pictures/img.jpg)'
                      }
                      className='w-full min-h-[84px] bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                    />
                    <div className='mt-2 flex gap-2'>
                      <button
                        onClick={handleScanSingle}
                        className='btn-glass btn-glass--muted px-3 py-2 text-sm'
                        disabled={
                          scanSingleLoading || !scanSingleFilesText.trim()
                        }
                      >
                        {scanSingleLoading ? (
                          <div className='flex items-center gap-2'>
                            <RefreshCw size={16} className='animate-spin' />
                            Scanning…
                          </div>
                        ) : (
                          'Run scan-single'
                        )}
                      </button>
                    </div>
                    {scanSingleError && (
                      <div className='mt-2 text-xs text-red-400'>
                        {scanSingleError}
                      </div>
                    )}
                    {scanSingleResult && (
                      <details className='mt-2'>
                        <summary className='text-xs text-muted-foreground cursor-pointer'>
                          Raw result
                        </summary>
                        <pre className='mt-2 text-xs overflow-auto bg-black/30 rounded-lg p-3 border border-white/10 text-foreground/90'>
                          {JSON.stringify(scanSingleResult, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>

                  {/* Scan status */}
                  <div>
                    <div className='flex items-center gap-2 mb-2'>
                      <Clock size={14} className='text-muted-foreground' />
                      <span className='text-sm text-foreground'>
                        Check scan job status
                      </span>
                    </div>
                    <div className='flex gap-2'>
                      <input
                        type='text'
                        value={scanStatusJobId}
                        onChange={(e) => setScanStatusJobId(e.target.value)}
                        placeholder='Job ID (UUID)'
                        className='flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                      />
                      <button
                        onClick={handleCheckScanStatus}
                        className='btn-glass btn-glass--muted px-3 py-2 text-sm'
                        disabled={scanStatusLoading || !scanStatusJobId.trim()}
                      >
                        {scanStatusLoading ? (
                          <RefreshCw size={16} className='animate-spin' />
                        ) : (
                          'Check'
                        )}
                      </button>
                    </div>
                    {scanStatusError && (
                      <div className='mt-2 text-xs text-red-400'>
                        {scanStatusError}
                      </div>
                    )}
                    {scanStatusResult && (
                      <details className='mt-2'>
                        <summary className='text-xs text-muted-foreground cursor-pointer'>
                          Raw status
                        </summary>
                        <pre className='mt-2 text-xs overflow-auto bg-black/30 rounded-lg p-3 border border-white/10 text-foreground/90'>
                          {JSON.stringify(scanStatusResult, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>

                  {/* Mixed cluster detection */}
                  <div>
                    <div className='flex items-center gap-2 mb-2'>
                      <AlertCircle
                        size={14}
                        className='text-muted-foreground'
                      />
                      <span className='text-sm text-foreground'>
                        Detect mixed clusters
                      </span>
                    </div>
                    <div className='flex flex-wrap gap-2 items-center'>
                      <input
                        type='number'
                        min='0'
                        max='1'
                        step='0.05'
                        value={mixedThreshold}
                        onChange={(e) => setMixedThreshold(e.target.value)}
                        className='w-24 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                        placeholder='0.5'
                        aria-label='Coherence threshold'
                      />
                      <button
                        onClick={handleLoadMixedClusters}
                        className='btn-glass btn-glass--muted px-3 py-2 text-sm'
                        disabled={mixedLoading}
                      >
                        {mixedLoading ? (
                          <RefreshCw size={16} className='animate-spin' />
                        ) : (
                          'Find mixed clusters'
                        )}
                      </button>
                    </div>
                    {mixedError && (
                      <div className='mt-2 text-xs text-red-400'>
                        {mixedError}
                      </div>
                    )}
                    {mixedClusters.length > 0 && (
                      <div className='mt-3 space-y-2'>
                        {mixedClusters.map((cluster) => (
                          <div
                            key={cluster.cluster_id}
                            className='flex items-center justify-between gap-3 bg-white/5 border border-white/10 rounded-lg px-3 py-2'
                          >
                            <div className='min-w-0'>
                              <div className='text-sm text-foreground truncate'>
                                {cluster.label ||
                                  `Person ${cluster.cluster_id}`}
                              </div>
                              <div className='text-xs text-muted-foreground'>
                                {cluster.face_count} faces •{' '}
                                {cluster.coherence_score !== undefined
                                  ? `${Math.round(
                                      cluster.coherence_score * 100
                                    )}% coherence`
                                  : 'coherence n/a'}
                              </div>
                            </div>
                            <button
                              onClick={() =>
                                navigate(`/people/${cluster.cluster_id}`)
                              }
                              className='btn-glass btn-glass--muted text-xs px-2 py-1.5'
                            >
                              Open
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                    {!mixedLoading &&
                      !mixedError &&
                      mixedQueried &&
                      mixedClusters.length === 0 && (
                        <div className='mt-2 text-xs text-muted-foreground'>
                          No mixed clusters detected.
                        </div>
                      )}
                  </div>

                  {/* Embedding index stats */}
                  <div>
                    <div className='flex items-center gap-2 mb-2'>
                      <Users size={14} className='text-muted-foreground' />
                      <span className='text-sm text-foreground'>
                        Embedding index stats
                      </span>
                    </div>
                    <div className='flex gap-2'>
                      <button
                        onClick={handleLoadIndexStats}
                        className='btn-glass btn-glass--muted px-3 py-2 text-sm'
                        disabled={indexStatsLoading}
                      >
                        {indexStatsLoading ? (
                          <RefreshCw size={16} className='animate-spin' />
                        ) : (
                          'Refresh stats'
                        )}
                      </button>
                    </div>
                    {indexStatsError && (
                      <div className='mt-2 text-xs text-red-400'>
                        {indexStatsError}
                      </div>
                    )}
                    {indexStats && (
                      <div className='mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs text-muted-foreground'>
                        <div className='bg-white/5 border border-white/10 rounded-lg px-3 py-2'>
                          <div className='text-foreground font-medium'>
                            {indexStats.prototype_count ?? 0}
                          </div>
                          <div>Prototypes</div>
                        </div>
                        <div className='bg-white/5 border border-white/10 rounded-lg px-3 py-2'>
                          <div className='text-foreground font-medium'>
                            {indexStats.backend || 'unknown'}
                          </div>
                          <div>Backend</div>
                        </div>
                        <div className='bg-white/5 border border-white/10 rounded-lg px-3 py-2'>
                          <div className='text-foreground font-medium'>
                            {indexStats.memory_usage_mb ?? 0} MB
                          </div>
                          <div>Memory</div>
                        </div>
                        <div className='bg-white/5 border border-white/10 rounded-lg px-3 py-2'>
                          <div className='text-foreground font-medium'>
                            {indexStats.performance_tier || 'unknown'}
                          </div>
                          <div>Tier</div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Recompute prototypes */}
                  <div>
                    <div className='flex items-center gap-2 mb-2'>
                      <RefreshCw size={14} className='text-muted-foreground' />
                      <span className='text-sm text-foreground'>
                        Recompute face prototypes
                      </span>
                    </div>
                    <div className='flex gap-2'>
                      <button
                        onClick={handleRecomputePrototypes}
                        className='btn-glass btn-glass--muted px-3 py-2 text-sm'
                        disabled={recomputeLoading}
                      >
                        {recomputeLoading ? (
                          <RefreshCw size={16} className='animate-spin' />
                        ) : (
                          'Recompute prototypes'
                        )}
                      </button>
                    </div>
                    {recomputeMessage && (
                      <div className='mt-2 text-xs text-muted-foreground'>
                        {recomputeMessage}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Error State */}
            {error && (
              <div className='mb-6 text-sm text-destructive glass-surface rounded-xl p-4 border border-white/10'>
                {error}
              </div>
            )}

            {/* Loading State */}
            {loading && (
              <div className='flex items-center justify-center py-20'>
                <div className='flex items-center gap-3'>
                  <RefreshCw
                    size={20}
                    className='animate-spin text-muted-foreground'
                  />
                  <span className='text-muted-foreground'>
                    Loading face clusters...
                  </span>
                </div>
              </div>
            )}

            {/* Empty State */}
            {noResults && (
              <div className='text-center py-20'>
                <Users
                  size={48}
                  className='mx-auto text-muted-foreground mb-4'
                />
                <h3 className='text-lg font-medium text-foreground mb-2'>
                  {showHidden
                    ? 'No Hidden People'
                    : clusters.length === 0
                    ? 'No People Found'
                    : 'No Matches Found'}
                </h3>
                <p className='text-muted-foreground mb-6'>
                  {showHidden
                    ? 'Hidden people will show up here when you hide them.'
                    : clusters.length === 0
                    ? 'Start by scanning your photos for faces'
                    : 'Try a different search term.'}
                </p>
                {!showHidden && clusters.length === 0 && (
                  <button
                    onClick={handleScan}
                    disabled={scanning}
                    className={`btn-glass ${
                      scanning ? 'btn-glass--muted' : 'btn-glass--primary'
                    }`}
                  >
                    {scanning ? (
                      <div className='flex items-center gap-2'>
                        <RefreshCw size={16} className='animate-spin' />
                        Scanning...
                      </div>
                    ) : (
                      <div className='flex items-center gap-2'>
                        <Camera size={16} />
                        Scan for Faces
                      </div>
                    )}
                  </button>
                )}
              </div>
            )}

            {/* Face Clusters Grid */}
            {!loading && displayedClusters.length > 0 && (
              <div id='clusters-section' className='space-y-4'>
                {showHidden && (
                  <div className='text-sm text-yellow-400 bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3'>
                    <div className='flex items-center gap-2'>
                      <AlertCircle size={16} />
                      <span>
                        Showing {hiddenClusters.length} hidden people. These
                        won't appear in search results or suggestions.
                      </span>
                    </div>
                  </div>
                )}

                <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'>
                  {displayedClusters.map((cluster) => (
                    <div
                      key={cluster.id}
                      className={`${glass.surface} rounded-xl border border-white/10 overflow-hidden hover:border-white/20 transition-colors`}
                    >
                      {/* Preview Images */}
                      <div className='grid grid-cols-3 gap-1 p-3 bg-black/20'>
                        {(cluster.face_ids || [])
                          .slice(0, 6)
                          .map((faceId, index) => (
                            <img
                              key={index}
                              src={`${
                                import.meta.env.VITE_API_URL ||
                                'http://localhost:8000'
                              }/api/faces/crop/${faceId}?size=150`}
                              alt={`Face ${index + 1}`}
                              className='w-full h-20 object-cover rounded'
                              loading='lazy'
                              onError={(e) => {
                                // Fallback to full image if crop fails
                                const img = e.target as HTMLImageElement;
                                if (cluster.images[index]) {
                                  img.src = api.getImageUrl(
                                    cluster.images[index],
                                    150
                                  );
                                }
                              }}
                            />
                          ))}
                        {Array.from({
                          length: Math.max(
                            0,
                            6 - (cluster.face_ids?.length || 0)
                          ),
                        }).map((_, index) => (
                          <div
                            key={`empty-${index}`}
                            className='w-full h-20 bg-white/5 rounded flex items-center justify-center'
                          >
                            <ImageIcon size={16} className='text-white/20' />
                          </div>
                        ))}
                      </div>

                      {/* Cluster Info */}
                      <div className='p-4'>
                        <div className='flex items-center justify-between mb-3'>
                          <div className='flex items-center gap-2'>
                            <h3 className='font-medium text-foreground truncate'>
                              {cluster.label || `Person ${cluster.id}`}
                            </h3>
                            {cluster.indexing_disabled && (
                              <span
                                className='px-1.5 py-0.5 text-[10px] font-semibold bg-red-500/20 text-red-400 rounded flex items-center gap-1'
                                title='Auto-assignment is disabled for this person'
                              >
                                <ToggleLeft size={10} />
                                Manual
                              </span>
                            )}
                            {cluster.is_mixed && (
                              <span
                                className='px-1.5 py-0.5 text-[10px] font-semibold bg-yellow-500/20 text-yellow-400 rounded'
                                title='This cluster may contain multiple people'
                              >
                                Mixed?
                              </span>
                            )}
                          </div>
                          <div className='flex items-center gap-1 text-xs text-muted-foreground'>
                            <Camera size={12} />
                            {cluster.face_count}
                          </div>
                        </div>

                        {/* Quality and Stats Row */}
                        <div className='flex items-center justify-between mb-3'>
                          <div className='flex items-center gap-2'>
                            <CoherenceBadge
                              coherenceScore={cluster.coherence_score}
                            />
                            <div className='text-xs text-muted-foreground'>
                              {cluster.image_count} photos
                            </div>
                          </div>
                          {cluster.created_at && (
                            <div className='text-xs text-muted-foreground flex items-center gap-1'>
                              <Clock size={10} />
                              {new Date(
                                cluster.created_at
                              ).toLocaleDateString()}
                            </div>
                          )}
                        </div>

                        <div className='flex gap-2'>
                          <button
                            onClick={() =>
                              openRenameModal(
                                cluster.id,
                                cluster.label || `Person ${cluster.id}`
                              )
                            }
                            className='btn-glass btn-glass--muted text-xs px-2 py-1.5'
                            title='Rename'
                          >
                            <Tag size={12} />
                          </button>

                          {showHidden ? (
                            <button
                              onClick={() => handleUnhidePerson(cluster.id)}
                              disabled={hideLoading}
                              className='btn-glass btn-glass--muted text-xs px-2 py-1.5 hover:text-green-400'
                              title='Unhide this person'
                            >
                              {hideLoading ? (
                                <RefreshCw size={12} className='animate-spin' />
                              ) : (
                                <svg
                                  width='12'
                                  height='12'
                                  viewBox='0 0 24 24'
                                  fill='none'
                                  stroke='currentColor'
                                  strokeWidth='2'
                                  strokeLinecap='round'
                                  strokeLinejoin='round'
                                >
                                  <path d='M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z' />
                                  <circle cx='12' cy='12' r='3' />
                                </svg>
                              )}
                            </button>
                          ) : (
                            <button
                              onClick={() => handleHidePerson(cluster.id)}
                              disabled={hideLoading}
                              className='btn-glass btn-glass--muted text-xs px-2 py-1.5 hover:text-yellow-400'
                              title='Hide this person'
                            >
                              {hideLoading ? (
                                <RefreshCw size={12} className='animate-spin' />
                              ) : (
                                <svg
                                  width='12'
                                  height='12'
                                  viewBox='0 0 24 24'
                                  fill='none'
                                  stroke='currentColor'
                                  strokeWidth='2'
                                  strokeLinecap='round'
                                  strokeLinejoin='round'
                                >
                                  <path d='M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24' />
                                  <line x1='1' y1='1' x2='23' y2='23' />
                                </svg>
                              )}
                            </button>
                          )}

                          {!showHidden && cluster.face_count > 1 && (
                            <button
                              onClick={() => openSplitModal(cluster)}
                              className='btn-glass btn-glass--muted text-xs px-2 py-1.5 hover:text-blue-400'
                              title='Split this person into separate people'
                            >
                              <Users size={12} />
                            </button>
                          )}

                          <button
                            onClick={() =>
                              openDeleteModal(
                                cluster.id,
                                cluster.label || `Person ${cluster.id}`
                              )
                            }
                            className='btn-glass btn-glass--muted text-xs px-2 py-1.5 hover:text-red-400'
                            title='Delete this person group'
                          >
                            <Trash2 size={12} />
                          </button>

                          <Link
                            to={`/people/${cluster.id}`}
                            className='btn-glass btn-glass--primary text-xs px-3 py-1.5 flex-1 flex items-center justify-center'
                          >
                            <User size={12} className='mr-1' />
                            View Photos
                          </Link>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* Rename Modal */}
      {renameModal.open && (
        <div
          className='fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4'
          onClick={() =>
            setRenameModal({ open: false, clusterId: '', currentLabel: '' })
          }
        >
          <div
            className={`${glass.surface} border border-white/20 rounded-xl p-6 max-w-md w-full shadow-2xl`}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className='text-lg font-semibold text-foreground mb-4'>
              Rename Person
            </h3>
            <input
              type='text'
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              placeholder='Enter person name...'
              className='w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 mb-4'
              autoFocus
              onKeyDown={(e) => e.key === 'Enter' && confirmRename()}
            />
            <div className='flex gap-3 justify-end'>
              <button
                onClick={() =>
                  setRenameModal({
                    open: false,
                    clusterId: '',
                    currentLabel: '',
                  })
                }
                className='btn-glass btn-glass--muted px-4 py-2'
                disabled={renameLoading}
              >
                Cancel
              </button>
              <button
                onClick={confirmRename}
                className='btn-glass btn-glass--primary px-4 py-2 flex items-center gap-2'
                disabled={renameLoading || !newLabel.trim()}
              >
                {renameLoading && (
                  <RefreshCw size={14} className='animate-spin' />
                )}
                {renameLoading ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteModal.open && (
        <div
          className='fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4'
          onClick={() =>
            setDeleteModal({ open: false, clusterId: '', label: '' })
          }
        >
          <div
            className={`${glass.surface} border border-white/20 rounded-xl p-6 max-w-md w-full shadow-2xl`}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className='text-lg font-semibold text-foreground mb-2'>
              Delete Person?
            </h3>
            <p className='text-muted-foreground mb-4'>
              Delete "{deleteModal.label}"? This will ungroup these faces but
              won't delete the photos.
            </p>
            <div className='flex gap-3 justify-end'>
              <button
                onClick={() =>
                  setDeleteModal({ open: false, clusterId: '', label: '' })
                }
                className='btn-glass btn-glass--muted px-4 py-2'
                disabled={deleteLoading}
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className='btn-glass bg-red-500/20 hover:bg-red-500/30 text-red-400 px-4 py-2 rounded-lg transition-colors flex items-center gap-2'
                disabled={deleteLoading}
              >
                {deleteLoading && (
                  <RefreshCw size={14} className='animate-spin' />
                )}
                {deleteLoading ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Split Cluster Modal */}
      {splitModal.open && splitModal.cluster && (
        <SplitClusterModal
          cluster={splitModal.cluster}
          isOpen={splitModal.open}
          onClose={closeSplitModal}
          onSplit={handleSplitComplete}
        />
      )}

      {/* Boolean People Search Modal */}
      <BooleanPeopleSearch
        isOpen={booleanSearchOpen}
        onClose={() => setBooleanSearchOpen(false)}
      />
    </div>
  );
}

export default People;
