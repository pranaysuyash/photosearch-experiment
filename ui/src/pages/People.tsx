/**
 * People Page - Face Recognition Interface
 *
 * Displays face clusters and allows management of people in photos.
 * Uses the glass design system consistent with the rest of the app.
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Users,
  Camera,
  Search,
  RefreshCw,
  User,
  Tag,
  Clock,
  Image as ImageIcon
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface FaceCluster {
  id: string;
  label?: string;
  face_count: number;
  image_count: number;
  images: string[];
  created_at?: string;
}

interface FaceStats {
  total_photos: number;
  faces_detected: number;
  clusters_found: number;
  unidentified_faces: number;
}

export function People() {
  const [clusters, setClusters] = useState<FaceCluster[]>([]);
  const [stats, setStats] = useState<FaceStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchClusters();
    fetchStats();
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
    try {
      setScanning(true);
      const response = await api.scanFaces();
      console.log('Face scan completed:', response);

      // Refresh data after scan
      await fetchClusters();
      await fetchStats();
    } catch (err) {
      console.error('Failed to scan faces:', err);
      setError('Failed to scan for faces');
    } finally {
      setScanning(false);
    }
  };

  const handleSetLabel = async (clusterId: string, newLabel: string) => {
    try {
      await api.setFaceClusterLabel(clusterId, newLabel);

      // Update local state
      setClusters(clusters.map(cluster =>
        cluster.id === clusterId
          ? { ...cluster, label: newLabel }
          : cluster
      ));
    } catch (err) {
      console.error('Failed to set label:', err);
      setError('Failed to update label');
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

              <div className={`${glass.surface} rounded-xl p-4 border border-white/10`}>
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

              <div className={`${glass.surface} rounded-xl p-4 border border-white/10`}>
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

              <div className={`${glass.surface} rounded-xl p-4 border border-white/10`}>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-orange-500/20 flex items-center justify-center">
                    <User className="text-orange-400" size={18} />
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-foreground">{stats.unidentified_faces}</div>
                    <div className="text-xs text-muted-foreground">Unidentified</div>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Search */}
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredClusters.map((cluster) => (
              <div key={cluster.id} className={`${glass.surface} rounded-xl border border-white/10 overflow-hidden hover:border-white/20 transition-colors`}>
                {/* Preview Images */}
                <div className="grid grid-cols-3 gap-1 p-3 bg-black/20">
                  {cluster.images.slice(0, 6).map((imagePath, index) => (
                    <img
                      key={index}
                      src={api.getImageUrl(imagePath, 150)}
                      alt={`Face ${index + 1}`}
                      className="w-full h-20 object-cover rounded"
                      loading="lazy"
                    />
                  ))}
                  {Array.from({ length: Math.max(0, 6 - cluster.images.length) }).map((_, index) => (
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
                      onClick={() => {
                        const newLabel = prompt('Enter person name:', cluster.label || `Person ${cluster.id}`);
                        if (newLabel && newLabel.trim()) {
                          handleSetLabel(cluster.id, newLabel.trim());
                        }
                      }}
                      className="btn-glass btn-glass--muted text-xs px-3 py-1.5 flex-1"
                    >
                      <Tag size={12} className="mr-1" />
                      Rename
                    </button>

                    <Link
                      to={`/search?query=person:${encodeURIComponent(cluster.label || cluster.id)}`}
                      className="btn-glass btn-glass--primary text-xs px-3 py-1.5 flex-1"
                    >
                      <User size={12} className="mr-1" />
                      View
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default People;