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
  CheckCircle
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';
import ReviewQueue from '../components/people/ReviewQueue';

interface FaceCluster {
  id: string;
  label?: string;
  face_count: number;
  image_count: number;
  face_ids?: number[];  // IDs for face crop endpoint
  images: string[];
  created_at?: string;
}

interface FaceStats {
  total_photos: number;
  faces_detected: number;
  clusters_found: number;
  unidentified_faces: number;
  singletons: number;
  low_confidence: number;
}

export function People() {
  const navigate = useNavigate();
  const [clusters, setClusters] = useState<FaceCluster[]>([]);
  const [stats, setStats] = useState<FaceStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState<{ progress: number; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState<'people' | 'review'>('people');
  const [reviewCount, setReviewCount] = useState(0);

  // Modal states
  const [renameModal, setRenameModal] = useState<{ open: boolean; clusterId: string; currentLabel: string }>({
    open: false, clusterId: '', currentLabel: ''
  });
  const [deleteModal, setDeleteModal] = useState<{ open: boolean; clusterId: string; label: string }>({
    open: false, clusterId: '', label: ''
  });
  const [newLabel, setNewLabel] = useState('');
  const [renameLoading, setRenameLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  useEffect(() => {
    fetchClusters();
    fetchStats();
    fetchReviewCount();
  }, []);

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
        method: 'POST'
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
          const statusResponse = await fetch(`${apiUrl}/api/faces/scan-async/${startData.job_id}`);
          const statusData = await statusResponse.json();

          setScanProgress({
            progress: statusData.progress || 0,
            message: statusData.message || 'Scanning...'
          });

          if (statusData.status === 'completed' || statusData.status === 'error') {
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

  const handleSetLabel = async (clusterId: string, newLabel: string) => {
    try {
      setRenameLoading(true);
      await api.setFaceClusterLabel(clusterId, newLabel);

      // Update local state
      setClusters(clusters.map(cluster =>
        cluster.id === clusterId
          ? { ...cluster, label: newLabel }
          : cluster
      ));

      // Refresh stats in case labels affect counts
      await fetchStats();
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
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/clusters/${clusterId}`,
        { method: 'DELETE' }
      );
      if (response.ok) {
        setClusters(clusters.filter(c => c.id !== clusterId));
        await fetchStats();
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

  const filteredClusters = clusters.filter(cluster =>
    cluster.label?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    cluster.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Users className="text-foreground" size={28} />
              <div>
                <h1 className="text-2xl font-bold text-foreground">People</h1>
                <p className="text-sm text-muted-foreground">
                  Face recognition and person management
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleScan}
                disabled={scanning}
                className={`btn-glass ${scanning ? 'btn-glass--muted' : 'btn-glass--primary'} text-sm px-4 py-2`}
              >
                {scanning ? (
                  <div className="flex items-center gap-2">
                    <RefreshCw size={16} className="animate-spin" />
                    Scanning...
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
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
      <div className="border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-1">
            <button
              onClick={() => setActiveTab('people')}
              className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 ${activeTab === 'people'
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
            >
              <Users size={16} className="inline mr-2" />
              People
            </button>
            <button
              onClick={() => setActiveTab('review')}
              className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 flex items-center gap-2 ${activeTab === 'review'
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
            >
              <CheckCircle size={16} />
              Needs Review
              {reviewCount > 0 && (
                <span className="bg-orange-500 text-white text-xs rounded-full px-2 py-0.5 min-w-[20px] text-center">
                  {reviewCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Review Queue Tab Content */}
      {activeTab === 'review' && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <ReviewQueue onCountChange={setReviewCount} />
        </div>
      )}

      {/* People Tab Content */}
      {activeTab === 'people' && (
        <>
          {/* Stats and Search */}
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              {/* Stats Cards */}
              {stats && (
                <>
                  <div className={`${glass.surface} rounded-xl p-4 border border-white/10`}>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                        <ImageIcon className="text-blue-400" size={18} />
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-foreground">{stats.total_photos.toLocaleString()}</div>
                        <div className="text-xs text-muted-foreground">Total Photos</div>
                      </div>
                    </div>
                  </div>

                  <div className={`${glass.surface} rounded-xl p-4 border border-white/10 hover:border-primary/50 cursor-pointer transition-colors`}
                    onClick={() => document.getElementById('clusters-section')?.scrollIntoView({ behavior: 'smooth' })}>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                        <Users className="text-green-400" size={18} />
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-foreground">{stats.clusters_found}</div>
                        <div className="text-xs text-muted-foreground">People Found</div>
                      </div>
                    </div>
                  </div>

                  <div className={`${glass.surface} rounded-xl p-4 border border-white/10 hover:border-primary/50 cursor-pointer transition-colors`}
                    onClick={() => navigate('/people/all-photos')}>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                        <Camera className="text-purple-400" size={18} />
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-foreground">{stats.faces_detected.toLocaleString()}</div>
                        <div className="text-xs text-muted-foreground">Faces Detected</div>
                      </div>
                    </div>
                  </div>

                  <div className={`${glass.surface} rounded-xl p-4 border border-white/10 hover:border-orange-500/50 cursor-pointer transition-colors`}
                    onClick={() => stats.unidentified_faces > 0 && navigate('/people/unidentified')}>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-orange-500/20 flex items-center justify-center">
                        <User className="text-orange-400" size={18} />
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-foreground">{stats.unidentified_faces}</div>
                        <div className="text-xs text-muted-foreground">Name These</div>
                      </div>
                    </div>
                  </div>

                  <div className={`${glass.surface} rounded-xl p-4 border border-white/10 hover:border-yellow-500/50 cursor-pointer transition-colors`}
                    onClick={() => stats.singletons > 0 && navigate('/people/singletons')}>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-yellow-500/20 flex items-center justify-center">
                        <User className="text-yellow-400" size={18} />
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-foreground">{stats.singletons}</div>
                        <div className="text-xs text-muted-foreground">Seen Once</div>
                      </div>
                    </div>
                  </div>

                  <div className={`${glass.surface} rounded-xl p-4 border border-white/10 hover:border-red-500/50 cursor-pointer transition-colors`}
                    onClick={() => stats.low_confidence > 0 && navigate('/people/low-confidence')}>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center">
                        <AlertCircle className="text-red-400" size={18} />
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-foreground">{stats.low_confidence}</div>
                        <div className="text-xs text-muted-foreground">Review These</div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Search Row */}
            <div className="mb-6">
              <div className={`${glass.surface} rounded-xl p-4 border border-white/10`}>
                <div className="flex items-center gap-2">
                  <Search className="text-muted-foreground" size={16} />
                  <input
                    type="text"
                    placeholder="Search people..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="flex-1 bg-transparent outline-none text-sm placeholder:text-muted-foreground"
                  />
                </div>
              </div>
            </div>

            {/* Scan Progress */}
            {scanProgress && (
              <div className={`${glass.surface} rounded-xl p-4 border border-white/10 mb-6`}>
                <div className="flex items-center gap-3 mb-2">
                  <RefreshCw size={16} className="animate-spin text-primary" />
                  <span className="text-sm text-foreground">Scanning for faces...</span>
                </div>
                <div className="w-full bg-white/10 rounded-full h-2 mb-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-300"
                    style={{ width: `${scanProgress.progress}%` }}
                  />
                </div>
                <div className="text-xs text-muted-foreground">{scanProgress.message}</div>
              </div>
            )}

            {/* Error State */}
            {error && (
              <div className="mb-6 text-sm text-destructive glass-surface rounded-xl p-4 border border-white/10">
                {error}
              </div>
            )}

            {/* Loading State */}
            {loading && (
              <div className="flex items-center justify-center py-20">
                <div className="flex items-center gap-3">
                  <RefreshCw size={20} className="animate-spin text-muted-foreground" />
                  <span className="text-muted-foreground">Loading face clusters...</span>
                </div>
              </div>
            )}

            {/* No People State */}
            {!loading && clusters.length === 0 && (
              <div className="text-center py-20">
                <Users size={48} className="mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium text-foreground mb-2">No People Found</h3>
                <p className="text-muted-foreground mb-6">
                  Start by scanning your photos for faces
                </p>
                <button
                  onClick={handleScan}
                  disabled={scanning}
                  className="btn-glass btn-glass--primary"
                >
                  <Camera size={16} className="mr-2" />
                  Scan for Faces
                </button>
              </div>
            )}

            {/* Face Clusters Grid */}
            {!loading && filteredClusters.length > 0 && (
              <div id="clusters-section" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {filteredClusters.map((cluster) => (
                  <div key={cluster.id} className={`${glass.surface} rounded-xl border border-white/10 overflow-hidden hover:border-white/20 transition-colors`}>
                    {/* Preview Images */}
                    <div className="grid grid-cols-3 gap-1 p-3 bg-black/20">
                      {(cluster.face_ids || []).slice(0, 6).map((faceId, index) => (
                        <img
                          key={index}
                          src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/${faceId}/crop?size=150`}
                          alt={`Face ${index + 1}`}
                          className="w-full h-20 object-cover rounded"
                          loading="lazy"
                          onError={(e) => {
                            // Fallback to full image if crop fails
                            const img = e.target as HTMLImageElement;
                            if (cluster.images[index]) {
                              img.src = api.getImageUrl(cluster.images[index], 150);
                            }
                          }}
                        />
                      ))}
                      {Array.from({ length: Math.max(0, 6 - (cluster.face_ids?.length || 0)) }).map((_, index) => (
                        <div key={`empty-${index}`} className="w-full h-20 bg-white/5 rounded flex items-center justify-center">
                          <ImageIcon size={16} className="text-white/20" />
                        </div>
                      ))}
                    </div>

                    {/* Cluster Info */}
                    <div className="p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="font-medium text-foreground truncate">
                          {cluster.label || `Person ${cluster.id}`}
                        </h3>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Camera size={12} />
                          {cluster.face_count}
                        </div>
                      </div>

                      <div className="flex items-center justify-between mb-3">
                        <div className="text-xs text-muted-foreground">
                          {cluster.image_count} photos
                        </div>
                        {cluster.created_at && (
                          <div className="text-xs text-muted-foreground flex items-center gap-1">
                            <Clock size={10} />
                            {new Date(cluster.created_at).toLocaleDateString()}
                          </div>
                        )}
                      </div>

                      <div className="flex gap-2">
                        <button
                          onClick={() => openRenameModal(cluster.id, cluster.label || `Person ${cluster.id}`)}
                          className="btn-glass btn-glass--muted text-xs px-2 py-1.5"
                          title="Rename"
                        >
                          <Tag size={12} />
                        </button>

                        <button
                          onClick={() => openDeleteModal(cluster.id, cluster.label || `Person ${cluster.id}`)}
                          className="btn-glass btn-glass--muted text-xs px-2 py-1.5 hover:text-red-400"
                          title="Delete this person group"
                        >
                          <Trash2 size={12} />
                        </button>

                        <Link
                          to={`/people/${cluster.id}`}
                          className="btn-glass btn-glass--primary text-xs px-3 py-1.5 flex-1 flex items-center justify-center"
                        >
                          <User size={12} className="mr-1" />
                          View Photos
                        </Link>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* Rename Modal */}
      {renameModal.open && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setRenameModal({ open: false, clusterId: '', currentLabel: '' })}>
          <div className={`${glass.surface} border border-white/20 rounded-xl p-6 max-w-md w-full shadow-2xl`} onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-foreground mb-4">Rename Person</h3>
            <input
              type="text"
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              placeholder="Enter person name..."
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 mb-4"
              autoFocus
              onKeyDown={(e) => e.key === 'Enter' && confirmRename()}
            />
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setRenameModal({ open: false, clusterId: '', currentLabel: '' })}
                className="btn-glass btn-glass--muted px-4 py-2"
                disabled={renameLoading}
              >
                Cancel
              </button>
              <button
                onClick={confirmRename}
                className="btn-glass btn-glass--primary px-4 py-2 flex items-center gap-2"
                disabled={renameLoading || !newLabel.trim()}
              >
                {renameLoading && <RefreshCw size={14} className="animate-spin" />}
                {renameLoading ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteModal.open && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setDeleteModal({ open: false, clusterId: '', label: '' })}>
          <div className={`${glass.surface} border border-white/20 rounded-xl p-6 max-w-md w-full shadow-2xl`} onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-foreground mb-2">Delete Person?</h3>
            <p className="text-muted-foreground mb-4">
              Delete "{deleteModal.label}"? This will ungroup these faces but won't delete the photos.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteModal({ open: false, clusterId: '', label: '' })}
                className="btn-glass btn-glass--muted px-4 py-2"
                disabled={deleteLoading}
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="btn-glass bg-red-500/20 hover:bg-red-500/30 text-red-400 px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                disabled={deleteLoading}
              >
                {deleteLoading && <RefreshCw size={14} className="animate-spin" />}
                {deleteLoading ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


export default People;
